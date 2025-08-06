from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.db import transaction
import logging
import json

from .models import (
    Workflow, WorkflowExecution, WorkflowNode, WorkflowNodeExecution, 
    WorkflowAuditLog
)

User = get_user_model()
logger = logging.getLogger(__name__)


class WorkflowExecutionService:
    """Service for executing workflows and managing workflow instances."""
    
    @staticmethod
    def create_execution(workflow, triggered_by, trigger_data=None):
        """Create a new workflow execution instance."""
        try:
            with transaction.atomic():
                execution = WorkflowExecution.objects.create(
                    workflow=workflow,
                    triggered_by=triggered_by,
                    status='queued',
                    trigger_data=trigger_data or {},
                    context_data={}
                )
                
                # Create node execution records for all nodes in the workflow
                nodes = workflow.nodes.all().order_by('created_at')
                for node in nodes:
                    WorkflowNodeExecution.objects.create(
                        workflow_execution=execution,
                        workflow_node=node,
                        status='pending'
                    )
                
                # Log the execution creation
                WorkflowAuditService.log_action(
                    triggered_by, 'execution_started', workflow, execution,
                    f"Workflow execution created for '{workflow.name}'"
                )
                
                return execution
        except Exception as e:
            logger.error(f"Failed to create workflow execution: {e}")
            raise
    
    @staticmethod
    def start_execution(execution):
        """Start executing a workflow (simplified implementation)."""
        try:
            with transaction.atomic():
                execution.status = 'running'
                execution.save()
                
                # Find the start node
                start_nodes = execution.workflow.nodes.filter(node_type__type='start')
                if not start_nodes.exists():
                    raise ValueError("Workflow must have at least one start node")
                
                start_node = start_nodes.first()
                execution.current_node = start_node
                execution.save()
                
                # Execute the start node
                WorkflowExecutionService._execute_node(execution, start_node)
                
        except Exception as e:
            logger.error(f"Failed to start workflow execution: {e}")
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.completed_at = timezone.now()
            execution.duration_seconds = (
                execution.completed_at - execution.started_at
            ).total_seconds()
            execution.save()
            
            # Update workflow statistics
            WorkflowExecutionService._update_workflow_stats(execution.workflow)
    
    @staticmethod
    def _execute_node(execution, node):
        """Execute a specific workflow node."""
        try:
            # Get or create node execution record
            node_execution, created = WorkflowNodeExecution.objects.get_or_create(
                workflow_execution=execution,
                workflow_node=node,
                defaults={'status': 'running', 'started_at': timezone.now()}
            )
            
            if not created:
                node_execution.status = 'running'
                node_execution.started_at = timezone.now()
                node_execution.save()
            
            # Simulate node execution based on type
            success = WorkflowExecutionService._simulate_node_execution(node, node_execution)
            
            if success:
                node_execution.status = 'completed'
                node_execution.completed_at = timezone.now()
                node_execution.duration_seconds = (
                    node_execution.completed_at - node_execution.started_at
                ).total_seconds()
                node_execution.save()
                
                # Find next nodes to execute
                next_nodes = WorkflowExecutionService._get_next_nodes(execution, node)
                
                if next_nodes:
                    # Continue execution with next nodes
                    for next_node in next_nodes:
                        WorkflowExecutionService._execute_node(execution, next_node)
                else:
                    # No more nodes, complete the workflow
                    WorkflowExecutionService._complete_execution(execution, 'completed')
            else:
                # Node failed
                node_execution.status = 'failed'
                node_execution.completed_at = timezone.now()
                node_execution.duration_seconds = (
                    node_execution.completed_at - node_execution.started_at
                ).total_seconds()
                node_execution.error_message = f"Node execution failed: {node.name}"
                node_execution.save()
                
                # Fail the entire workflow
                WorkflowExecutionService._complete_execution(execution, 'failed')
                
        except Exception as e:
            logger.error(f"Failed to execute node {node.name}: {e}")
            node_execution.status = 'failed'
            node_execution.error_message = str(e)
            node_execution.save()
            
            WorkflowExecutionService._complete_execution(execution, 'failed')
    
    @staticmethod
    def _simulate_node_execution(node, node_execution):
        """Simulate node execution (placeholder for actual implementation)."""
        import random
        import time
        
        # Simulate processing time
        time.sleep(random.uniform(0.1, 0.5))
        
        # Set some sample output data
        node_execution.output_data = {
            'executed_at': timezone.now().isoformat(),
            'node_type': node.node_type.type,
            'simulation': True,
            'processing_time_seconds': random.uniform(0.1, 5.0)
        }
        
        # Simulate success/failure (95% success rate)
        return random.random() > 0.05
    
    @staticmethod
    def _get_next_nodes(execution, current_node):
        """Get the next nodes to execute based on current node and conditions."""
        # Get outgoing edges from current node
        edges = current_node.outgoing_edges.all()
        next_nodes = []
        
        for edge in edges:
            # Simplified condition checking
            should_execute = True
            
            if edge.condition_type == 'always':
                should_execute = True
            elif edge.condition_type == 'success':
                # Check if current node completed successfully
                node_execution = execution.node_executions.get(workflow_node=current_node)
                should_execute = node_execution.status == 'completed'
            elif edge.condition_type == 'failure':
                # Check if current node failed
                node_execution = execution.node_executions.get(workflow_node=current_node)
                should_execute = node_execution.status == 'failed'
            # Add more condition types as needed
            
            if should_execute:
                next_nodes.append(edge.target_node)
        
        return next_nodes
    
    @staticmethod
    def _complete_execution(execution, final_status):
        """Complete a workflow execution."""
        execution.status = final_status
        execution.completed_at = timezone.now()
        execution.duration_seconds = (
            execution.completed_at - execution.started_at
        ).total_seconds()
        execution.current_node = None
        execution.save()
        
        # Update workflow statistics
        WorkflowExecutionService._update_workflow_stats(execution.workflow)
        
        # Log completion
        WorkflowAuditService.log_action(
            execution.triggered_by, 
            'execution_completed' if final_status == 'completed' else 'execution_failed',
            execution.workflow, 
            execution,
            f"Workflow execution {final_status}: {execution.workflow.name}"
        )
    
    @staticmethod
    def _update_workflow_stats(workflow):
        """Update workflow execution statistics."""
        executions = workflow.executions.all()
        total = executions.count()
        successful = executions.filter(status='completed').count()
        failed = executions.filter(status='failed').count()
        
        # Calculate average duration
        completed_executions = executions.filter(
            status='completed', 
            duration_seconds__isnull=False
        )
        avg_duration = 0
        if completed_executions.exists():
            avg_duration = sum(e.duration_seconds for e in completed_executions) / completed_executions.count()
        
        # Update workflow
        workflow.total_executions = total
        workflow.successful_executions = successful
        workflow.failed_executions = failed
        workflow.average_duration_seconds = avg_duration
        workflow.last_executed_at = timezone.now()
        workflow.save()
    
    @staticmethod
    def cancel_execution(execution, cancelled_by):
        """Cancel a running workflow execution."""
        if execution.status in ['queued', 'running', 'paused']:
            execution.status = 'cancelled'
            execution.completed_at = timezone.now()
            execution.duration_seconds = (
                execution.completed_at - execution.started_at
            ).total_seconds()
            execution.save()
            
            # Cancel running node executions
            execution.node_executions.filter(status='running').update(
                status='cancelled',
                completed_at=timezone.now()
            )
            
            # Log cancellation
            WorkflowAuditService.log_action(
                cancelled_by, 'execution_cancelled', execution.workflow, execution,
                f"Workflow execution cancelled: {execution.workflow.name}"
            )


