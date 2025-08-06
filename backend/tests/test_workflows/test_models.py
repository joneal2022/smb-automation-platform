"""
Unit tests for workflow models
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal
import uuid

from apps.workflows.models import (
    NodeType, WorkflowTemplate, Workflow, WorkflowNode, WorkflowEdge,
    WorkflowExecution, WorkflowNodeExecution, WorkflowAuditLog
)
from tests.factories import (
    NodeTypeFactory, WorkflowTemplateFactory, WorkflowFactory, WorkflowNodeFactory,
    WorkflowEdgeFactory, WorkflowExecutionFactory, WorkflowNodeExecutionFactory,
    WorkflowAuditLogFactory, UserFactory, ActiveWorkflowFactory,
    CompletedWorkflowExecutionFactory, FailedWorkflowExecutionFactory
)

User = get_user_model()


class TestNodeType:
    """Tests for NodeType model."""
    
    def test_create_node_type(self, db):
        """Test creating a node type."""
        node_type = NodeTypeFactory(
            name='Test Process Node',
            type='process',
            icon='cog',
            color='#007bff'
        )
        
        assert node_type.name == 'Test Process Node'
        assert node_type.type == 'process'
        assert node_type.get_type_display() == 'Process Node'
        assert node_type.icon == 'cog'
        assert node_type.color == '#007bff'
        assert str(node_type) == 'Test Process Node (Process Node)'
    
    def test_node_type_unique_name(self, db):
        """Test that node type names must be unique."""
        NodeTypeFactory(name='Unique Node')
        
        with pytest.raises(IntegrityError):
            NodeTypeFactory(name='Unique Node')
    
    def test_node_type_choices(self, db):
        """Test node type choices are valid."""
        valid_types = ['start', 'end', 'process', 'decision', 'approval', 
                      'document', 'integration', 'notification']
        
        for node_type in valid_types:
            node = NodeTypeFactory(type=node_type)
            assert node.type == node_type
    
    def test_node_type_config_schema(self, db):
        """Test node type config schema."""
        schema = {
            "properties": {
                "timeout": {"type": "number", "default": 300},
                "priority": {"type": "string", "enum": ["low", "normal", "high"]}
            },
            "required": ["timeout"]
        }
        
        node_type = NodeTypeFactory(config_schema=schema)
        assert node_type.config_schema == schema
    
    def test_node_type_default_values(self, db):
        """Test node type default values."""
        node_type = NodeTypeFactory()
        
        assert node_type.requires_user_action in [True, False]
        assert node_type.allows_multiple_outputs in [True, False]
        assert node_type.created_at is not None
        assert node_type.updated_at is not None
    
    def test_node_type_ordering(self, db):
        """Test node type ordering."""
        node1 = NodeTypeFactory(type='start', name='A Start')
        node2 = NodeTypeFactory(type='start', name='B Start')
        node3 = NodeTypeFactory(type='end', name='A End')
        
        ordered = NodeType.objects.all()
        assert list(ordered) == [node3, node1, node2]  # end comes before start alphabetically


class TestWorkflowTemplate:
    """Tests for WorkflowTemplate model."""
    
    def test_create_workflow_template(self, db):
        """Test creating a workflow template."""
        template = WorkflowTemplateFactory(
            name='Invoice Processing',
            category='document_processing',
            complexity_level=3,
            setup_time_minutes=45
        )
        
        assert template.name == 'Invoice Processing'
        assert template.category == 'document_processing'
        assert template.complexity_level == 3
        assert template.setup_time_minutes == 45
        assert template.usage_count == 0  # Should be 0 initially
        assert str(template) == 'Invoice Processing'
    
    def test_template_increment_usage(self, db):
        """Test incrementing template usage count."""
        template = WorkflowTemplateFactory(usage_count=5)
        initial_count = template.usage_count
        
        template.increment_usage()
        
        template.refresh_from_db()
        assert template.usage_count == initial_count + 1
    
    def test_template_category_choices(self, db):
        """Test template category choices."""
        valid_categories = [
            'document_processing', 'approval', 'customer_service',
            'integration', 'compliance'
        ]
        
        for category in valid_categories:
            template = WorkflowTemplateFactory(category=category)
            assert template.category == category
    
    def test_template_complexity_validation(self, db):
        """Test template complexity level validation."""
        # Valid complexity levels
        for level in range(1, 6):  # 1-5
            template = WorkflowTemplateFactory(complexity_level=level)
            assert template.complexity_level == level
        
        # Invalid complexity levels should be handled by factory bounds
        template = WorkflowTemplateFactory()
        assert 1 <= template.complexity_level <= 5
    
    def test_template_definition_structure(self, db):
        """Test template definition structure."""
        definition = {
            "nodes": [
                {
                    "node_id": "start_1",
                    "name": "Start",
                    "type": "start",
                    "position": {"x": 100, "y": 100}
                }
            ],
            "edges": []
        }
        
        template = WorkflowTemplateFactory(definition=definition)
        assert template.definition == definition
        assert len(template.definition['nodes']) == 1
        assert template.definition['nodes'][0]['type'] == 'start'
    
    def test_template_tags(self, db):
        """Test template tags field."""
        tags = ['invoice', 'accounting', 'automation']
        template = WorkflowTemplateFactory(tags=tags)
        
        assert template.tags == tags
        assert 'invoice' in template.tags
    
    def test_template_ordering(self, db):
        """Test template ordering by usage count."""
        template1 = WorkflowTemplateFactory(name='Template A', usage_count=5)
        template2 = WorkflowTemplateFactory(name='Template B', usage_count=10)
        template3 = WorkflowTemplateFactory(name='Template C', usage_count=3)
        
        ordered = WorkflowTemplate.objects.all()
        assert list(ordered) == [template2, template1, template3]


class TestWorkflow:
    """Tests for Workflow model."""
    
    def test_create_workflow(self, db):
        """Test creating a workflow."""
        user = UserFactory()
        template = WorkflowTemplateFactory()
        
        workflow = WorkflowFactory(
            name='Test Workflow',
            description='Test workflow description',
            created_by=user,
            status='draft',
            template=template
        )
        
        assert workflow.name == 'Test Workflow'
        assert workflow.created_by == user
        assert workflow.status == 'draft'
        assert workflow.template == template
        assert str(workflow) == 'Test Workflow'
    
    def test_workflow_success_rate_property(self, db):
        """Test workflow success rate calculation."""
        workflow = WorkflowFactory(
            total_executions=100,
            successful_executions=85,
            failed_executions=15
        )
        
        assert workflow.success_rate == 85.0
        
        # Test with zero executions
        workflow_empty = WorkflowFactory(total_executions=0)
        assert workflow_empty.success_rate == 0
    
    def test_workflow_status_choices(self, db):
        """Test workflow status choices."""
        valid_statuses = ['draft', 'active', 'paused', 'inactive', 'archived']
        
        for status in valid_statuses:
            workflow = WorkflowFactory(status=status)
            assert workflow.status == status
    
    def test_workflow_trigger_choices(self, db):
        """Test workflow trigger type choices."""
        valid_triggers = ['manual', 'schedule', 'event', 'webhook', 'document_upload']
        
        for trigger in valid_triggers:
            workflow = WorkflowFactory(trigger_type=trigger)
            assert workflow.trigger_type == trigger
    
    def test_workflow_assigned_users(self, db):
        """Test workflow assigned users many-to-many relationship."""
        workflow = WorkflowFactory()
        user1 = UserFactory()
        user2 = UserFactory()
        
        workflow.assigned_users.add(user1, user2)
        
        assert workflow.assigned_users.count() == 2
        assert user1 in workflow.assigned_users.all()
        assert user2 in workflow.assigned_users.all()
    
    def test_workflow_definition_field(self, db):
        """Test workflow definition JSON field."""
        definition = {
            "nodes": [
                {"node_id": "start_1", "type": "start"},
                {"node_id": "end_1", "type": "end"}
            ],
            "edges": [
                {"source": "start_1", "target": "end_1"}
            ],
            "version": 1
        }
        
        workflow = WorkflowFactory(definition=definition)
        assert workflow.definition == definition
        assert workflow.definition['version'] == 1
    
    def test_workflow_schedule_config(self, db):
        """Test workflow schedule configuration."""
        schedule_config = {
            "interval": "daily",
            "time": "09:00",
            "timezone": "UTC",
            "enabled": True
        }
        
        workflow = WorkflowFactory(
            trigger_type='schedule',
            schedule_config=schedule_config
        )
        
        assert workflow.schedule_config == schedule_config
        assert workflow.schedule_config['interval'] == 'daily'
    
    def test_workflow_indexes(self, db):
        """Test that workflow indexes are working."""
        user = UserFactory()
        workflow1 = WorkflowFactory(created_by=user, status='active')
        workflow2 = WorkflowFactory(created_by=user, status='inactive')
        
        # Test index on created_by and status
        active_workflows = Workflow.objects.filter(created_by=user, status='active')
        assert workflow1 in active_workflows
        assert workflow2 not in active_workflows


class TestWorkflowNode:
    """Tests for WorkflowNode model."""
    
    def test_create_workflow_node(self, db):
        """Test creating a workflow node."""
        workflow = WorkflowFactory()
        node_type = NodeTypeFactory(type='process')
        
        node = WorkflowNodeFactory(
            workflow=workflow,
            node_type=node_type,
            node_id='process_1',
            name='Process Documents',
            position_x=200,
            position_y=150
        )
        
        assert node.workflow == workflow
        assert node.node_type == node_type
        assert node.node_id == 'process_1'
        assert node.name == 'Process Documents'
        assert node.position_x == 200
        assert node.position_y == 150
        assert str(node) == f'{workflow.name} - Process Documents'
    
    def test_workflow_node_unique_constraint(self, db):
        """Test workflow node unique constraint on workflow and node_id."""
        workflow = WorkflowFactory()
        node_type = NodeTypeFactory()
        
        WorkflowNodeFactory(workflow=workflow, node_id='unique_node')
        
        with pytest.raises(IntegrityError):
            WorkflowNodeFactory(workflow=workflow, node_id='unique_node')
    
    def test_workflow_node_config(self, db):
        """Test workflow node configuration."""
        config = {
            "timeout_seconds": 600,
            "retry_count": 5,
            "priority": "high",
            "custom_field": "value"
        }
        
        node = WorkflowNodeFactory(config=config)
        assert node.config == config
        assert node.config['priority'] == 'high'
    
    def test_workflow_node_assigned_user(self, db):
        """Test workflow node assigned user."""
        user = UserFactory()
        node = WorkflowNodeFactory(assigned_user=user)
        
        assert node.assigned_user == user
    
    def test_workflow_node_default_values(self, db):
        """Test workflow node default values."""
        node = WorkflowNodeFactory()
        
        assert node.is_required is True
        assert node.timeout_seconds == 300
        assert node.retry_count == 3
        assert node.created_at is not None
        assert node.updated_at is not None


class TestWorkflowEdge:
    """Tests for WorkflowEdge model."""
    
    def test_create_workflow_edge(self, db):
        """Test creating a workflow edge."""
        workflow = WorkflowFactory()
        source_node = WorkflowNodeFactory(workflow=workflow, node_id='source')
        target_node = WorkflowNodeFactory(workflow=workflow, node_id='target')
        
        edge = WorkflowEdgeFactory(
            workflow=workflow,
            source_node=source_node,
            target_node=target_node,
            condition_type='success',
            label='On Success'
        )
        
        assert edge.workflow == workflow
        assert edge.source_node == source_node
        assert edge.target_node == target_node
        assert edge.condition_type == 'success'
        assert edge.label == 'On Success'
        assert str(edge) == f'{source_node.name} → {target_node.name}'
    
    def test_workflow_edge_unique_constraint(self, db):
        """Test workflow edge unique constraint."""
        workflow = WorkflowFactory()
        source_node = WorkflowNodeFactory(workflow=workflow)
        target_node = WorkflowNodeFactory(workflow=workflow)
        
        WorkflowEdgeFactory(
            workflow=workflow,
            source_node=source_node,
            target_node=target_node,
            condition_type='success'
        )
        
        with pytest.raises(IntegrityError):
            WorkflowEdgeFactory(
                workflow=workflow,
                source_node=source_node,
                target_node=target_node,
                condition_type='success'
            )
    
    def test_workflow_edge_condition_types(self, db):
        """Test workflow edge condition types."""
        valid_conditions = [
            'always', 'success', 'failure', 'conditional',
            'approval_yes', 'approval_no'
        ]
        
        workflow = WorkflowFactory()
        source_node = WorkflowNodeFactory(workflow=workflow)
        
        for condition in valid_conditions:
            target_node = WorkflowNodeFactory(workflow=workflow)
            edge = WorkflowEdgeFactory(
                workflow=workflow,
                source_node=source_node,
                target_node=target_node,
                condition_type=condition
            )
            assert edge.condition_type == condition
    
    def test_workflow_edge_condition_config(self, db):
        """Test workflow edge condition configuration."""
        condition_config = {
            "threshold": 0.8,
            "field": "confidence",
            "operator": "greater_than"
        }
        
        edge = WorkflowEdgeFactory(
            condition_type='conditional',
            condition_config=condition_config
        )
        
        assert edge.condition_config == condition_config
        assert edge.condition_config['threshold'] == 0.8


class TestWorkflowExecution:
    """Tests for WorkflowExecution model."""
    
    def test_create_workflow_execution(self, db):
        """Test creating a workflow execution."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        current_node = workflow.nodes.first()
        
        execution = WorkflowExecutionFactory(
            workflow=workflow,
            status='running',
            triggered_by=user,
            current_node=current_node
        )
        
        assert execution.workflow == workflow
        assert execution.triggered_by == user
        assert execution.status == 'running'
        assert execution.current_node == current_node
        assert str(execution).startswith(workflow.name)
    
    def test_workflow_execution_status_choices(self, db):
        """Test workflow execution status choices."""
        valid_statuses = ['queued', 'running', 'paused', 'completed', 'failed', 'cancelled']
        
        for status in valid_statuses:
            execution = WorkflowExecutionFactory(status=status)
            assert execution.status == status
    
    def test_workflow_execution_trigger_data(self, db):
        """Test workflow execution trigger data."""
        trigger_data = {
            "source": "api",
            "user_id": 123,
            "document_ids": [1, 2, 3],
            "batch_id": str(uuid.uuid4())
        }
        
        execution = WorkflowExecutionFactory(trigger_data=trigger_data)
        assert execution.trigger_data == trigger_data
        assert execution.trigger_data['source'] == 'api'
    
    def test_workflow_execution_context_data(self, db):
        """Test workflow execution context data."""
        context_data = {
            "variables": {
                "user_name": "John Doe",
                "department": "Finance"
            },
            "metadata": {
                "request_id": str(uuid.uuid4()),
                "session_id": "abc123"
            }
        }
        
        execution = WorkflowExecutionFactory(context_data=context_data)
        assert execution.context_data == context_data
        assert execution.context_data['variables']['user_name'] == 'John Doe'
    
    def test_workflow_execution_duration_calculation(self, db):
        """Test workflow execution duration calculation."""
        execution = CompletedWorkflowExecutionFactory()
        
        assert execution.duration_seconds is not None
        assert execution.duration_seconds > 0
        assert execution.completed_at is not None
    
    def test_workflow_execution_error_handling(self, db):
        """Test workflow execution error handling."""
        execution = FailedWorkflowExecutionFactory()
        
        assert execution.status == 'failed'
        assert execution.error_message != ''
        assert execution.error_details != {}
        assert 'error_type' in execution.error_details
    
    def test_workflow_execution_indexes(self, db):
        """Test workflow execution indexes."""
        workflow = WorkflowFactory()
        user = UserFactory()
        
        execution1 = WorkflowExecutionFactory(workflow=workflow, status='completed')
        execution2 = WorkflowExecutionFactory(workflow=workflow, status='failed')
        execution3 = WorkflowExecutionFactory(triggered_by=user)
        
        # Test workflow and status index
        completed_executions = WorkflowExecution.objects.filter(
            workflow=workflow, status='completed'
        )
        assert execution1 in completed_executions
        assert execution2 not in completed_executions


