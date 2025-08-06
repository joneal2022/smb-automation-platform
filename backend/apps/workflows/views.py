from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404
from .models import (
    NodeType, WorkflowTemplate, Workflow, WorkflowNode, WorkflowEdge,
    WorkflowExecution, WorkflowNodeExecution, WorkflowAuditLog
)
from .serializers import (
    NodeTypeSerializer, WorkflowTemplateSerializer, WorkflowTemplateListSerializer,
    WorkflowSerializer, WorkflowListSerializer, WorkflowCanvasSerializer,
    WorkflowNodeSerializer, WorkflowEdgeSerializer, WorkflowExecutionSerializer,
    WorkflowExecutionListSerializer, WorkflowAuditLogSerializer
)
from .services import WorkflowExecutionService, WorkflowAuditService, WorkflowMonitoringService


class NodeTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for NodeType - read-only for workflow builder."""
    
    queryset = NodeType.objects.all()
    serializer_class = NodeTypeSerializer
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def by_type(self, request):
        """Group node types by their type for the workflow palette."""
        node_types = NodeType.objects.all()
        grouped = {}
        
        for node_type in node_types:
            type_key = node_type.type
            if type_key not in grouped:
                grouped[type_key] = []
            grouped[type_key].append(NodeTypeSerializer(node_type).data)
        
        return Response(grouped)


class WorkflowTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet for WorkflowTemplate management."""
    
    queryset = WorkflowTemplate.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowTemplateListSerializer
        return WorkflowTemplateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category=category)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(tags__icontains=search)
            )
        
        return queryset.order_by('-usage_count', 'name')
    
    @action(detail=True, methods=['post'])
    def use_template(self, request, pk=None):
        """Create a new workflow from this template."""
        template = self.get_object()
        
        # Increment usage count
        template.increment_usage()
        
        # Create workflow from template
        workflow_data = {
            'name': f"{template.name} - {request.user.get_full_name()}",
            'description': f"Created from template: {template.description}",
            'template': template.id,
            'definition': template.definition.copy() if template.definition else {},
            'status': 'draft'
        }
        
        serializer = WorkflowSerializer(data=workflow_data, context={'request': request})
        if serializer.is_valid():
            workflow = serializer.save()
            
            return Response(WorkflowCanvasSerializer(workflow).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class WorkflowViewSet(viewsets.ModelViewSet):
    """ViewSet for Workflow management."""
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowListSerializer
        elif self.action == 'canvas':
            return WorkflowCanvasSerializer
        return WorkflowSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Base queryset - workflows created by user or assigned to user
        queryset = Workflow.objects.filter(
            Q(created_by=user) | Q(assigned_users=user)
        ).distinct()
        
        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Prefetch related data for performance
        if self.action == 'list':
            queryset = queryset.select_related('created_by', 'template')
        elif self.action in ['retrieve', 'canvas']:
            queryset = queryset.prefetch_related(
                Prefetch('nodes', queryset=WorkflowNode.objects.select_related('node_type')),
                Prefetch('edges', queryset=WorkflowEdge.objects.select_related('source_node', 'target_node')),
                'assigned_users'
            )
        
        return queryset.order_by('-updated_at')
    
    def perform_create(self, serializer):
        workflow = serializer.save(created_by=self.request.user)
    
    def perform_update(self, serializer):
        workflow = serializer.save()
    
    @action(detail=True, methods=['get'])
    def canvas(self, request, pk=None):
        """Get workflow data optimized for the canvas builder."""
        workflow = self.get_object()
        serializer = WorkflowCanvasSerializer(workflow)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def save_canvas(self, request, pk=None):
        """Save workflow canvas data (nodes and edges)."""
        workflow = self.get_object()
        
        # Check permissions
        if workflow.created_by != request.user and request.user not in workflow.assigned_users.all():
            return Response(
                {'error': 'You do not have permission to edit this workflow'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        nodes_data = request.data.get('nodes', [])
        edges_data = request.data.get('edges', [])
        
        # Update workflow definition
        workflow.definition = {
            'nodes': nodes_data,
            'edges': edges_data,
            'version': workflow.definition.get('version', 0) + 1
        }
        workflow.save()
        
        # Delete existing nodes and edges
        workflow.nodes.all().delete()
        workflow.edges.all().delete()
        
        # Create new nodes
        node_map = {}
        for node_data in nodes_data:
            node_type = get_object_or_404(NodeType, id=node_data['node_type'])
            node = WorkflowNode.objects.create(
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
            node_map[node_data['node_id']] = node
        
        # Create new edges
        for edge_data in edges_data:
            source_node = node_map.get(edge_data['source'])
            target_node = node_map.get(edge_data['target'])
            
            if source_node and target_node:
                WorkflowEdge.objects.create(
                    workflow=workflow,
                    source_node=source_node,
                    target_node=target_node,
                    condition_type=edge_data.get('condition_type', 'always'),
                    condition_config=edge_data.get('condition_config', {}),
                    label=edge_data.get('label', '')
                )
        
        return Response(WorkflowCanvasSerializer(workflow).data)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a workflow."""
        workflow = self.get_object()
        
        # Validate workflow has required nodes
        if not workflow.nodes.filter(node_type__type='start').exists():
            return Response(
                {'error': 'Workflow must have at least one start node'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not workflow.nodes.filter(node_type__type='end').exists():
            return Response(
                {'error': 'Workflow must have at least one end node'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        workflow.status = 'active'
        workflow.save()
        
        return Response({'status': 'activated'})
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a workflow."""
        workflow = self.get_object()
        workflow.status = 'inactive'
        workflow.save()
        
        return Response({'status': 'deactivated'})
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute a workflow."""
        workflow = self.get_object()
        
        if workflow.status != 'active':
            return Response(
                {'error': 'Workflow must be active to execute'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        trigger_data = request.data.get('trigger_data', {})
        
        # Create execution
        execution = WorkflowExecutionService.create_execution(
            workflow, request.user, trigger_data
        )
        
        # Start execution in background (simplified - normally would use Celery)
        try:
            WorkflowExecutionService.start_execution(execution)
            return Response(WorkflowExecutionSerializer(execution).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            execution.refresh_from_db()  # Get updated status
            return Response(WorkflowExecutionSerializer(execution).data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """Get workflow executions."""
        workflow = self.get_object()
        executions = workflow.executions.order_by('-started_at')
        
        # Pagination
        page = self.paginate_queryset(executions)
        if page is not None:
            serializer = WorkflowExecutionListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = WorkflowExecutionListSerializer(executions, many=True)
        return Response(serializer.data)


class WorkflowExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for WorkflowExecution monitoring."""
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowExecutionListSerializer
        return WorkflowExecutionSerializer
    
    def get_queryset(self):
        user = self.request.user
        
        # Filter executions for workflows user has access to
        return WorkflowExecution.objects.filter(
            Q(workflow__created_by=user) | Q(workflow__assigned_users=user) | Q(triggered_by=user)
        ).distinct().select_related('workflow', 'triggered_by', 'current_node').order_by('-started_at')


class WorkflowAuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for WorkflowAuditLog - compliance and monitoring."""
    
    serializer_class = WorkflowAuditLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        
        # Filter audit logs for workflows user has access to
        queryset = WorkflowAuditLog.objects.filter(
            Q(workflow__created_by=user) | Q(workflow__assigned_users=user) | Q(user=user)
        ).distinct().select_related('workflow', 'user').order_by('-timestamp')
        
        # Filter by workflow
        workflow_id = self.request.query_params.get('workflow')
        if workflow_id:
            queryset = queryset.filter(workflow_id=workflow_id)
        
        # Filter by action
        action = self.request.query_params.get('action')
        if action:
            queryset = queryset.filter(action=action)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """Get dashboard statistics for workflow monitoring."""
        stats = WorkflowMonitoringService.get_workflow_dashboard_stats()
        return Response(stats)
