"""
Performance and load testing for workflow execution
"""
import pytest
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from django.db import connection
from django.test.utils import override_settings
from unittest.mock import patch, MagicMock
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
import psutil
import os

from apps.workflows.models import (
    Workflow, WorkflowExecution, WorkflowNode, WorkflowNodeExecution
)
from apps.workflows.services import (
    WorkflowExecutionService, WorkflowMonitoringService
)
from tests.factories import (
    BulkWorkflowFactory, ActiveWorkflowFactory, WorkflowExecutionFactory,
    UserFactory, WorkflowFactory, WorkflowNodeFactory, NodeTypeFactory,
    CompletedWorkflowExecutionFactory
)


@contextmanager
def track_performance():
    """Context manager to track performance metrics."""
    process = psutil.Process()
    
    # Initial metrics
    start_time = time.time()
    start_memory = process.memory_info().rss / 1024 / 1024  # MB
    start_queries = len(connection.queries)
    
    yield
    
    # Final metrics
    end_time = time.time()
    end_memory = process.memory_info().rss / 1024 / 1024  # MB
    end_queries = len(connection.queries)
    
    execution_time = end_time - start_time
    memory_used = end_memory - start_memory
    queries_executed = end_queries - start_queries
    
    print(f"Performance Metrics:")
    print(f"  Execution Time: {execution_time:.3f} seconds")
    print(f"  Memory Used: {memory_used:.2f} MB")
    print(f"  Database Queries: {queries_executed}")