class WorkflowAuditService:
    """Service for logging workflow actions for compliance."""
    
    @staticmethod
    def log_action(user, action, workflow=None, workflow_execution=None, 
                  description="", request=None, metadata=None):
        """Log a workflow-related action."""
        try:
            audit_data = {
                'user': user,
                'action': action,
                'description': description,
                'metadata': metadata or {}
            }
            
            if workflow:
                audit_data['workflow'] = workflow
            
            if workflow_execution:
                audit_data['workflow_execution'] = workflow_execution
            
            if request:
                audit_data.update({
                    'user_ip': WorkflowAuditService._get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')[:500]
                })
            
            WorkflowAuditLog.objects.create(**audit_data)
            
        except Exception as e:
            logger.error(f"Failed to log audit action: {e}")
    
    @staticmethod
    def _get_client_ip(request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class WorkflowTemplateService:
    """Service for managing workflow templates."""
    
    @staticmethod
    def create_workflow_from_template(template, user, custom_name=None):
        """Create a new workflow instance from a template."""
        try:
            with transaction.atomic():
                workflow_name = custom_name or f"{template.name} - {user.get_full_name()}"
                
                # Create workflow
                workflow = Workflow.objects.create(
                    name=workflow_name,
                    description=f"Created from template: {template.description}",
                    created_by=user,
                    template=template,
                    definition=template.definition.copy() if template.definition else {},
                    status='draft'
                )
                
                # Create nodes and edges from template definition
                if template.definition and 'nodes' in template.definition:
                    WorkflowTemplateService._create_nodes_from_template(
                        workflow, template.definition['nodes']
                    )
                
                if template.definition and 'edges' in template.definition:
                    WorkflowTemplateService._create_edges_from_template(
                        workflow, template.definition['edges']
                    )
                
                # Increment template usage
                template.increment_usage()
                
                # Log action
                WorkflowAuditService.log_action(
                    user, 'workflow_created', workflow,
                    description=f"Workflow created from template: {template.name}"
                )
                
                return workflow
                
        except Exception as e:
            logger.error(f"Failed to create workflow from template: {e}")
            raise
    
    @staticmethod
    def _create_nodes_from_template(workflow, nodes_data):
        """Create workflow nodes from template definition."""
        from .models import NodeType
        
        for node_data in nodes_data:
            try:
                node_type = NodeType.objects.get(type=node_data['type'])
                WorkflowNode.objects.create(
                    workflow=workflow,
                    node_type=node_type,
                    node_id=node_data['node_id'],
                    name=node_data['name'],
                    description=node_data.get('description', ''),
                    position_x=node_data['position']['x'],
                    position_y=node_data['position']['y'],
                    config=node_data.get('config', {}),
                    is_required=node_data.get('is_required', True),
                    timeout_seconds=node_data.get('timeout_seconds', 300),
                    retry_count=node_data.get('retry_count', 3)
                )
            except NodeType.DoesNotExist:
                logger.warning(f"NodeType {node_data['type']} not found, skipping node")
                continue
    
    @staticmethod
    def _create_edges_from_template(workflow, edges_data):
        """Create workflow edges from template definition."""
        for edge_data in edges_data:
            try:
                source_node = workflow.nodes.get(node_id=edge_data['source'])
                target_node = workflow.nodes.get(node_id=edge_data['target'])
                
                from .models import WorkflowEdge
                WorkflowEdge.objects.create(
                    workflow=workflow,
                    source_node=source_node,
                    target_node=target_node,
                    condition_type=edge_data.get('condition_type', 'always'),
                    condition_config=edge_data.get('condition_config', {}),
                    label=edge_data.get('label', '')
                )
            except WorkflowNode.DoesNotExist:
                logger.warning(f"Node not found for edge {edge_data}, skipping")
                continue


class WorkflowMonitoringService:
    """Service for monitoring workflow performance and health."""
    
    @staticmethod
    def get_workflow_dashboard_stats():
        """Get dashboard statistics for workflows."""
        try:
            from django.db.models import Count, Avg, Q
            from django.utils import timezone
            
            now = timezone.now()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)
            
            # Basic counts
            total_workflows = Workflow.objects.count()
            active_workflows = Workflow.objects.filter(status='active').count()
            
            # Execution stats
            total_executions = WorkflowExecution.objects.count()
            recent_executions = WorkflowExecution.objects.filter(
                started_at__gte=last_24h
            ).count()
            
            running_executions = WorkflowExecution.objects.filter(
                status__in=['queued', 'running']
            ).count()
            
            # Success rates
            completed_executions = WorkflowExecution.objects.filter(
                status='completed'
            ).count()
            failed_executions = WorkflowExecution.objects.filter(
                status='failed'
            ).count()
            
            success_rate = 0
            if total_executions > 0:
                success_rate = (completed_executions / total_executions) * 100
            
            # Average processing time
            avg_duration = WorkflowExecution.objects.filter(
                status='completed',
                duration_seconds__isnull=False
            ).aggregate(avg=Avg('duration_seconds'))['avg'] or 0
            
            return {
                'total_workflows': total_workflows,
                'active_workflows': active_workflows,
                'total_executions': total_executions,
                'recent_executions': recent_executions,
                'running_executions': running_executions,
                'success_rate': round(success_rate, 1),
                'average_duration': round(avg_duration, 1),
                'last_updated': now.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard stats: {e}")
            return {
                'total_workflows': 0,
                'active_workflows': 0,
                'total_executions': 0,
                'recent_executions': 0,
                'running_executions': 0,
                'success_rate': 0,
                'average_duration': 0,
                'last_updated': timezone.now().isoformat()
            }
    
    @staticmethod
    def get_workflow_performance_metrics(workflow_id, days=7):
        """Get performance metrics for a specific workflow."""
        try:
            workflow = Workflow.objects.get(id=workflow_id)
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            executions = workflow.executions.filter(
                started_at__gte=start_date,
                started_at__lte=end_date
            )
            
            # Daily execution counts
            daily_stats = {}
            for i in range(days):
                date = (start_date + timedelta(days=i)).date()
                day_executions = executions.filter(started_at__date=date)
                
                daily_stats[date.isoformat()] = {
                    'total': day_executions.count(),
                    'completed': day_executions.filter(status='completed').count(),
                    'failed': day_executions.filter(status='failed').count(),
                    'avg_duration': day_executions.filter(
                        status='completed',
                        duration_seconds__isnull=False
                    ).aggregate(avg=Avg('duration_seconds'))['avg'] or 0
                }
            
            return {
                'workflow_id': workflow_id,
                'workflow_name': workflow.name,
                'period_days': days,
                'daily_stats': daily_stats,
                'total_period_executions': executions.count(),
                'period_success_rate': workflow.success_rate
            }
            
        except Workflow.DoesNotExist:
            return {'error': 'Workflow not found'}
        except Exception as e:
            logger.error(f"Failed to get workflow metrics: {e}")
            return {'error': str(e)}