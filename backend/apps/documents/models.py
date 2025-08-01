from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator
from django.utils import timezone
import uuid
import os

User = get_user_model()


def document_upload_path(instance, filename):
    """Generate upload path for documents"""
    # Create path: documents/org_id/year/month/filename
    org_id = instance.uploaded_by.organization.id
    now = timezone.now()
    return f'documents/{org_id}/{now.year}/{now.month:02d}/{filename}'


class DocumentType(models.Model):
    """Document type classification for processing templates"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    # Processing settings
    ocr_enabled = models.BooleanField(default=True)
    ai_extraction_enabled = models.BooleanField(default=True)
    extraction_template = models.JSONField(default=dict, blank=True)
    
    # Validation rules
    validation_rules = models.JSONField(default=dict, blank=True)
    required_fields = models.JSONField(default=list, blank=True)
    
    # File constraints
    max_file_size_mb = models.PositiveIntegerField(default=50)
    allowed_extensions = models.JSONField(default=list, blank=True)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'document_types'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Document(models.Model):
    """Main document model for uploaded files"""
    
    STATUS_CHOICES = [
        ('uploaded', 'Uploaded'),
        ('processing', 'Processing'),
        ('ocr_complete', 'OCR Complete'),
        ('extraction_complete', 'Extraction Complete'),
        ('review_required', 'Review Required'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('error', 'Error'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # File information
    original_filename = models.CharField(max_length=255)
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'])]
    )
    file_size = models.PositiveIntegerField()  # Size in bytes
    file_hash = models.CharField(max_length=64, unique=True)  # SHA-256 hash for duplicate detection
    mime_type = models.CharField(max_length=100)
    
    # Classification
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, null=True, blank=True)
    auto_detected_type = models.CharField(max_length=100, blank=True)
    confidence_score = models.FloatField(null=True, blank=True)  # AI confidence in classification
    
    # Processing status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='uploaded')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_completed_at = models.DateTimeField(null=True, blank=True)
    
    # OCR results
    ocr_text = models.TextField(blank=True)
    ocr_confidence = models.FloatField(null=True, blank=True)
    ocr_language = models.CharField(max_length=10, blank=True)
    
    # User and organization
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='uploaded_documents')
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_documents')
    
    # Metadata
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Error handling
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    max_retries = models.PositiveIntegerField(default=3)
    
    # Compliance
    contains_pii = models.BooleanField(default=False)
    contains_phi = models.BooleanField(default=False)
    data_classification = models.CharField(
        max_length=20,
        choices=[('public', 'Public'), ('internal', 'Internal'), ('confidential', 'Confidential'), ('restricted', 'Restricted')],
        default='internal'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'documents'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['uploaded_by', '-created_at']),
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['document_type', '-created_at']),
            models.Index(fields=['file_hash']),
        ]
    
    def __str__(self):
        return f"{self.original_filename} ({self.status})"
    
    @property
    def file_size_mb(self):
        """Return file size in MB"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def processing_time(self):
        """Calculate processing time if completed"""
        if self.processing_started_at and self.processing_completed_at:
            return (self.processing_completed_at - self.processing_started_at).total_seconds()
        return None
    
    def can_retry(self):
        """Check if document can be retried"""
        return self.status == 'error' and self.retry_count < self.max_retries


class DocumentExtraction(models.Model):
    """Extracted data fields from documents"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='extractions')
    
    # Extracted field information
    field_name = models.CharField(max_length=100)
    field_value = models.TextField()
    field_type = models.CharField(
        max_length=20,
        choices=[
            ('text', 'Text'),
            ('number', 'Number'),
            ('date', 'Date'),
            ('currency', 'Currency'),
            ('email', 'Email'),
            ('phone', 'Phone'),
            ('address', 'Address'),
        ],
        default='text'
    )
    
    # AI confidence and positioning
    confidence = models.FloatField()
    bounding_box = models.JSONField(null=True, blank=True)  # Coordinates where field was found
    
    # Review status
    is_verified = models.BooleanField(default=False)
    verified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    # Original and corrected values
    original_value = models.TextField()  # As extracted by AI
    corrected_value = models.TextField(blank=True)  # Human corrected value
    correction_reason = models.CharField(max_length=255, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'document_extractions'
        ordering = ['field_name']
        indexes = [
            models.Index(fields=['document', 'field_name']),
            models.Index(fields=['is_verified']),
        ]
        unique_together = ['document', 'field_name']
    
    def __str__(self):
        return f"{self.document.original_filename} - {self.field_name}: {self.field_value}"


class DocumentProcessingLog(models.Model):
    """Log of processing steps for audit trail"""
    
    STEP_CHOICES = [
        ('upload', 'File Upload'),
        ('validation', 'File Validation'),
        ('classification', 'Document Classification'),
        ('ocr', 'OCR Processing'),
        ('extraction', 'Data Extraction'),
        ('validation_rules', 'Validation Rules'),
        ('review', 'Human Review'),
        ('approval', 'Final Approval'),
        ('error', 'Error Occurred'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='processing_logs')
    
    step = models.CharField(max_length=20, choices=STEP_CHOICES)
    status = models.CharField(
        max_length=20,
        choices=[('started', 'Started'), ('completed', 'Completed'), ('failed', 'Failed'), ('skipped', 'Skipped')]
    )
    
    # Processing details
    message = models.TextField()
    details = models.JSONField(default=dict, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)
    
    # User who performed the step (for manual steps)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_processing_logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['document', '-created_at']),
            models.Index(fields=['step', 'status']),
        ]
    
    def __str__(self):
        return f"{self.document.original_filename} - {self.step}: {self.status}"


class DocumentBatch(models.Model):
    """Batch processing for multiple documents"""
    
    STATUS_CHOICES = [
        ('created', 'Created'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('partially_completed', 'Partially Completed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Batch settings
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT, null=True, blank=True)
    auto_approve_threshold = models.FloatField(default=0.95)  # Auto-approve if confidence > threshold
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')
    total_documents = models.PositiveIntegerField(default=0)
    processed_documents = models.PositiveIntegerField(default=0)
    successful_documents = models.PositiveIntegerField(default=0)
    failed_documents = models.PositiveIntegerField(default=0)
    
    # User and timing
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_batches')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'document_batches'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Batch: {self.name} ({self.status})"
    
    @property
    def completion_percentage(self):
        """Calculate completion percentage"""
        if self.total_documents == 0:
            return 0
        return round((self.processed_documents / self.total_documents) * 100, 1)
    
    @property
    def success_rate(self):
        """Calculate success rate of processed documents"""
        if self.processed_documents == 0:
            return 0
        return round((self.successful_documents / self.processed_documents) * 100, 1)


class DocumentBatchItem(models.Model):
    """Individual documents within a batch"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch = models.ForeignKey(DocumentBatch, on_delete=models.CASCADE, related_name='items')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='batch_items')
    
    # Processing order and status
    processing_order = models.PositiveIntegerField()
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'document_batch_items'
        ordering = ['processing_order']
        unique_together = ['batch', 'document']
    
    def __str__(self):
        return f"{self.batch.name} - {self.document.original_filename}"