class TestWorkflowExecutionPerformance:
    """Test workflow execution performance under various loads."""
    
    @pytest.mark.performance
    def test_single_workflow_execution_performance(self, db):
        """Test performance of single workflow execution."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        
        with track_performance():
            execution = WorkflowExecutionService.create_execution(workflow, user)
            
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
        
        # Verify execution completed
        execution.refresh_from_db()
        assert execution.status == 'completed'
    
    @pytest.mark.performance
    def test_multiple_workflow_executions_performance(self, db):
        """Test performance of multiple sequential workflow executions."""
        workflow = ActiveWorkflowFactory()
        users = [UserFactory() for _ in range(10)]
        
        execution_times = []
        
        for user in users:
            start_time = time.time()
            
            execution = WorkflowExecutionService.create_execution(workflow, user)
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
            
            end_time = time.time()
            execution_times.append(end_time - start_time)
            
            execution.refresh_from_db()
            assert execution.status == 'completed'
        
        # Analyze performance
        avg_time = statistics.mean(execution_times)
        max_time = max(execution_times)
        min_time = min(execution_times)
        
        print(f"Execution Performance (10 workflows):")
        print(f"  Average: {avg_time:.3f}s")
        print(f"  Min: {min_time:.3f}s") 
        print(f"  Max: {max_time:.3f}s")
        
        # Performance assertions
        assert avg_time < 1.0  # Average should be under 1 second
        assert max_time < 2.0  # No execution should take more than 2 seconds
    
    @pytest.mark.performance
    def test_complex_workflow_performance(self, db):
        """Test performance with complex workflow (many nodes)."""
        # Create workflow with 50 nodes
        workflow = WorkflowFactory(status='active')
        
        start_type = NodeTypeFactory(type='start')
        process_type = NodeTypeFactory(type='process')
        end_type = NodeTypeFactory(type='end')
        
        # Create start node
        start_node = WorkflowNodeFactory(
            workflow=workflow,
            node_type=start_type,
            node_id='start_1'
        )
        
        # Create chain of process nodes
        nodes = [start_node]
        for i in range(48):  # 48 process nodes
            node = WorkflowNodeFactory(
                workflow=workflow,
                node_type=process_type,
                node_id=f'process_{i+1}'
            )
            nodes.append(node)
        
        # Create end node
        end_node = WorkflowNodeFactory(
            workflow=workflow,
            node_type=end_type,
            node_id='end_1'
        )
        nodes.append(end_node)
        
        # Create sequential edges
        from apps.workflows.models import WorkflowEdge
        for i in range(len(nodes) - 1):
            WorkflowEdge.objects.create(
                workflow=workflow,
                source_node=nodes[i],
                target_node=nodes[i + 1],
                condition_type='always'
            )
        
        user = UserFactory()
        
        with track_performance():
            execution = WorkflowExecutionService.create_execution(workflow, user)
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
        
        # Verify execution completed
        execution.refresh_from_db()
        assert execution.status == 'completed'
        assert execution.node_executions.count() == 50
        assert execution.node_executions.filter(status='completed').count() == 50
    
    @pytest.mark.performance
    @override_settings(DEBUG=True)  # Enable query logging
    def test_workflow_query_optimization(self, db):
        """Test database query optimization for workflow operations."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        
        # Clear existing queries
        connection.queries.clear()
        
        # Execute workflow and count queries
        execution = WorkflowExecutionService.create_execution(workflow, user)
        create_queries = len(connection.queries)
        
        connection.queries.clear()
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
            WorkflowExecutionService.start_execution(execution)
        execution_queries = len(connection.queries)
        
        print(f"Query Optimization:")
        print(f"  Creation queries: {create_queries}")
        print(f"  Execution queries: {execution_queries}")
        print(f"  Total queries: {create_queries + execution_queries}")
        
        # Verify query efficiency
        assert create_queries < 20  # Creation should be efficient
        assert execution_queries < 30  # Execution should be efficient
    
    @pytest.mark.performance
    def test_workflow_memory_usage(self, db):
        """Test memory usage during workflow execution."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create and execute multiple workflows
        workflows = []
        for i in range(20):
            workflow = ActiveWorkflowFactory()
            workflows.append(workflow)
            
            user = UserFactory()
            execution = WorkflowExecutionService.create_execution(workflow, user)
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory Usage:")
        print(f"  Initial: {initial_memory:.2f} MB")
        print(f"  Final: {final_memory:.2f} MB")
        print(f"  Increase: {memory_increase:.2f} MB")
        print(f"  Per workflow: {memory_increase/20:.2f} MB")
        
        # Verify memory usage is reasonable
        assert memory_increase < 100  # Should not use more than 100MB for 20 workflows
        assert memory_increase / 20 < 5  # Should not use more than 5MB per workflow


class TestConcurrentWorkflowExecution(TransactionTestCase):
    """Test concurrent workflow execution performance."""
    
    @pytest.mark.performance
    def test_concurrent_execution_performance(self):
        """Test performance of concurrent workflow executions."""
        workflow = ActiveWorkflowFactory()
        users = [UserFactory() for _ in range(10)]
        
        def execute_workflow(user):
            start_time = time.time()
            execution = WorkflowExecutionService.create_execution(workflow, user)
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
            end_time = time.time()
            
            execution.refresh_from_db()
            return {
                'execution_id': execution.id,
                'duration': end_time - start_time,
                'status': execution.status
            }
        
        start_time = time.time()
        
        # Execute workflows concurrently
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(execute_workflow, user) for user in users]
            results = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful = [r for r in results if r['status'] == 'completed']
        durations = [r['duration'] for r in results]
        
        avg_duration = statistics.mean(durations)
        max_duration = max(durations)
        
        print(f"Concurrent Execution Performance:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Successful executions: {len(successful)}/10")
        print(f"  Average duration: {avg_duration:.3f}s")
        print(f"  Max duration: {max_duration:.3f}s")
        print(f"  Concurrency benefit: {sum(durations)/total_time:.2f}x")
        
        # Performance assertions
        assert len(successful) == 10  # All should succeed
        assert total_time < sum(durations)  # Should be faster than sequential
        assert avg_duration < 2.0  # Individual executions should be fast
    
    @pytest.mark.performance
    def test_concurrent_workflow_creation_performance(self):
        """Test performance of concurrent workflow creation."""
        users = [UserFactory() for _ in range(20)]
        
        def create_and_execute_workflow(user):
            start_time = time.time()
            
            workflow = ActiveWorkflowFactory(created_by=user)
            execution = WorkflowExecutionService.create_execution(workflow, user)
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
            
            end_time = time.time()
            return end_time - start_time
        
        start_time = time.time()
        
        # Create and execute workflows concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_and_execute_workflow, user) for user in users]
            durations = [future.result() for future in as_completed(futures)]
        
        total_time = time.time() - start_time
        avg_duration = statistics.mean(durations)
        
        print(f"Concurrent Creation + Execution Performance:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average duration: {avg_duration:.3f}s")
        print(f"  Workflows created: {len(durations)}")
        
        # Verify all workflows were created and executed
        assert len(durations) == 20
        assert avg_duration < 3.0  # Should complete within 3 seconds each
    
    @pytest.mark.performance
    def test_database_connection_pooling(self):
        """Test database connection handling under concurrent load."""
        workflow = ActiveWorkflowFactory()
        
        def stress_test_execution():
            user = UserFactory()
            for _ in range(5):  # Each thread creates 5 executions
                execution = WorkflowExecutionService.create_execution(workflow, user)
                with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                    WorkflowExecutionService.start_execution(execution)
        
        # Run stress test with high concurrency
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(stress_test_execution) for _ in range(10)]
            
            # Wait for all to complete
            for future in as_completed(futures):
                future.result()  # Will raise if any failed
        
        # Verify all executions completed
        total_executions = WorkflowExecution.objects.count()
        completed_executions = WorkflowExecution.objects.filter(status='completed').count()
        
        print(f"Database Stress Test:")
        print(f"  Total executions: {total_executions}")
        print(f"  Completed executions: {completed_executions}")
        print(f"  Success rate: {completed_executions/total_executions*100:.1f}%")
        
        assert total_executions == 50  # 10 threads * 5 executions each
        assert completed_executions == total_executions  # All should succeed


class TestWorkflowScalabilityLimits:
    """Test workflow system scalability limits."""
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_large_scale_workflow_creation(self, db):
        """Test creating large numbers of workflows."""
        start_time = time.time()
        
        # Create 100 workflows using bulk factory
        workflows = BulkWorkflowFactory.create_workflows_batch(count=100, with_executions=False)
        
        creation_time = time.time() - start_time
        
        print(f"Large Scale Creation:")
        print(f"  Workflows created: {len(workflows)}")
        print(f"  Creation time: {creation_time:.3f}s")
        print(f"  Time per workflow: {creation_time/len(workflows):.4f}s")
        
        # Verify all workflows were created
        assert len(workflows) == 100
        assert all(w.nodes.count() >= 2 for w in workflows)  # Each has start and end nodes
        assert creation_time < 60  # Should complete within 1 minute
    
    @pytest.mark.performance
    @pytest.mark.slow
    def test_bulk_execution_performance(self, db):
        """Test executing many workflows in bulk."""
        # Create 50 simple workflows
        workflows = []
        for i in range(50):
            workflow = ActiveWorkflowFactory()
            workflows.append(workflow)
        
        users = [UserFactory() for _ in range(10)]
        
        start_time = time.time()
        
        # Create executions for all workflows
        executions = []
        for i, workflow in enumerate(workflows):
            user = users[i % len(users)]  # Distribute across users
            execution = WorkflowExecutionService.create_execution(workflow, user)
            executions.append(execution)
        
        # Execute all workflows
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
            for execution in executions:
                WorkflowExecutionService.start_execution(execution)
        
        total_time = time.time() - start_time
        
        # Verify results
        completed = WorkflowExecution.objects.filter(status='completed').count()
        
        print(f"Bulk Execution Performance:")
        print(f"  Workflows executed: {len(executions)}")
        print(f"  Completed: {completed}")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Time per execution: {total_time/len(executions):.4f}s")
        
        assert completed == len(executions)
        assert total_time < 120  # Should complete within 2 minutes
    
    @pytest.mark.performance
    def test_monitoring_service_performance_at_scale(self, db):
        """Test monitoring service performance with large datasets."""
        # Create workflows with many executions
        workflows = []
        for i in range(20):
            workflow = WorkflowFactory()
            workflows.append(workflow)
            
            # Create 50 executions per workflow
            for j in range(50):
                status = 'completed' if j % 2 == 0 else 'failed'
                duration = float(j + 1) if status == 'completed' else None
                WorkflowExecutionFactory(
                    workflow=workflow,
                    status=status,
                    duration_seconds=duration
                )
        
        # Test dashboard stats performance
        start_time = time.time()
        stats = WorkflowMonitoringService.get_workflow_dashboard_stats()
        dashboard_time = time.time() - start_time
        
        # Test individual workflow metrics performance
        start_time = time.time()
        metrics = WorkflowMonitoringService.get_workflow_performance_metrics(
            workflows[0].id, days=30
        )
        metrics_time = time.time() - start_time
        
        print(f"Monitoring Service Performance:")
        print(f"  Dashboard stats time: {dashboard_time:.3f}s")
        print(f"  Workflow metrics time: {metrics_time:.3f}s")
        print(f"  Total workflows: {stats['total_workflows']}")
        print(f"  Total executions: {stats['total_executions']}")
        
        # Verify performance is acceptable
        assert dashboard_time < 2.0  # Dashboard should load quickly
        assert metrics_time < 1.0  # Individual metrics should be fast
        
        # Verify data accuracy
        assert stats['total_workflows'] == 20
        assert stats['total_executions'] == 1000  # 20 workflows * 50 executions
    
    @pytest.mark.performance
    def test_audit_log_performance_at_scale(self, db):
        """Test audit log performance with large volumes."""
        workflow = WorkflowFactory()
        user = UserFactory()
        
        # Create large number of audit logs
        start_time = time.time()
        
        for i in range(1000):
            WorkflowAuditService.log_action(
                user=user,
                action='data_accessed',
                workflow=workflow,
                description=f'Test audit log {i}'
            )
        
        creation_time = time.time() - start_time
        
        # Test querying performance
        start_time = time.time()
        logs = WorkflowAuditLog.objects.filter(workflow=workflow)[:100]
        list(logs)  # Force evaluation
        query_time = time.time() - start_time
        
        print(f"Audit Log Performance:")
        print(f"  Creation time (1000 logs): {creation_time:.3f}s")
        print(f"  Query time (100 logs): {query_time:.3f}s")
        print(f"  Logs per second (creation): {1000/creation_time:.1f}")
        
        # Performance assertions
        assert creation_time < 10.0  # Should create 1000 logs within 10 seconds
        assert query_time < 0.5  # Query should be very fast due to indexes
        
        # Verify all logs were created
        total_logs = WorkflowAuditLog.objects.filter(workflow=workflow).count()
        assert total_logs == 1000


class TestWorkflowMemoryManagement:
    """Test memory management during workflow execution."""
    
    @pytest.mark.performance
    def test_memory_cleanup_after_execution(self, db):
        """Test that memory is properly cleaned up after workflow execution."""
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Execute multiple workflows
        for i in range(20):
            workflow = ActiveWorkflowFactory()
            user = UserFactory()
            
            execution = WorkflowExecutionService.create_execution(workflow, user)
            with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
                WorkflowExecutionService.start_execution(execution)
            
            # Force garbage collection every 5 workflows
            if i % 5 == 0:
                gc.collect()
        
        # Final cleanup and measurement
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        print(f"Memory Management:")
        print(f"  Initial memory: {initial_memory:.2f} MB")
        print(f"  Final memory: {final_memory:.2f} MB")
        print(f"  Memory increase: {memory_increase:.2f} MB")
        print(f"  Memory per workflow: {memory_increase/20:.3f} MB")
        
        # Verify reasonable memory usage
        assert memory_increase < 50  # Should not increase by more than 50MB
        assert memory_increase / 20 < 2.5  # Should not use more than 2.5MB per workflow
    
    @pytest.mark.performance
    def test_large_context_data_handling(self, db):
        """Test handling of workflows with large context data."""
        workflow = ActiveWorkflowFactory()
        user = UserFactory()
        
        # Create execution with large context data
        large_context = {
            'documents': [f'document_{i}.pdf' for i in range(1000)],
            'data': {f'field_{i}': f'value_{i}' * 100 for i in range(100)},
            'metadata': {
                'processing_history': [f'step_{i}' for i in range(500)]
            }
        }
        
        start_time = time.time()
        execution = WorkflowExecutionService.create_execution(
            workflow, user, trigger_data=large_context
        )
        
        with patch('apps.workflows.services.WorkflowExecutionService._simulate_node_execution', return_value=True):
            WorkflowExecutionService.start_execution(execution)
        
        execution_time = time.time() - start_time
        
        print(f"Large Context Data Handling:")
        print(f"  Execution time: {execution_time:.3f}s")
        print(f"  Context data size: ~{len(str(large_context))} characters")
        
        # Verify execution completed despite large context
        execution.refresh_from_db()
        assert execution.status == 'completed'
        assert execution.trigger_data['documents']  # Context data preserved
        assert execution_time < 5.0  # Should still execute reasonably fast


# Performance test markers and configuration
def pytest_configure(config):
    """Configure pytest markers for performance tests."""
    config.addinivalue_line("markers", "performance: mark test as performance test")
    config.addinivalue_line("markers", "slow: mark test as slow running test")