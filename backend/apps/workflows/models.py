from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid
import json


class NodeType(models.Model):
    """Defines the types of nodes available in workflows."""
    
    TYPE_CHOICES = [
        ('start', 'Start Node'),
        ('end', 'End Node'),
        ('process', 'Process Node'),
        ('decision', 'Decision Node'),
        ('approval', 'Approval Node'),
        ('document', 'Document Processing'),
        ('integration', 'Integration Node'),
        ('notification', 'Notification Node'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    icon = models.CharField(max_length=50, default='box')  # CSS icon class
    color = models.CharField(max_length=7, default='#0d6efd')  # Hex color
    description = models.TextField(blank=True)
    
    # Configuration schema for this node type (JSON)
    config_schema = models.JSONField(default=dict, blank=True)
    
    # Whether this node type requires user intervention
    requires_user_action = models.BooleanField(default=False)
    
    # Whether this node can have multiple outputs
    allows_multiple_outputs = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['type', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_type_display()})"


class WorkflowTemplate(models.Model):
    """Pre-built workflow templates for common business processes."""
    
    CATEGORY_CHOICES = [
        ('document_processing', 'Document Processing'),
        ('approval', 'Approval Workflows'),
        ('customer_service', 'Customer Service'),
        ('integration', 'System Integration'),
        ('compliance', 'Compliance & Audit'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    
    # JSON definition of the workflow structure
    definition = models.JSONField(default=dict)
    
    # Preview image or diagram
    preview_image = models.ImageField(upload_to='workflow_templates/', blank=True, null=True)
    
    # Estimated setup time in minutes
    setup_time_minutes = models.PositiveIntegerField(default=30)
    
    # Complexity level 1-5
    complexity_level = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    # Tags for searching and filtering
    tags = models.JSONField(default=list, blank=True)
    
    # Usage statistics
    usage_count = models.PositiveIntegerField(default=0)
    
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-usage_count', 'name']
    
    def __str__(self):
        return self.name
    
    def increment_usage(self):
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class Workflow(models.Model):
    """Main workflow definition created by users."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('inactive', 'Inactive'),
        ('archived', 'Archived'),
    ]
    
    TRIGGER_CHOICES = [
        ('manual', 'Manual Start'),
        ('schedule', 'Scheduled'),
        ('event', 'Event Triggered'),
        ('webhook', 'Webhook'),
        ('document_upload', 'Document Upload'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Organization (assuming you have one)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workflows')
    assigned_users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='assigned_workflows')
    
    # Workflow configuration
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    trigger_type = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='manual')
    
    # JSON definition of the complete workflow
    definition = models.JSONField(default=dict)
    
    # Template this workflow was created from (if any)
    template = models.ForeignKey(WorkflowTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Scheduling configuration (for scheduled workflows)
    schedule_config = models.JSONField(default=dict, blank=True)
    
    # Performance metrics
    total_executions = models.PositiveIntegerField(default=0)
    successful_executions = models.PositiveIntegerField(default=0)
    failed_executions = models.PositiveIntegerField(default=0)
    average_duration_seconds = models.FloatField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_executed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['trigger_type', 'status']),
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def success_rate(self):
        if self.total_executions == 0:
            return 0
        return (self.successful_executions / self.total_executions) * 100


class WorkflowNode(models.Model):
    """Individual nodes within a workflow."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='nodes')
    node_type = models.ForeignKey(NodeType, on_delete=models.CASCADE)
    
    # Unique identifier within the workflow
    node_id = models.CharField(max_length=100)  # e.g., "start_1", "process_2"
    
    # Display properties
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Position on canvas
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    
    # Node-specific configuration
    config = models.JSONField(default=dict, blank=True)
    
    # Execution properties
    is_required = models.BooleanField(default=True)
    timeout_seconds = models.PositiveIntegerField(default=300)  # 5 minutes
    retry_count = models.PositiveIntegerField(default=3)
    
    # Assigned user for manual tasks
    assigned_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['workflow', 'node_id']
        ordering = ['workflow', 'node_id']
    
    def __str__(self):
        return f"{self.workflow.name} - {self.name}"


class WorkflowEdge(models.Model):
    """Connections between workflow nodes."""
    
    CONDITION_TYPES = [
        ('always', 'Always'),
        ('success', 'On Success'),
        ('failure', 'On Failure'),
        ('conditional', 'Conditional'),
        ('approval_yes', 'Approval Yes'),
        ('approval_no', 'Approval No'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='edges')
    
    source_node = models.ForeignKey(
        WorkflowNode, 
        on_delete=models.CASCADE, 
        related_name='outgoing_edges'
    )
    target_node = models.ForeignKey(
        WorkflowNode, 
        on_delete=models.CASCADE, 
        related_name='incoming_edges'
    )
    
    # Condition for traversing this edge
    condition_type = models.CharField(max_length=20, choices=CONDITION_TYPES, default='always')
    condition_config = models.JSONField(default=dict, blank=True)
    
    # Display properties
    label = models.CharField(max_length=100, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['workflow', 'source_node', 'target_node', 'condition_type']
        ordering = ['workflow', 'source_node']
    
    def __str__(self):
        return f"{self.source_node.name} → {self.target_node.name}"


class WorkflowExecution(models.Model):
    """Tracks individual workflow execution instances."""
    
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('running', 'Running'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions')
    
    # Execution metadata
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    triggered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    trigger_data = models.JSONField(default=dict, blank=True)
    
    # Execution tracking
    current_node = models.ForeignKey(
        WorkflowNode, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='current_executions'
    )
    
    # Execution context data
    context_data = models.JSONField(default=dict, blank=True)
    
    # Performance metrics
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # Error information
    error_message = models.TextField(blank=True)
    error_details = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['triggered_by', 'started_at']),
        ]
    
    def __str__(self):
        return f"{self.workflow.name} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"


class WorkflowNodeExecution(models.Model):
    """Tracks execution of individual nodes within a workflow."""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
        ('waiting_approval', 'Waiting for Approval'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workflow_execution = models.ForeignKey(
        WorkflowExecution, 
        on_delete=models.CASCADE, 
        related_name='node_executions'
    )
    workflow_node = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE)
    
    # Execution status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Input and output data
    input_data = models.JSONField(default=dict, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    
    # Performance tracking
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    
    # For approval nodes
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['workflow_execution', 'workflow_node']
        ordering = ['workflow_execution', 'started_at']
    
    def __str__(self):
        return f"{self.workflow_execution} - {self.workflow_node.name}"


class WorkflowAuditLog(models.Model):
    """Audit trail for workflow actions (GDPR/HIPAA compliance)."""
    
    ACTION_CHOICES = [
        ('workflow_created', 'Workflow Created'),
        ('workflow_updated', 'Workflow Updated'),
        ('workflow_activated', 'Workflow Activated'),
        ('workflow_deactivated', 'Workflow Deactivated'),
        ('execution_started', 'Execution Started'),
        ('execution_completed', 'Execution Completed'),
        ('execution_failed', 'Execution Failed'),
        ('node_approved', 'Node Approved'),
        ('node_rejected', 'Node Rejected'),
        ('data_accessed', 'Data Accessed'),
        ('data_modified', 'Data Modified'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # What was acted upon
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, null=True, blank=True)
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, null=True, blank=True)
    
    # Who performed the action
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    user_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Action details
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    description = models.TextField()
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['workflow', 'action', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.action} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
