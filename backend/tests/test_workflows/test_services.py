"""
Unit tests for workflow services
"""
import pytest
from unittest.mock import patch, MagicMock, call
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta
import uuid
import json

from apps.workflows.services import (
    WorkflowExecutionService, WorkflowAuditService, WorkflowTemplateService,
    WorkflowMonitoringService
)
from apps.workflows.models import (
    Workflow, WorkflowExecution, WorkflowNode, WorkflowNodeExecution,
    WorkflowAuditLog, NodeType, WorkflowTemplate
)
from tests.factories import (
    WorkflowFactory, ActiveWorkflowFactory, WorkflowExecutionFactory,
    WorkflowNodeFactory, WorkflowNodeExecutionFactory, WorkflowTemplateFactory,
    NodeTypeFactory, UserFactory, WorkflowAuditLogFactory
)

User = get_user_model()


class TestWorkflowExecutionService:
    """Tests for WorkflowExecutionService."""
    
    def test_create_execution_success(self, db):
        """Test creating a workflow execution successfully."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        trigger_data = {"source": "test", "data": "value"}
        
        execution = WorkflowExecutionService.create_execution(
            workflow, user, trigger_data
        )
        
        assert execution.workflow == workflow
        assert execution.triggered_by == user
        assert execution.status == 'queued'
        assert execution.trigger_data == trigger_data
        assert execution.context_data == {}
        
        # Check node executions were created
        node_count = workflow.nodes.count()
        assert execution.node_executions.count() == node_count
    
    def test_create_execution_with_audit_log(self, db):
        """Test that creating execution creates audit log."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        
        with patch('apps.workflows.services.WorkflowAuditService.log_action') as mock_log:
            execution = WorkflowExecutionService.create_execution(workflow, user)
            
            mock_log.assert_called_once_with(
                user, 'execution_started', workflow, execution,
                f"Workflow execution created for '{workflow.name}'"
            )
    
    def test_create_execution_error_handling(self, db):
        """Test error handling in create_execution."""
        workflow = WorkflowFactory()
        user = UserFactory()
        
        # Mock database error
        with patch('apps.workflows.models.WorkflowExecution.objects.create') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            with pytest.raises(Exception) as exc_info:
                WorkflowExecutionService.create_execution(workflow, user)
            
            assert "Database error" in str(exc_info.value)
    
    @patch('apps.workflows.services.WorkflowExecutionService._execute_node')
    def test_start_execution_success(self, mock_execute_node, db):
        """Test starting a workflow execution successfully."""
        workflow = ActiveWorkflowFactory()
        execution = WorkflowExecutionFactory(workflow=workflow, status='queued')
        
        # Ensure we have a start node
        start_node_type = NodeTypeFactory(type='start')
        start_node = WorkflowNodeFactory(
            workflow=workflow,
            node_type=start_node_type,
            node_id='start_1'
        )
        
        WorkflowExecutionService.start_execution(execution)
        
        execution.refresh_from_db()
        assert execution.status == 'running'
        assert execution.current_node == start_node
        
        mock_execute_node.assert_called_once_with(execution, start_node)
    
    def test_start_execution_no_start_node(self, db):
        """Test starting execution without start node."""
        workflow = WorkflowFactory()  # No nodes
        execution = WorkflowExecutionFactory(workflow=workflow, status='queued')
        
        WorkflowExecutionService.start_execution(execution)
        
        execution.refresh_from_db()
        assert execution.status == 'failed'
        assert 'start node' in execution.error_message.lower()
    
    def test_start_execution_with_exception(self, db):
        """Test start_execution with unexpected exception."""
        workflow = ActiveWorkflowFactory()
        execution = WorkflowExecutionFactory(workflow=workflow, status='queued')
        
        with patch('apps.workflows.models.Workflow.nodes') as mock_nodes:
            mock_nodes.filter.side_effect = Exception("Unexpected error")
            
            WorkflowExecutionService.start_execution(execution)
            
            execution.refresh_from_db()
            assert execution.status == 'failed'
            assert execution.error_message == 'Unexpected error'
            assert execution.completed_at is not None
    
    @patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution')
    @patch('apps.workflows.services.WorkflowExecutionService._get_next_nodes')
    def test_execute_node_success(self, mock_get_next, mock_simulate, db):
        """Test executing a node successfully."""
        workflow = ActiveWorkflowFactory()
        execution = WorkflowExecutionFactory(workflow=workflow)
        node = workflow.nodes.first()
        
        mock_simulate.return_value = True
        mock_get_next.return_value = []  # No next nodes
        
        with patch('apps.workflows.services.WorkflowExecutionService._complete_execution') as mock_complete:
            WorkflowExecutionService._execute_node(execution, node)
            
            # Check node execution was created and completed
            node_execution = WorkflowNodeExecution.objects.get(
                workflow_execution=execution,
                workflow_node=node
            )
            assert node_execution.status == 'completed'
            assert node_execution.completed_at is not None
            
            mock_complete.assert_called_once_with(execution, 'completed')
    
    @patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution')
    def test_execute_node_failure(self, mock_simulate, db):
        """Test executing a node that fails."""
        workflow = ActiveWorkflowFactory()
        execution = WorkflowExecutionFactory(workflow=workflow)
        node = workflow.nodes.first()
        
        mock_simulate.return_value = False
        
        with patch('apps.workflows.services.WorkflowExecutionService._complete_execution') as mock_complete:
            WorkflowExecutionService._execute_node(execution, node)
            
            # Check node execution failed
            node_execution = WorkflowNodeExecution.objects.get(
                workflow_execution=execution,
                workflow_node=node
            )
            assert node_execution.status == 'failed'
            assert 'execution failed' in node_execution.error_message.lower()
            
            mock_complete.assert_called_once_with(execution, 'failed')
    
    @patch('time.sleep')  # Speed up tests
    def test_simulate_node_execution(self, mock_sleep, db):
        """Test node execution simulation."""
        node = WorkflowNodeFactory()
        node_execution = WorkflowNodeExecutionFactory(workflow_node=node)
        
        result = WorkflowExecutionService._simulate_node_execution(node, node_execution)
        
        # Should return success (95% success rate in simulation)
        assert isinstance(result, bool)
        
        # Check output data was set
        assert node_execution.output_data is not None
        assert 'executed_at' in node_execution.output_data
        assert node_execution.output_data['node_type'] == node.node_type.type
    
    def test_get_next_nodes_always_condition(self, db):
        """Test getting next nodes with 'always' condition."""
        workflow = ActiveWorkflowFactory()
        source_node = workflow.nodes.first()
        target_node = WorkflowNodeFactory(workflow=workflow)
        
        # Create edge with 'always' condition
        from apps.workflows.models import WorkflowEdge
        WorkflowEdge.objects.create(
            workflow=workflow,
            source_node=source_node,
            target_node=target_node,
            condition_type='always'
        )
        
        execution = WorkflowExecutionFactory(workflow=workflow)
        next_nodes = WorkflowExecutionService._get_next_nodes(execution, source_node)
        
        assert target_node in next_nodes
    
    def test_get_next_nodes_success_condition(self, db):
        """Test getting next nodes with 'success' condition."""
        workflow = ActiveWorkflowFactory()
        source_node = workflow.nodes.first()
        target_node = WorkflowNodeFactory(workflow=workflow)
        
        # Create edge with 'success' condition
        from apps.workflows.models import WorkflowEdge
        WorkflowEdge.objects.create(
            workflow=workflow,
            source_node=source_node,
            target_node=target_node,
            condition_type='success'
        )
        
        execution = WorkflowExecutionFactory(workflow=workflow)
        
        # Create completed node execution
        WorkflowNodeExecutionFactory(
            workflow_execution=execution,
            workflow_node=source_node,
            status='completed'
        )
        
        next_nodes = WorkflowExecutionService._get_next_nodes(execution, source_node)
        assert target_node in next_nodes
    
    def test_complete_execution(self, db):
        """Test completing a workflow execution."""
        workflow = WorkflowFactory()
        execution = WorkflowExecutionFactory(workflow=workflow, status='running')
        
        with patch('apps.workflows.services.WorkflowExecutionService._update_workflow_stats') as mock_update:
            WorkflowExecutionService._complete_execution(execution, 'completed')
            
            execution.refresh_from_db()
            assert execution.status == 'completed'
            assert execution.completed_at is not None
            assert execution.duration_seconds is not None
            assert execution.current_node is None
            
            mock_update.assert_called_once_with(workflow)
    
    def test_update_workflow_stats(self, db):
        """Test updating workflow statistics."""
        workflow = WorkflowFactory()
        
        # Create some executions
        WorkflowExecutionFactory(workflow=workflow, status='completed', duration_seconds=10.0)
        WorkflowExecutionFactory(workflow=workflow, status='completed', duration_seconds=20.0)
        WorkflowExecutionFactory(workflow=workflow, status='failed')
        
        WorkflowExecutionService._update_workflow_stats(workflow)
        
        workflow.refresh_from_db()
        assert workflow.total_executions == 3
        assert workflow.successful_executions == 2
        assert workflow.failed_executions == 1
        assert workflow.average_duration_seconds == 15.0  # (10+20)/2
        assert workflow.last_executed_at is not None
    
    def test_cancel_execution(self, db):
        """Test cancelling a workflow execution."""
        workflow = ActiveWorkflowFactory()
        execution = WorkflowExecutionFactory(workflow=workflow, status='running')
        user = UserFactory()
        
        # Create running node executions
        for node in workflow.nodes.all():
            WorkflowNodeExecutionFactory(
                workflow_execution=execution,
                workflow_node=node,
                status='running'
            )
        
        with patch('apps.workflows.services.WorkflowAuditService.log_action') as mock_log:
            WorkflowExecutionService.cancel_execution(execution, user)
            
            execution.refresh_from_db()
            assert execution.status == 'cancelled'
            assert execution.completed_at is not None
            
            # Check node executions were cancelled
            for node_exec in execution.node_executions.all():
                node_exec.refresh_from_db()
                assert node_exec.status == 'cancelled'
            
            mock_log.assert_called_once()


