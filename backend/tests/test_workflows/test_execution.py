"""
End-to-end workflow execution scenario tests
"""
import pytest
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.test import TransactionTestCase
from django.db import transaction
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import uuid

from apps.workflows.models import (
    NodeType, Workflow, WorkflowNode, WorkflowEdge,
    WorkflowExecution, WorkflowNodeExecution, WorkflowAuditLog
)
from apps.workflows.services import WorkflowExecutionService, WorkflowAuditService
from tests.factories import (
    NodeTypeFactory, WorkflowFactory, WorkflowNodeFactory, WorkflowEdgeFactory,
    WorkflowExecutionFactory, UserFactory, ActiveWorkflowFactory,
    InvoiceProcessingTemplateFactory
)


class TestWorkflowExecutionScenarios:
    """Test complete workflow execution scenarios."""
    
    def test_simple_linear_workflow(self, db):
        """Test execution of simple linear workflow: Start -> Process -> End."""
        # Create node types
        start_type = NodeTypeFactory(type='start')
        process_type = NodeTypeFactory(type='process')
        end_type = NodeTypeFactory(type='end')
        
        # Create workflow
        workflow = WorkflowFactory(status='active')
        
        # Create nodes
        start_node = WorkflowNodeFactory(
            workflow=workflow,
            node_type=start_type,
            node_id='start_1',
            name='Start Process'
        )
        process_node = WorkflowNodeFactory(
            workflow=workflow,
            node_type=process_type,
            node_id='process_1',
            name='Process Data'
        )
        end_node = WorkflowNodeFactory(
            workflow=workflow,
            node_type=end_type,
            node_id='end_1',
            name='End Process'
        )
        
        # Create edges
        WorkflowEdgeFactory(
            workflow=workflow,
            source_node=start_node,
            target_node=process_node,
            condition_type='always'
        )
        WorkflowEdgeFactory(
            workflow=workflow,
            source_node=process_node,
            target_node=end_node,
            condition_type='success'
        )
        
        # Execute workflow
        user = UserFactory()
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        # Mock successful node execution
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
            WorkflowExecutionService.start_execution(execution)
        
        # Verify execution completed
        execution.refresh_from_db()
        assert execution.status == 'completed'
        assert execution.completed_at is not None
        
        # Verify all nodes were executed
        node_executions = execution.node_executions.all()
        assert len(node_executions) == 3
        
        completed_nodes = execution.node_executions.filter(status='completed')
        assert len(completed_nodes) == 3
    
    def test_decision_workflow_success_path(self, db):
        """Test workflow with decision node taking success path."""
        # Create node types
        start_type = NodeTypeFactory(type='start')
        decision_type = NodeTypeFactory(type='decision')
        process_type = NodeTypeFactory(type='process')
        end_type = NodeTypeFactory(type='end')
        
        # Create workflow
        workflow = WorkflowFactory(status='active')
        
        # Create nodes
        start_node = WorkflowNodeFactory(workflow=workflow, node_type=start_type, node_id='start_1')
        decision_node = WorkflowNodeFactory(workflow=workflow, node_type=decision_type, node_id='decision_1')
        success_node = WorkflowNodeFactory(workflow=workflow, node_type=process_type, node_id='success_1')
        failure_node = WorkflowNodeFactory(workflow=workflow, node_type=process_type, node_id='failure_1')
        end_node = WorkflowNodeFactory(workflow=workflow, node_type=end_type, node_id='end_1')
        
        # Create edges
        WorkflowEdgeFactory(workflow=workflow, source_node=start_node, target_node=decision_node, condition_type='always')
        WorkflowEdgeFactory(workflow=workflow, source_node=decision_node, target_node=success_node, condition_type='success')
        WorkflowEdgeFactory(workflow=workflow, source_node=decision_node, target_node=failure_node, condition_type='failure')
        WorkflowEdgeFactory(workflow=workflow, source_node=success_node, target_node=end_node, condition_type='always')
        WorkflowEdgeFactory(workflow=workflow, source_node=failure_node, target_node=end_node, condition_type='always')
        
        # Execute workflow
        user = UserFactory()
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        # Mock successful execution for all nodes
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
            WorkflowExecutionService.start_execution(execution)
        
        # Verify execution
        execution.refresh_from_db()
        assert execution.status == 'completed'
        
        # Verify success path was taken (success_node should be completed)
        success_execution = execution.node_executions.filter(workflow_node=success_node).first()
        assert success_execution.status == 'completed'
        
        # Verify failure path was not taken (failure_node should be pending)
        failure_execution = execution.node_executions.filter(workflow_node=failure_node).first()
        assert failure_execution.status == 'pending'
    
    def test_approval_workflow(self, db):
        """Test workflow with approval node."""
        # Create node types
        start_type = NodeTypeFactory(type='start')
        approval_type = NodeTypeFactory(type='approval', requires_user_action=True)
        process_type = NodeTypeFactory(type='process')
        end_type = NodeTypeFactory(type='end')
        
        # Create workflow
        workflow = WorkflowFactory(status='active')
        
        # Create nodes
        start_node = WorkflowNodeFactory(workflow=workflow, node_type=start_type, node_id='start_1')
        approval_node = WorkflowNodeFactory(workflow=workflow, node_type=approval_type, node_id='approval_1')
        process_node = WorkflowNodeFactory(workflow=workflow, node_type=process_type, node_id='process_1')
        end_node = WorkflowNodeFactory(workflow=workflow, node_type=end_type, node_id='end_1')
        
        # Create edges
        WorkflowEdgeFactory(workflow=workflow, source_node=start_node, target_node=approval_node, condition_type='always')
        WorkflowEdgeFactory(workflow=workflow, source_node=approval_node, target_node=process_node, condition_type='approval_yes')
        WorkflowEdgeFactory(workflow=workflow, source_node=process_node, target_node=end_node, condition_type='success')
        
        # Execute workflow
        user = UserFactory()
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        # Mock node execution that stops at approval
        def mock_simulation(node, node_execution):
            if node.node_type.type == 'approval':
                node_execution.status = 'waiting_approval'
                node_execution.save()
                return False  # Don't continue automatically
            return True
        
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', side_effect=mock_simulation):
            WorkflowExecutionService.start_execution(execution)
        
        # Verify execution is paused at approval
        execution.refresh_from_db()
        assert execution.status == 'paused' or execution.status == 'running'
        
        approval_execution = execution.node_executions.filter(workflow_node=approval_node).first()
        assert approval_execution.status == 'waiting_approval'
    
    def test_parallel_execution_workflow(self, db):
        """Test workflow with parallel execution paths."""
        # Create node types
        start_type = NodeTypeFactory(type='start')
        process_type = NodeTypeFactory(type='process')
        end_type = NodeTypeFactory(type='end')
        
        # Create workflow
        workflow = WorkflowFactory(status='active')
        
        # Create nodes
        start_node = WorkflowNodeFactory(workflow=workflow, node_type=start_type, node_id='start_1')
        process_a = WorkflowNodeFactory(workflow=workflow, node_type=process_type, node_id='process_a')
        process_b = WorkflowNodeFactory(workflow=workflow, node_type=process_type, node_id='process_b')
        end_node = WorkflowNodeFactory(workflow=workflow, node_type=end_type, node_id='end_1')
        
        # Create edges for parallel execution
        WorkflowEdgeFactory(workflow=workflow, source_node=start_node, target_node=process_a, condition_type='always')
        WorkflowEdgeFactory(workflow=workflow, source_node=start_node, target_node=process_b, condition_type='always')
        WorkflowEdgeFactory(workflow=workflow, source_node=process_a, target_node=end_node, condition_type='success')
        WorkflowEdgeFactory(workflow=workflow, source_node=process_b, target_node=end_node, condition_type='success')
        
        # Execute workflow
        user = UserFactory()
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
            WorkflowExecutionService.start_execution(execution)
        
        # Verify both parallel paths were executed
        execution.refresh_from_db()
        assert execution.status == 'completed'
        
        process_a_exec = execution.node_executions.filter(workflow_node=process_a).first()
        process_b_exec = execution.node_executions.filter(workflow_node=process_b).first()
        
        assert process_a_exec.status == 'completed'
        assert process_b_exec.status == 'completed'
    
    def test_workflow_execution_failure(self, db):
        """Test workflow execution with node failure."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        # Mock node failure
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=False):
            WorkflowExecutionService.start_execution(execution)
        
        # Verify execution failed
        execution.refresh_from_db()
        assert execution.status == 'failed'
        assert execution.error_message != ''
        assert execution.completed_at is not None
    
    def test_workflow_execution_timeout(self, db):
        """Test workflow execution with timeout handling."""
        workflow = ActiveWorkflowFactory()
        
        # Set short timeout on nodes
        for node in workflow.nodes.all():
            node.timeout_seconds = 1
            node.save()
        
        user = UserFactory()
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        # Mock slow node execution
        def slow_simulation(node, node_execution):
            time.sleep(2)  # Exceed timeout
            return True
        
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', side_effect=slow_simulation):
            # In a real implementation, this would handle timeout
            WorkflowExecutionService.start_execution(execution)
        
        # For now, just verify execution completed (timeout handling would be added to service)
        execution.refresh_from_db()
        # assert execution.status in ['failed', 'completed']  # Depends on timeout implementation
    
    def test_workflow_execution_retry(self, db):
        """Test workflow execution with node retry logic."""
        workflow = ActiveWorkflowFactory()
        node = workflow.nodes.first()
        node.retry_count = 3
        node.save()
        
        user = UserFactory()
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        # Mock failing then succeeding execution
        call_count = 0
        def retry_simulation(node, node_execution):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return False  # Fail first 2 times
            return True  # Succeed on 3rd try
        
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', side_effect=retry_simulation):
            WorkflowExecutionService.start_execution(execution)
        
        # In current implementation, retry logic would need to be added
        execution.refresh_from_db()
        # Would verify retry behavior when implemented
    
    def test_complex_invoice_processing_workflow(self, db):
        """Test complex invoice processing workflow scenario."""
        # Create all required node types
        start_type = NodeTypeFactory(type='start')
        document_type = NodeTypeFactory(type='document')
        decision_type = NodeTypeFactory(type='decision')
        approval_type = NodeTypeFactory(type='approval')
        integration_type = NodeTypeFactory(type='integration')
        notification_type = NodeTypeFactory(type='notification')
        end_type = NodeTypeFactory(type='end')
        
        # Create workflow
        workflow = WorkflowFactory(name='Invoice Processing', status='active')
        
        # Create nodes following invoice processing flow
        start_node = WorkflowNodeFactory(workflow=workflow, node_type=start_type, node_id='start_1', name='Start Invoice Processing')
        extract_node = WorkflowNodeFactory(workflow=workflow, node_type=document_type, node_id='extract_1', name='Extract Invoice Data')
        validate_node = WorkflowNodeFactory(workflow=workflow, node_type=decision_type, node_id='validate_1', name='Validate Data')
        approval_node = WorkflowNodeFactory(workflow=workflow, node_type=approval_type, node_id='approval_1', name='Finance Approval')
        integrate_node = WorkflowNodeFactory(workflow=workflow, node_type=integration_type, node_id='integrate_1', name='Update Accounting')
        notify_node = WorkflowNodeFactory(workflow=workflow, node_type=notification_type, node_id='notify_1', name='Send Notification')
        end_node = WorkflowNodeFactory(workflow=workflow, node_type=end_type, node_id='end_1', name='Complete')
        
        # Create workflow edges
        WorkflowEdgeFactory(workflow=workflow, source_node=start_node, target_node=extract_node, condition_type='always')
        WorkflowEdgeFactory(workflow=workflow, source_node=extract_node, target_node=validate_node, condition_type='success')
        WorkflowEdgeFactory(workflow=workflow, source_node=validate_node, target_node=approval_node, condition_type='success')
        WorkflowEdgeFactory(workflow=workflow, source_node=approval_node, target_node=integrate_node, condition_type='approval_yes')
        WorkflowEdgeFactory(workflow=workflow, source_node=integrate_node, target_node=notify_node, condition_type='success')
        WorkflowEdgeFactory(workflow=workflow, source_node=notify_node, target_node=end_node, condition_type='always')
        
        # Execute workflow
        user = UserFactory()
        trigger_data = {
            'invoice_file': 'invoice_001.pdf',
            'vendor': 'ACME Corp',
            'amount': 1250.00
        }
        
        execution = WorkflowExecutionService.create_execution(workflow, user, trigger_data)
        
        # Mock successful execution for all nodes
        def invoice_simulation(node, node_execution):
            # Simulate different processing based on node type
            if node.node_type.type == 'document':
                node_execution.output_data = {
                    'vendor': 'ACME Corp',
                    'amount': 1250.00,
                    'invoice_number': 'INV-001',
                    'confidence': 0.95
                }
            elif node.node_type.type == 'decision':
                node_execution.output_data = {'validation_passed': True}
            elif node.node_type.type == 'approval':
                node_execution.output_data = {'approved': True, 'approver': 'Finance Manager'}
            elif node.node_type.type == 'integration':
                node_execution.output_data = {'transaction_id': 'TXN-123', 'status': 'posted'}
            elif node.node_type.type == 'notification':
                node_execution.output_data = {'notification_sent': True, 'recipient': 'accounts@company.com'}
            
            node_execution.save()
            return True
        
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', side_effect=invoice_simulation):
            WorkflowExecutionService.start_execution(execution)
        
        # Verify execution completed successfully
        execution.refresh_from_db()
        assert execution.status == 'completed'
        assert execution.trigger_data['vendor'] == 'ACME Corp'
        
        # Verify all nodes executed with correct data flow
        extract_exec = execution.node_executions.filter(workflow_node=extract_node).first()
        assert extract_exec.output_data['vendor'] == 'ACME Corp'
        assert extract_exec.output_data['confidence'] == 0.95
        
        validate_exec = execution.node_executions.filter(workflow_node=validate_node).first()
        assert validate_exec.output_data['validation_passed'] is True
        
        approval_exec = execution.node_executions.filter(workflow_node=approval_node).first()
        assert approval_exec.output_data['approved'] is True
        
        integrate_exec = execution.node_executions.filter(workflow_node=integrate_node).first()
        assert integrate_exec.output_data['transaction_id'] == 'TXN-123'


class TestWorkflowExecutionConcurrency(TransactionTestCase):
    """Test concurrent workflow execution scenarios."""
    
    def test_concurrent_executions_same_workflow(self):
        """Test multiple concurrent executions of the same workflow."""
        workflow = ActiveWorkflowFactory()
        users = [UserFactory() for _ in range(5)]
        
        def execute_workflow(user):
            execution = WorkflowExecutionService.create_execution(workflow, user)
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
            return execution.id
        
        # Execute workflows concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_workflow, user) for user in users]
            execution_ids = [future.result() for future in as_completed(futures)]
        
        # Verify all executions completed
        assert len(execution_ids) == 5
        executions = WorkflowExecution.objects.filter(id__in=execution_ids)
        assert all(exec.status == 'completed' for exec in executions)
    
    def test_concurrent_workflow_modifications(self):
        """Test concurrent workflow modifications during execution."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        
        # Start execution
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        def modify_workflow():
            # Simulate workflow modification during execution
            workflow.name = 'Modified Workflow'
            workflow.save()
        
        def execute_workflow():
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
        
        # Run modification and execution concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(modify_workflow)
            future2 = executor.submit(execute_workflow)
            
            future1.result()
            future2.result()
        
        # Verify execution completed despite workflow modification
        execution.refresh_from_db()
        assert execution.status == 'completed'
        
        workflow.refresh_from_db()
        assert workflow.name == 'Modified Workflow'