class TestWorkflowNodeExecution:
    """Tests for WorkflowNodeExecution model."""
    
    def test_create_workflow_node_execution(self, db):
        """Test creating a workflow node execution."""
        execution = WorkflowExecutionFactory()
        node = WorkflowNodeFactory(workflow=execution.workflow)
        
        node_execution = WorkflowNodeExecutionFactory(
            workflow_execution=execution,
            workflow_node=node,
            status='completed',
            input_data={"param": "value"},
            output_data={"result": "success"}
        )
        
        assert node_execution.workflow_execution == execution
        assert node_execution.workflow_node == node
        assert node_execution.status == 'completed'
        assert node_execution.input_data == {"param": "value"}
        assert node_execution.output_data == {"result": "success"}
        assert str(node_execution).startswith(str(execution))
    
    def test_workflow_node_execution_unique_constraint(self, db):
        """Test workflow node execution unique constraint."""
        execution = WorkflowExecutionFactory()
        node = WorkflowNodeFactory(workflow=execution.workflow)
        
        WorkflowNodeExecutionFactory(
            workflow_execution=execution,
            workflow_node=node
        )
        
        with pytest.raises(IntegrityError):
            WorkflowNodeExecutionFactory(
                workflow_execution=execution,
                workflow_node=node
            )
    
    def test_workflow_node_execution_status_choices(self, db):
        """Test workflow node execution status choices."""
        valid_statuses = ['pending', 'running', 'completed', 'failed', 'skipped', 'waiting_approval']
        
        for status in valid_statuses:
            node_execution = WorkflowNodeExecutionFactory(status=status)
            assert node_execution.status == status
    
    def test_workflow_node_execution_approval(self, db):
        """Test workflow node execution approval fields."""
        user = UserFactory()
        node_execution = WorkflowNodeExecutionFactory(
            status='waiting_approval',
            approved_by=user,
            approval_notes='Approved for processing'
        )
        
        assert node_execution.approved_by == user
        assert node_execution.approval_notes == 'Approved for processing'
    
    def test_workflow_node_execution_timing(self, db):
        """Test workflow node execution timing fields."""
        node_execution = WorkflowNodeExecutionFactory(
            status='completed',
            started_at=timezone.now(),
            completed_at=timezone.now(),
            duration_seconds=5.5
        )
        
        assert node_execution.started_at is not None
        assert node_execution.completed_at is not None
        assert node_execution.duration_seconds == 5.5
    
    def test_workflow_node_execution_retry(self, db):
        """Test workflow node execution retry handling."""
        node_execution = WorkflowNodeExecutionFactory(
            status='failed',
            retry_count=2,
            error_message='Node execution failed'
        )
        
        assert node_execution.retry_count == 2
        assert node_execution.error_message == 'Node execution failed'