class TestWorkflowAuditService:
    """Tests for WorkflowAuditService."""
    
    def test_log_action_basic(self, db):
        """Test basic audit log creation."""
        user = UserFactory()
        workflow = WorkflowFactory()
        
        WorkflowAuditService.log_action(
            user=user,
            action='workflow_created',
            workflow=workflow,
            description='Test workflow created'
        )
        
        audit_log = WorkflowAuditLog.objects.first()
        assert audit_log.user == user
        assert audit_log.action == 'workflow_created'
        assert audit_log.workflow == workflow
        assert audit_log.description == 'Test workflow created'
    
    def test_log_action_with_execution(self, db):
        """Test audit log with workflow execution."""
        user = UserFactory()
        execution = WorkflowExecutionFactory()
        
        WorkflowAuditService.log_action(
            user=user,
            action='execution_started',
            workflow=execution.workflow,
            workflow_execution=execution,
            description='Execution started'
        )
        
        audit_log = WorkflowAuditLog.objects.first()
        assert audit_log.workflow_execution == execution
        assert audit_log.workflow == execution.workflow
    
    def test_log_action_with_request(self, db):
        """Test audit log with request information."""
        user = UserFactory()
        workflow = WorkflowFactory()
        
        # Mock request object
        mock_request = MagicMock()
        mock_request.META = {
            'HTTP_X_FORWARDED_FOR': '10.0.0.1, 192.168.1.1',
            'HTTP_USER_AGENT': 'Mozilla/5.0 Test Browser',
            'REMOTE_ADDR': '127.0.0.1'
        }
        
        WorkflowAuditService.log_action(
            user=user,
            action='data_accessed',
            workflow=workflow,
            description='Data accessed',
            request=mock_request
        )
        
        audit_log = WorkflowAuditLog.objects.first()
        assert audit_log.user_ip == '10.0.0.1'  # First IP from X-Forwarded-For
        assert audit_log.user_agent == 'Mozilla/5.0 Test Browser'
    
    def test_log_action_with_metadata(self, db):
        """Test audit log with custom metadata."""
        user = UserFactory()
        workflow = WorkflowFactory()
        metadata = {
            'session_id': str(uuid.uuid4()),
            'additional_context': 'test data'
        }
        
        WorkflowAuditService.log_action(
            user=user,
            action='workflow_updated',
            workflow=workflow,
            description='Workflow updated',
            metadata=metadata
        )
        
        audit_log = WorkflowAuditLog.objects.first()
        assert audit_log.metadata == metadata
        assert audit_log.metadata['session_id'] == metadata['session_id']
    
    def test_log_action_error_handling(self, db):
        """Test audit log error handling."""
        user = UserFactory()
        
        # Mock database error
        with patch('apps.workflows.models.WorkflowAuditLog.objects.create') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            # Should not raise exception
            WorkflowAuditService.log_action(
                user=user,
                action='test_action',
                description='Test action'
            )
    
    def test_get_client_ip_x_forwarded_for(self, db):
        """Test getting client IP from X-Forwarded-For header."""
        mock_request = MagicMock()
        mock_request.META = {'HTTP_X_FORWARDED_FOR': '10.0.0.1, 192.168.1.1'}
        
        ip = WorkflowAuditService._get_client_ip(mock_request)
        assert ip == '10.0.0.1'
    
    def test_get_client_ip_remote_addr(self, db):
        """Test getting client IP from REMOTE_ADDR."""
        mock_request = MagicMock()
        mock_request.META = {'REMOTE_ADDR': '192.168.1.1'}
        
        ip = WorkflowAuditService._get_client_ip(mock_request)
        assert ip == '192.168.1.1'


