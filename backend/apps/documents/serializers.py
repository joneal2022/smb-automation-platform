from rest_framework import serializers
from .models import Document, DocumentType, DocumentExtraction, DocumentBatch, DocumentBatchItem, DocumentProcessingLog


class DocumentTypeSerializer(serializers.ModelSerializer):
    """Serializer for DocumentType model"""
    
    class Meta:
        model = DocumentType
        fields = [
            'id', 'name', 'description', 'ocr_enabled', 'ai_extraction_enabled',
            'extraction_template', 'validation_rules', 'required_fields',
            'max_file_size_mb', 'allowed_extensions', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentExtractionSerializer(serializers.ModelSerializer):
    """Serializer for DocumentExtraction model"""
    
    verified_by_name = serializers.CharField(source='verified_by.get_full_name', read_only=True)
    document_filename = serializers.CharField(source='document.original_filename', read_only=True)
    
    class Meta:
        model = DocumentExtraction
        fields = [
            'id', 'document', 'document_filename', 'field_name', 'field_value', 'field_type',
            'confidence', 'bounding_box', 'is_verified', 'verified_by', 'verified_by_name',
            'verified_at', 'original_value', 'corrected_value', 'correction_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'document', 'verified_by', 'verified_by_name', 'verified_at', 'created_at', 'updated_at']


class DocumentProcessingLogSerializer(serializers.ModelSerializer):
    """Serializer for DocumentProcessingLog model"""
    
    step_display = serializers.CharField(source='get_step_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    performed_by_name = serializers.CharField(source='performed_by.get_full_name', read_only=True)
    
    class Meta:
        model = DocumentProcessingLog
        fields = [
            'id', 'step', 'step_display', 'status', 'status_display', 'message',
            'details', 'duration_seconds', 'performed_by', 'performed_by_name', 'created_at'
        ]
        read_only_fields = ['id', 'step_display', 'status_display', 'performed_by_name', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Serializer for Document model"""
    
    document_type_name = serializers.CharField(source='document_type.name', read_only=True)
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    assigned_to_name = serializers.CharField(source='assigned_to.get_full_name', read_only=True)
    file_size_mb = serializers.ReadOnlyField()
    processing_time = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    can_retry = serializers.ReadOnlyField()
    
    # Related data counts
    extractions_count = serializers.SerializerMethodField()
    processing_logs_count = serializers.SerializerMethodField()
    unverified_extractions_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = [
            'id', 'original_filename', 'file', 'file_size', 'file_size_mb', 'file_hash',
            'mime_type', 'document_type', 'document_type_name', 'auto_detected_type',
            'confidence_score', 'status', 'status_display', 'priority', 'priority_display',
            'processing_started_at', 'processing_completed_at', 'processing_time',
            'ocr_text', 'ocr_confidence', 'ocr_language', 'uploaded_by', 'uploaded_by_name',
            'assigned_to', 'assigned_to_name', 'tags', 'metadata', 'error_message',
            'retry_count', 'max_retries', 'can_retry', 'contains_pii', 'contains_phi',
            'data_classification', 'created_at', 'updated_at', 'extractions_count',
            'processing_logs_count', 'unverified_extractions_count'
        ]
        read_only_fields = [
            'id', 'file_hash', 'auto_detected_type', 'confidence_score', 'processing_started_at',
            'processing_completed_at', 'processing_time', 'ocr_text', 'ocr_confidence',
            'ocr_language', 'uploaded_by', 'uploaded_by_name', 'error_message', 'retry_count',
            'can_retry', 'created_at', 'updated_at', 'extractions_count', 'processing_logs_count',
            'unverified_extractions_count', 'file_size_mb', 'status_display', 'priority_display',
            'document_type_name', 'assigned_to_name'
        ]
    
    def get_extractions_count(self, obj):
        """Get count of extractions for this document"""
        return obj.extractions.count()
    
    def get_processing_logs_count(self, obj):
        """Get count of processing logs for this document"""
        return obj.processing_logs.count()
    
    def get_unverified_extractions_count(self, obj):
        """Get count of unverified extractions"""
        return obj.extractions.filter(is_verified=False).count()


class DocumentBatchItemSerializer(serializers.ModelSerializer):
    """Serializer for DocumentBatchItem model"""
    
    document_details = DocumentSerializer(source='document', read_only=True)
    
    class Meta:
        model = DocumentBatchItem
        fields = [
            'id', 'batch', 'document', 'document_details', 'processing_order',
            'started_at', 'completed_at', 'created_at'
        ]
        read_only_fields = ['id', 'document_details', 'created_at']


class DocumentBatchSerializer(serializers.ModelSerializer):
    """Serializer for DocumentBatch model"""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    document_type_name = serializers.CharField(source='document_type.name', read_only=True)
    completion_percentage = serializers.ReadOnlyField()
    success_rate = serializers.ReadOnlyField()
    
    # Related items
    items = DocumentBatchItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = DocumentBatch
        fields = [
            'id', 'name', 'description', 'document_type', 'document_type_name',
            'auto_approve_threshold', 'status', 'status_display', 'total_documents',
            'processed_documents', 'successful_documents', 'failed_documents',
            'completion_percentage', 'success_rate', 'created_by', 'created_by_name',
            'started_at', 'completed_at', 'created_at', 'updated_at', 'items'
        ]
        read_only_fields = [
            'id', 'status', 'status_display', 'processed_documents', 'successful_documents',
            'failed_documents', 'completion_percentage', 'success_rate', 'created_by',
            'created_by_name', 'started_at', 'completed_at', 'created_at', 'updated_at',
            'items', 'document_type_name'
        ]


class DocumentUploadSerializer(serializers.Serializer):
    """Serializer for document upload"""
    
    file = serializers.FileField()
    document_type = serializers.UUIDField(required=False, allow_null=True)
    auto_process = serializers.BooleanField(default=False)
    use_openai = serializers.BooleanField(default=True)
    priority = serializers.ChoiceField(choices=Document.PRIORITY_CHOICES, default='normal')
    tags = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_file(self, value):
        """Validate uploaded file"""
        if not value:
            raise serializers.ValidationError("No file provided")
        
        # Check file size (50MB default limit)
        max_size = 50 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError(f"File size too large. Maximum allowed: {max_size // (1024*1024)}MB")
        
        return value
    
    def validate_document_type(self, value):
        """Validate document type exists and is active"""
        if value:
            try:
                DocumentType.objects.get(id=value, is_active=True)
            except DocumentType.DoesNotExist:
                raise serializers.ValidationError("Invalid document type")
        return value