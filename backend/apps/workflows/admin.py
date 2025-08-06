from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    NodeType, WorkflowTemplate, Workflow, WorkflowNode, WorkflowEdge,
    WorkflowExecution, WorkflowNodeExecution, WorkflowAuditLog
)


@admin.register(NodeType)
class NodeTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'color_display', 'requires_user_action', 'allows_multiple_outputs']
    list_filter = ['type', 'requires_user_action', 'allows_multiple_outputs']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def color_display(self, obj):
        return format_html(
            '<span style="background-color: {}; padding: 2px 8px; border-radius: 3px; color: white;">{}</span>',
            obj.color, obj.color
        )
    color_display.short_description = 'Color'


@admin.register(WorkflowTemplate)
class WorkflowTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'complexity_level', 'usage_count', 'is_active', 'created_at']
    list_filter = ['category', 'complexity_level', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'tags']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    list_editable = ['is_active']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'category', 'is_active')
        }),
        ('Configuration', {
            'fields': ('definition', 'setup_time_minutes', 'complexity_level', 'tags')
        }),
        ('Media', {
            'fields': ('preview_image',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('usage_count', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class WorkflowNodeInline(admin.TabularInline):
    model = WorkflowNode
    fields = ['node_id', 'name', 'node_type', 'position_x', 'position_y', 'assigned_user']
    extra = 0


class WorkflowEdgeInline(admin.TabularInline):
    model = WorkflowEdge
    fields = ['source_node', 'target_node', 'condition_type', 'label']
    extra = 0


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'trigger_type', 'success_rate_display', 'total_executions', 'created_by', 'updated_at']
    list_filter = ['status', 'trigger_type', 'created_at', 'template__category']
    search_fields = ['name', 'description', 'created_by__username']
    readonly_fields = ['total_executions', 'successful_executions', 'failed_executions', 
                      'average_duration_seconds', 'success_rate_display', 'created_at', 'updated_at', 'last_executed_at']
    filter_horizontal = ['assigned_users']
    inlines = [WorkflowNodeInline, WorkflowEdgeInline]
    
    def success_rate_display(self, obj):
        rate = obj.success_rate
        if rate >= 90:
            color = 'green'
        elif rate >= 70:
            color = 'orange'
        else:
            color = 'red'
        return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
    success_rate_display.short_description = 'Success Rate'
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'status', 'trigger_type')
        }),
        ('Assignment', {
            'fields': ('created_by', 'assigned_users')
        }),
        ('Configuration', {
            'fields': ('template', 'definition', 'schedule_config'),
            'classes': ('collapse',)
        }),
        ('Performance Metrics', {
            'fields': ('total_executions', 'successful_executions', 'failed_executions', 
                      'average_duration_seconds', 'success_rate_display'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'last_executed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkflowNode)
class WorkflowNodeAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'name', 'node_type', 'position_x', 'position_y', 'assigned_user', 'is_required']
    list_filter = ['node_type__type', 'is_required', 'workflow__status']
    search_fields = ['name', 'description', 'workflow__name']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(WorkflowEdge)
class WorkflowEdgeAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'source_node', 'target_node', 'condition_type', 'label']
    list_filter = ['condition_type', 'workflow__status']
    search_fields = ['workflow__name', 'source_node__name', 'target_node__name', 'label']


class WorkflowNodeExecutionInline(admin.TabularInline):
    model = WorkflowNodeExecution
    fields = ['workflow_node', 'status', 'started_at', 'completed_at', 'duration_seconds']
    readonly_fields = ['started_at', 'completed_at', 'duration_seconds']
    extra = 0


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'status', 'triggered_by', 'started_at', 'duration_display', 'current_node']
    list_filter = ['status', 'started_at', 'workflow__name']
    search_fields = ['workflow__name', 'triggered_by__username']
    readonly_fields = ['started_at', 'completed_at', 'duration_seconds', 'duration_display']
    inlines = [WorkflowNodeExecutionInline]
    
    def duration_display(self, obj):
        if obj.duration_seconds:
            if obj.duration_seconds < 60:
                return f"{obj.duration_seconds:.1f}s"
            elif obj.duration_seconds < 3600:
                return f"{obj.duration_seconds/60:.1f}m"
            else:
                return f"{obj.duration_seconds/3600:.1f}h"
        return "N/A"
    duration_display.short_description = 'Duration'
    
    fieldsets = (
        (None, {
            'fields': ('workflow', 'status', 'triggered_by', 'current_node')
        }),
        ('Data', {
            'fields': ('trigger_data', 'context_data'),
            'classes': ('collapse',)
        }),
        ('Performance', {
            'fields': ('started_at', 'completed_at', 'duration_seconds', 'duration_display')
        }),
        ('Errors', {
            'fields': ('error_message', 'error_details'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkflowNodeExecution)
class WorkflowNodeExecutionAdmin(admin.ModelAdmin):
    list_display = ['workflow_execution', 'workflow_node', 'status', 'started_at', 'duration_display', 'retry_count']
    list_filter = ['status', 'started_at', 'workflow_node__node_type__type']
    search_fields = ['workflow_execution__workflow__name', 'workflow_node__name']
    readonly_fields = ['started_at', 'completed_at', 'duration_seconds', 'duration_display']
    
    def duration_display(self, obj):
        if obj.duration_seconds:
            return f"{obj.duration_seconds:.1f}s"
        return "N/A"
    duration_display.short_description = 'Duration'


@admin.register(WorkflowAuditLog)
class WorkflowAuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'user', 'workflow', 'timestamp', 'user_ip']
    list_filter = ['action', 'timestamp', 'workflow__name']
    search_fields = ['user__username', 'workflow__name', 'description', 'user_ip']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