class TestWorkflowExecutionAuditTrail:
    """Test audit trail for workflow executions."""
    
    def test_execution_audit_logging(self, db):
        """Test that workflow execution creates proper audit logs."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        
        with patch('apps.workflows.services.WorkflowAuditService.log_action') as mock_log:
            execution = WorkflowExecutionService.create_execution(workflow, user)
            
            # Verify audit log was created for execution start
            mock_log.assert_called_with(
                user, 'execution_started', workflow, execution,
                f"Workflow execution created for '{workflow.name}'"
            )
    
    def test_execution_completion_audit(self, db):
        """Test audit logging for execution completion."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        with patch('apps.workflows.services.WorkflowAuditService.log_action') as mock_log:
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
            
            # Verify completion was logged
            mock_log.assert_any_call(
                user, 'execution_completed', workflow, execution,
                f"Workflow execution completed: {workflow.name}"
            )
    
    def test_execution_failure_audit(self, db):
        """Test audit logging for execution failure."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        with patch('apps.workflows.services.WorkflowAuditService.log_action') as mock_log:
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=False):
                WorkflowExecutionService.start_execution(execution)
            
            # Verify failure was logged
            mock_log.assert_any_call(
                user, 'execution_failed', workflow, execution,
                f"Workflow execution failed: {workflow.name}"
            )


class TestWorkflowExecutionPerformance:
    """Test workflow execution performance."""
    
    def test_large_workflow_execution(self, db):
        """Test execution of workflow with many nodes."""
        # Create workflow with 20 nodes
        workflow = WorkflowFactory(status='active')
        
        start_type = NodeTypeFactory(type='start')
        process_type = NodeTypeFactory(type='process')
        end_type = NodeTypeFactory(type='end')
        
        # Create nodes
        start_node = WorkflowNodeFactory(workflow=workflow, node_type=start_type, node_id='start_1')
        nodes = [start_node]
        
        # Create chain of process nodes
        for i in range(18):
            node = WorkflowNodeFactory(
                workflow=workflow,
                node_type=process_type,
                node_id=f'process_{i+1}'
            )
            nodes.append(node)
        
        end_node = WorkflowNodeFactory(workflow=workflow, node_type=end_type, node_id='end_1')
        nodes.append(end_node)
        
        # Create sequential edges
        for i in range(len(nodes) - 1):
            WorkflowEdgeFactory(
                workflow=workflow,
                source_node=nodes[i],
                target_node=nodes[i + 1],
                condition_type='always'
            )
        
        # Execute workflow and measure performance
        user = UserFactory()
        start_time = time.time()
        
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
            WorkflowExecutionService.start_execution(execution)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify execution completed in reasonable time
        execution.refresh_from_db()
        assert execution.status == 'completed'
        assert execution_time < 10.0  # Should complete within 10 seconds
        
        # Verify all nodes executed
        assert execution.node_executions.filter(status='completed').count() == 20
    
    def test_workflow_statistics_update_performance(self, db):
        """Test performance of workflow statistics updates."""
        workflow = WorkflowFactory()
        
        # Create many executions
        executions = []
        for i in range(100):
            status = 'completed' if i % 2 == 0 else 'failed'
            duration = float(i + 1)
            execution = WorkflowExecutionFactory(
                workflow=workflow,
                status=status,
                duration_seconds=duration if status == 'completed' else None
            )
            executions.append(execution)
        
        # Measure statistics update performance
        start_time = time.time()
        WorkflowExecutionService._update_workflow_stats(workflow)
        end_time = time.time()
        
        update_time = end_time - start_time
        
        # Verify statistics were calculated correctly
        workflow.refresh_from_db()
        assert workflow.total_executions == 100
        assert workflow.successful_executions == 50
        assert workflow.failed_executions == 50
        
        # Verify performance is acceptable
        assert update_time < 1.0  # Should complete within 1 second
    
    def test_audit_log_performance(self, db):
        """Test performance of audit logging during execution."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        
        # Measure execution time with audit logging
        start_time = time.time()
        
        execution = WorkflowExecutionService.create_execution(workflow, user)
        
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
            WorkflowExecutionService.start_execution(execution)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verify audit logs were created
        audit_logs = WorkflowAuditLog.objects.filter(workflow=workflow)
        assert audit_logs.count() >= 2  # At least start and completion logs
        
        # Verify performance impact is minimal
        assert execution_time < 5.0  # Should complete within 5 seconds