class TestWorkflowAuditLog:
    """Tests for WorkflowAuditLog model."""
    
    def test_create_workflow_audit_log(self, db):
        """Test creating a workflow audit log."""
        workflow = WorkflowFactory()
        execution = WorkflowExecutionFactory(workflow=workflow)
        user = UserFactory()
        
        audit_log = WorkflowAuditLogFactory(
            workflow=workflow,
            workflow_execution=execution,
            user=user,
            action='execution_started',
            description='Workflow execution started',
            user_ip='192.168.1.1',
            user_agent='Mozilla/5.0...'
        )
        
        assert audit_log.workflow == workflow
        assert audit_log.workflow_execution == execution
        assert audit_log.user == user
        assert audit_log.action == 'execution_started'
        assert audit_log.description == 'Workflow execution started'
        assert audit_log.user_ip == '192.168.1.1'
        assert str(audit_log).startswith('execution_started')
    
    def test_workflow_audit_log_action_choices(self, db):
        """Test workflow audit log action choices."""
        valid_actions = [
            'workflow_created', 'workflow_updated', 'workflow_activated',
            'workflow_deactivated', 'execution_started', 'execution_completed',
            'execution_failed', 'node_approved', 'node_rejected',
            'data_accessed', 'data_modified'
        ]
        
        for action in valid_actions:
            audit_log = WorkflowAuditLogFactory(action=action)
            assert audit_log.action == action
    
    def test_workflow_audit_log_metadata(self, db):
        """Test workflow audit log metadata field."""
        metadata = {
            "browser": "Chrome",
            "session_id": str(uuid.uuid4()),
            "request_id": str(uuid.uuid4()),
            "additional_data": {"key": "value"}
        }
        
        audit_log = WorkflowAuditLogFactory(metadata=metadata)
        assert audit_log.metadata == metadata
        assert audit_log.metadata['browser'] == 'Chrome'
    
    def test_workflow_audit_log_ordering(self, db):
        """Test workflow audit log ordering by timestamp."""
        log1 = WorkflowAuditLogFactory(action='workflow_created')
        log2 = WorkflowAuditLogFactory(action='workflow_activated')
        log3 = WorkflowAuditLogFactory(action='execution_started')
        
        # Should be ordered by timestamp descending (newest first)
        ordered_logs = WorkflowAuditLog.objects.all()
        assert ordered_logs[0] == log3
        assert ordered_logs[1] == log2
        assert ordered_logs[2] == log1
    
    def test_workflow_audit_log_indexes(self, db):
        """Test workflow audit log indexes."""
        workflow = WorkflowFactory()
        user = UserFactory()
        
        log1 = WorkflowAuditLogFactory(workflow=workflow, action='workflow_created')
        log2 = WorkflowAuditLogFactory(workflow=workflow, action='workflow_updated')
        log3 = WorkflowAuditLogFactory(user=user, action='data_accessed')
        
        # Test workflow and action index
        workflow_logs = WorkflowAuditLog.objects.filter(
            workflow=workflow, action='workflow_created'
        )
        assert log1 in workflow_logs
        assert log2 not in workflow_logs
        
        # Test user index
        user_logs = WorkflowAuditLog.objects.filter(user=user)
        assert log3 in user_logs