class TestWorkflowTemplateService:
    """Tests for WorkflowTemplateService."""
    
    def test_create_workflow_from_template_success(self, db):
        """Test creating workflow from template successfully."""
        template = WorkflowTemplateFactory()
        user = UserFactory()
        
        # Create node types for the template
        start_type = NodeTypeFactory(type='start')
        process_type = NodeTypeFactory(type='process')
        end_type = NodeTypeFactory(type='end')
        
        workflow = WorkflowTemplateService.create_workflow_from_template(
            template, user, "Custom Workflow Name"
        )
        
        assert workflow.name == "Custom Workflow Name"
        assert workflow.created_by == user
        assert workflow.template == template
        assert workflow.status == 'draft'
        assert workflow.description.startswith("Created from template:")
        
        # Check template usage was incremented
        template.refresh_from_db()
        initial_usage = template.usage_count
        template.increment_usage()
        assert template.usage_count == initial_usage + 1
    
    def test_create_workflow_from_template_with_nodes(self, db):
        """Test creating workflow from template with nodes."""
        # Create node types first
        start_type = NodeTypeFactory(type='start')
        process_type = NodeTypeFactory(type='process')
        end_type = NodeTypeFactory(type='end')
        
        template_definition = {
            "nodes": [
                {
                    "node_id": "start_1",
                    "name": "Start Process",
                    "type": "start",
                    "position": {"x": 100, "y": 100},
                    "config": {}
                },
                {
                    "node_id": "process_1",
                    "name": "Process Data",
                    "type": "process",
                    "position": {"x": 300, "y": 100},
                    "config": {"timeout_seconds": 600}
                }
            ],
            "edges": [
                {
                    "source": "start_1",
                    "target": "process_1",
                    "condition_type": "always"
                }
            ]
        }
        
        template = WorkflowTemplateFactory(definition=template_definition)
        user = UserFactory()
        
        workflow = WorkflowTemplateService.create_workflow_from_template(template, user)
        
        # Check nodes were created
        assert workflow.nodes.count() == 2
        start_node = workflow.nodes.get(node_id='start_1')
        assert start_node.name == 'Start Process'
        assert start_node.node_type.type == 'start'
        
        # Check edges were created
        assert workflow.edges.count() == 1
        edge = workflow.edges.first()
        assert edge.source_node.node_id == 'start_1'
        assert edge.target_node.node_id == 'process_1'
    
    def test_create_workflow_from_template_missing_node_type(self, db):
        """Test creating workflow when node type is missing."""
        template_definition = {
            "nodes": [
                {
                    "node_id": "missing_1",
                    "name": "Missing Type Node",
                    "type": "nonexistent_type",
                    "position": {"x": 100, "y": 100}
                }
            ],
            "edges": []
        }
        
        template = WorkflowTemplateFactory(definition=template_definition)
        user = UserFactory()
        
        workflow = WorkflowTemplateService.create_workflow_from_template(template, user)
        
        # Should create workflow but skip missing node type
        assert workflow.nodes.count() == 0
    
    def test_create_workflow_from_template_audit_log(self, db):
        """Test that creating workflow creates audit log."""
        template = WorkflowTemplateFactory()
        user = UserFactory()
        
        with patch('apps.workflows.services.WorkflowAuditService.log_action') as mock_log:
            workflow = WorkflowTemplateService.create_workflow_from_template(template, user)
            
            mock_log.assert_called_once_with(
                user, 'workflow_created', workflow,
                description=f"Workflow created from template: {template.name}"
            )
    
    def test_create_nodes_from_template(self, db):
        """Test creating nodes from template definition."""
        workflow = WorkflowFactory()
        start_type = NodeTypeFactory(type='start')
        
        nodes_data = [
            {
                "node_id": "start_1",
                "name": "Start Node",
                "type": "start",
                "position": {"x": 100, "y": 100},
                "config": {"custom": "value"},
                "is_required": True,
                "timeout_seconds": 600,
                "retry_count": 5
            }
        ]
        
        WorkflowTemplateService._create_nodes_from_template(workflow, nodes_data)
        
        assert workflow.nodes.count() == 1
        node = workflow.nodes.first()
        assert node.node_id == 'start_1'
        assert node.name == 'Start Node'
        assert node.position_x == 100
        assert node.position_y == 100
        assert node.config == {"custom": "value"}
        assert node.is_required is True
        assert node.timeout_seconds == 600
        assert node.retry_count == 5
    
    def test_create_edges_from_template(self, db):
        """Test creating edges from template definition."""
        workflow = WorkflowFactory()
        source_node = WorkflowNodeFactory(workflow=workflow, node_id='source_1')
        target_node = WorkflowNodeFactory(workflow=workflow, node_id='target_1')
        
        edges_data = [
            {
                "source": "source_1",
                "target": "target_1",
                "condition_type": "success",
                "condition_config": {"threshold": 0.8},
                "label": "On Success"
            }
        ]
        
        WorkflowTemplateService._create_edges_from_template(workflow, edges_data)
        
        assert workflow.edges.count() == 1
        edge = workflow.edges.first()
        assert edge.source_node == source_node
        assert edge.target_node == target_node
        assert edge.condition_type == 'success'
        assert edge.condition_config == {"threshold": 0.8}
        assert edge.label == 'On Success'


