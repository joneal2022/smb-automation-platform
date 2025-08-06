from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    NodeType, WorkflowTemplate, Workflow, WorkflowNode, WorkflowEdge,
    WorkflowExecution, WorkflowNodeExecution, WorkflowAuditLog
)

User = get_user_model()


class NodeTypeSerializer(serializers.ModelSerializer):
    """Serializer for NodeType model."""
    
    class Meta:
        model = NodeType
        fields = [
            'id', 'name', 'type', 'icon', 'color', 'description',
            'config_schema', 'requires_user_action', 'allows_multiple_outputs',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkflowTemplateSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowTemplate model."""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'name', 'description', 'category', 'definition',
            'preview_image', 'setup_time_minutes', 'complexity_level',
            'tags', 'usage_count', 'is_active', 'created_by',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'usage_count', 'created_at', 'updated_at', 'created_by_name']
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class WorkflowNodeSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowNode model."""
    
    node_type_details = NodeTypeSerializer(source='node_type', read_only=True)
    assigned_user_name = serializers.CharField(source='assigned_user.get_full_name', read_only=True)
    
    class Meta:
        model = WorkflowNode
        fields = [
            'id', 'workflow', 'node_type', 'node_type_details', 'node_id',
            'name', 'description', 'position_x', 'position_y', 'config',
            'is_required', 'timeout_seconds', 'retry_count', 'assigned_user',
            'assigned_user_name', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'node_type_details', 'assigned_user_name']


class WorkflowEdgeSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowEdge model."""
    
    source_node_name = serializers.CharField(source='source_node.name', read_only=True)
    target_node_name = serializers.CharField(source='target_node.name', read_only=True)
    
    class Meta:
        model = WorkflowEdge
        fields = [
            'id', 'workflow', 'source_node', 'target_node', 'condition_type',
            'condition_config', 'label', 'source_node_name', 'target_node_name',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'source_node_name', 'target_node_name']


class WorkflowSerializer(serializers.ModelSerializer):
    """Serializer for Workflow model."""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_users_details = serializers.SerializerMethodField()
    template_name = serializers.CharField(source='template.name', read_only=True)
    nodes = WorkflowNodeSerializer(many=True, read_only=True)
    edges = WorkflowEdgeSerializer(many=True, read_only=True)
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'created_by', 'created_by_name',
            'assigned_users', 'assigned_users_details', 'status', 'trigger_type',
            'definition', 'template', 'template_name', 'schedule_config',
            'total_executions', 'successful_executions', 'failed_executions',
            'average_duration_seconds', 'success_rate', 'nodes', 'edges',
            'created_at', 'updated_at', 'last_executed_at'
        ]
        read_only_fields = [
            'id', 'created_by_name', 'assigned_users_details', 'template_name',
            'total_executions', 'successful_executions', 'failed_executions',
            'average_duration_seconds', 'success_rate', 'nodes', 'edges',
            'created_at', 'updated_at', 'last_executed_at'
        ]
    
    def get_assigned_users_details(self, obj):
        return [
            {
                'id': user.id,
                'name': user.get_full_name(),
                'email': user.email
            }
            for user in obj.assigned_users.all()
        ]
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class WorkflowListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for workflow lists."""
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    template_name = serializers.CharField(source='template.name', read_only=True)
    success_rate = serializers.ReadOnlyField()
    node_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'status', 'trigger_type',
            'created_by_name', 'template_name', 'total_executions',
            'success_rate', 'node_count', 'created_at', 'updated_at',
            'last_executed_at'
        ]
    
    def get_node_count(self, obj):
        return obj.nodes.count()


class WorkflowNodeExecutionSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowNodeExecution model."""
    
    workflow_node_name = serializers.CharField(source='workflow_node.name', read_only=True)
    approved_by_name = serializers.CharField(source='approved_by.get_full_name', read_only=True)
    
    class Meta:
        model = WorkflowNodeExecution
        fields = [
            'id', 'workflow_execution', 'workflow_node', 'workflow_node_name',
            'status', 'input_data', 'output_data', 'started_at', 'completed_at',
            'duration_seconds', 'error_message', 'retry_count', 'approved_by',
            'approved_by_name', 'approval_notes'
        ]
        read_only_fields = [
            'id', 'workflow_node_name', 'approved_by_name', 'started_at',
            'completed_at', 'duration_seconds'
        ]


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowExecution model."""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    triggered_by_name = serializers.CharField(source='triggered_by.get_full_name', read_only=True)
    current_node_name = serializers.CharField(source='current_node.name', read_only=True)
    node_executions = WorkflowNodeExecutionSerializer(many=True, read_only=True)
    
    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'workflow', 'workflow_name', 'status', 'triggered_by',
            'triggered_by_name', 'trigger_data', 'current_node',
            'current_node_name', 'context_data', 'started_at', 'completed_at',
            'duration_seconds', 'error_message', 'error_details', 'node_executions'
        ]
        read_only_fields = [
            'id', 'workflow_name', 'triggered_by_name', 'current_node_name',
            'started_at', 'completed_at', 'duration_seconds', 'node_executions'
        ]
    
    def create(self, validated_data):
        validated_data['triggered_by'] = self.context['request'].user
        return super().create(validated_data)


class WorkflowExecutionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for execution lists."""
    
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    triggered_by_name = serializers.CharField(source='triggered_by.get_full_name', read_only=True)
    current_node_name = serializers.CharField(source='current_node.name', read_only=True)
    
    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'workflow_name', 'status', 'triggered_by_name',
            'current_node_name', 'started_at', 'completed_at',
            'duration_seconds', 'error_message'
        ]


class WorkflowAuditLogSerializer(serializers.ModelSerializer):
    """Serializer for WorkflowAuditLog model."""
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    workflow_name = serializers.CharField(source='workflow.name', read_only=True)
    
    class Meta:
        model = WorkflowAuditLog
        fields = [
            'id', 'workflow', 'workflow_name', 'workflow_execution',
            'user', 'user_name', 'user_ip', 'user_agent', 'action',
            'description', 'metadata', 'timestamp'
        ]
        read_only_fields = ['id', 'workflow_name', 'user_name', 'timestamp']


# Specialized serializers for workflow builder canvas
class WorkflowCanvasSerializer(serializers.ModelSerializer):
    """Serializer optimized for the workflow builder canvas."""
    
    nodes = serializers.SerializerMethodField()
    edges = serializers.SerializerMethodField()
    
    class Meta:
        model = Workflow
        fields = ['id', 'name', 'description', 'status', 'nodes', 'edges', 'definition']
    
    def get_nodes(self, obj):
        nodes = obj.nodes.select_related('node_type').all()
        return [
            {
                'id': str(node.id),
                'node_id': node.node_id,
                'name': node.name,
                'type': node.node_type.type,
                'icon': node.node_type.icon,
                'color': node.node_type.color,
                'position': {
                    'x': node.position_x,
                    'y': node.position_y
                },
                'config': node.config,
                'requires_user_action': node.node_type.requires_user_action,
                'allows_multiple_outputs': node.node_type.allows_multiple_outputs
            }
            for node in nodes
        ]
    
    def get_edges(self, obj):
        edges = obj.edges.select_related('source_node', 'target_node').all()
        return [
            {
                'id': str(edge.id),
                'source': edge.source_node.node_id,
                'target': edge.target_node.node_id,
                'condition_type': edge.condition_type,
                'label': edge.label,
                'condition_config': edge.condition_config
            }
            for edge in edges
        ]


class WorkflowTemplateListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for template gallery."""
    
    class Meta:
        model = WorkflowTemplate
        fields = [
            'id', 'name', 'description', 'category', 'preview_image',
            'setup_time_minutes', 'complexity_level', 'tags', 'usage_count'
        ]