class TestWorkflowMonitoringService:
    """Tests for WorkflowMonitoringService."""
    
    def test_get_workflow_dashboard_stats(self, db):
        """Test getting workflow dashboard statistics."""
        # Create test data
        workflow1 = WorkflowFactory(status='active')
        workflow2 = WorkflowFactory(status='inactive')
        workflow3 = WorkflowFactory(status='active')
        
        # Create executions
        now = timezone.now()
        recent_time = now - timedelta(hours=12)
        old_time = now - timedelta(days=2)
        
        WorkflowExecutionFactory(workflow=workflow1, status='completed', started_at=recent_time)
        WorkflowExecutionFactory(workflow=workflow1, status='failed', started_at=recent_time)
        WorkflowExecutionFactory(workflow=workflow2, status='completed', started_at=old_time)
        WorkflowExecutionFactory(workflow=workflow1, status='running')
        
        stats = WorkflowMonitoringService.get_workflow_dashboard_stats()
        
        assert stats['total_workflows'] == 3
        assert stats['active_workflows'] == 2
        assert stats['total_executions'] == 4
        assert stats['recent_executions'] == 2  # Within last 24 hours
        assert stats['running_executions'] == 1
        assert stats['success_rate'] == 50.0  # 2 completed out of 4 total
        assert 'average_duration' in stats
        assert 'last_updated' in stats
    
    def test_get_workflow_dashboard_stats_empty(self, db):
        """Test dashboard stats with no data."""
        stats = WorkflowMonitoringService.get_workflow_dashboard_stats()
        
        assert stats['total_workflows'] == 0
        assert stats['active_workflows'] == 0
        assert stats['total_executions'] == 0
        assert stats['recent_executions'] == 0
        assert stats['running_executions'] == 0
        assert stats['success_rate'] == 0
        assert stats['average_duration'] == 0
    
    def test_get_workflow_performance_metrics(self, db):
        """Test getting workflow performance metrics."""
        workflow = WorkflowFactory()
        
        # Create executions over several days
        now = timezone.now()
        dates = [now - timedelta(days=i) for i in range(7)]
        
        for i, date in enumerate(dates):
            status = 'completed' if i % 2 == 0 else 'failed'
            duration = 30.0 + i * 10  # Varying durations
            
            WorkflowExecutionFactory(
                workflow=workflow,
                status=status,
                started_at=date,
                duration_seconds=duration if status == 'completed' else None
            )
        
        metrics = WorkflowMonitoringService.get_workflow_performance_metrics(
            workflow.id, days=7
        )
        
        assert metrics['workflow_id'] == str(workflow.id)
        assert metrics['workflow_name'] == workflow.name
        assert metrics['period_days'] == 7
        assert metrics['total_period_executions'] == 7
        assert 'daily_stats' in metrics
        
        # Check daily stats structure
        daily_stats = metrics['daily_stats']
        assert len(daily_stats) == 7
        
        for date_str, stats in daily_stats.items():
            assert 'total' in stats
            assert 'completed' in stats
            assert 'failed' in stats
            assert 'avg_duration' in stats
    
    def test_get_workflow_performance_metrics_nonexistent(self, db):
        """Test performance metrics for nonexistent workflow."""
        fake_id = uuid.uuid4()
        
        metrics = WorkflowMonitoringService.get_workflow_performance_metrics(fake_id)
        
        assert 'error' in metrics
        assert metrics['error'] == 'Workflow not found'
    
    def test_get_workflow_performance_metrics_error_handling(self, db):
        """Test error handling in performance metrics."""
        workflow = WorkflowFactory()
        
        with patch('apps.workflows.models.Workflow.objects.get') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            metrics = WorkflowMonitoringService.get_workflow_performance_metrics(workflow.id)
            
            assert 'error' in metrics
            assert metrics['error'] == 'Database error'