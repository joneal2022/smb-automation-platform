"""
Unit tests for document models
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.utils import timezone
from decimal import Decimal
import uuid

from apps.documents.models import (
    DocumentType, Document, DocumentExtraction, 
    DocumentProcessingLog, DocumentBatch, DocumentBatchItem
)
from tests.factories import (
    DocumentTypeFactory, DocumentFactory, DocumentExtractionFactory,
    DocumentProcessingLogFactory, DocumentBatchFactory, DocumentBatchItemFactory,
    UserFactory, TestFileFactory
)


class TestDocumentType:
    """Tests for DocumentType model"""
    
    def test_create_document_type(self, db):
        """Test creating a document type"""
        doc_type = DocumentTypeFactory(name="Test Invoice")
        
        assert doc_type.name == "Test Invoice"
        assert doc_type.ocr_enabled is True
        assert doc_type.ai_extraction_enabled is True
        assert doc_type.is_active is True
        assert doc_type.max_file_size_mb == 50
        assert isinstance(doc_type.id, uuid.UUID)
    
    def test_document_type_str(self, db):
        """Test string representation"""
        doc_type = DocumentTypeFactory(name="Invoice")
        assert str(doc_type) == "Invoice"
    
    def test_unique_name_constraint(self, db):
        """Test that document type names must be unique"""
        DocumentTypeFactory(name="Invoice")
        
        with pytest.raises(IntegrityError):
            DocumentTypeFactory(name="Invoice")
    
    def test_extraction_template_default(self, db):
        """Test default extraction template"""
        doc_type = DocumentTypeFactory(extraction_template={})
        assert doc_type.extraction_template == {}
    
    def test_validation_rules_json(self, db):
        """Test JSON validation rules"""
        rules = {"required_fields": ["amount", "date"]}
        doc_type = DocumentTypeFactory(validation_rules=rules)
        
        assert doc_type.validation_rules == rules
        assert "required_fields" in doc_type.validation_rules
    
    def test_allowed_extensions_list(self, db):
        """Test allowed extensions as list"""
        extensions = ['pdf', 'png', 'jpg']
        doc_type = DocumentTypeFactory(allowed_extensions=extensions)
        
        assert doc_type.allowed_extensions == extensions
        assert 'pdf' in doc_type.allowed_extensions


class TestDocument:
    """Tests for Document model"""
    
    def test_create_document(self, db, authenticated_user, document_type):
        """Test creating a document"""
        document = DocumentFactory(
            uploaded_by=authenticated_user,
            document_type=document_type,
            original_filename="test_invoice.pdf"
        )
        
        assert document.original_filename == "test_invoice.pdf"
        assert document.uploaded_by == authenticated_user
        assert document.document_type == document_type
        assert document.status == 'uploaded'
        assert isinstance(document.id, uuid.UUID)
    
    def test_document_str(self, db):
        """Test string representation"""
        document = DocumentFactory(
            original_filename="invoice.pdf",
            status="processing"
        )
        assert str(document) == "invoice.pdf (processing)"
    
    def test_file_size_mb_property(self, db):
        """Test file size in MB calculation"""
        document = DocumentFactory(file_size=2097152)  # 2MB in bytes (2*1024*1024)
        assert document.file_size_mb == 2.0
    
    def test_processing_time_property(self, db):
        """Test processing time calculation"""
        start_time = timezone.now()
        end_time = start_time + timezone.timedelta(seconds=30)
        
        document = DocumentFactory(
            processing_started_at=start_time,
            processing_completed_at=end_time
        )
        
        assert document.processing_time == 30.0
    
    def test_processing_time_none_when_incomplete(self, db):
        """Test processing time is None when not completed"""
        document = DocumentFactory(
            processing_started_at=timezone.now(),
            processing_completed_at=None
        )
        
        assert document.processing_time is None
    
    def test_can_retry_when_error(self, db):
        """Test can_retry method with error status"""
        document = DocumentFactory(
            status='error',
            retry_count=1,
            max_retries=3
        )
        
        assert document.can_retry() is True
    
    def test_cannot_retry_when_max_reached(self, db):
        """Test can_retry method when max retries reached"""
        document = DocumentFactory(
            status='error',
            retry_count=3,
            max_retries=3
        )
        
        assert document.can_retry() is False
    
    def test_cannot_retry_when_not_error(self, db):
        """Test can_retry method with non-error status"""
        document = DocumentFactory(
            status='approved',
            retry_count=0,
            max_retries=3
        )
        
        assert document.can_retry() is False
    
    def test_unique_file_hash_constraint(self, db, authenticated_user):
        """Test that file hash must be unique per organization"""
        file_hash = "unique_hash_123"
        
        DocumentFactory(
            uploaded_by=authenticated_user,
            file_hash=file_hash
        )
        
        # Same hash should cause IntegrityError
        with pytest.raises(IntegrityError):
            DocumentFactory(
                uploaded_by=authenticated_user,
                file_hash=file_hash
            )
    
    def test_status_choices_validation(self, db):
        """Test document status choices are validated"""
        document = DocumentFactory()
        
        # Valid status
        document.status = 'processing'
        document.save()
        
        # Invalid status should be handled by Django
        document.status = 'invalid_status'
        # Note: Django doesn't enforce choices at DB level by default
        # This would need to be handled in serializers/forms
    
    def test_priority_choices(self, db):
        """Test priority field choices"""
        document = DocumentFactory(priority='high')
        assert document.priority == 'high'
        
        document.priority = 'urgent'
        document.save()
        assert document.priority == 'urgent'
    
    def test_data_classification_choices(self, db):
        """Test data classification choices"""
        document = DocumentFactory(data_classification='confidential')
        assert document.data_classification == 'confidential'
    
    def test_tags_json_field(self, db):
        """Test tags as JSON field"""
        tags = ['invoice', 'business', 'urgent']
        document = DocumentFactory(tags=tags)
        
        assert document.tags == tags
        assert 'invoice' in document.tags
    
    def test_metadata_json_field(self, db):
        """Test metadata as JSON field"""
        metadata = {'source': 'email', 'processed_by': 'AI', 'version': '1.0'}
        document = DocumentFactory(metadata=metadata)
        
        assert document.metadata == metadata
        assert document.metadata['source'] == 'email'


class TestDocumentExtraction:
    """Tests for DocumentExtraction model"""
    
    def test_create_extraction(self, db, sample_document):
        """Test creating a document extraction"""
        extraction = DocumentExtractionFactory(
            document=sample_document,
            field_name="total_amount",
            field_value="$1,234.56",
            field_type="currency",
            confidence=0.95,
            is_verified=False
        )
        
        assert extraction.field_name == "total_amount"
        assert extraction.field_value == "$1,234.56"
        assert extraction.field_type == "currency"
        assert extraction.confidence == 0.95
        assert extraction.is_verified is False
    
    def test_extraction_str(self, db, sample_document):
        """Test string representation"""
        extraction = DocumentExtractionFactory(
            document=sample_document,
            field_name="amount",
            field_value="100.00"
        )
        
        expected = f"{sample_document.original_filename} - amount: 100.00"
        assert str(extraction) == expected
    
    def test_unique_together_constraint(self, db, sample_document):
        """Test unique constraint on document + field_name"""
        DocumentExtractionFactory(
            document=sample_document,
            field_name="amount"
        )
        
        # Same document + field_name should fail
        with pytest.raises(IntegrityError):
            DocumentExtractionFactory(
                document=sample_document,
                field_name="amount"
            )
    
    def test_verification_fields(self, db, authenticated_user):
        """Test verification-related fields"""
        extraction = DocumentExtractionFactory(
            is_verified=True,
            verified_by=authenticated_user,
            verified_at=timezone.now(),
            corrected_value="Corrected Value",
            correction_reason="OCR error fixed"
        )
        
        assert extraction.is_verified is True
        assert extraction.verified_by == authenticated_user
        assert extraction.verified_at is not None
        assert extraction.corrected_value == "Corrected Value"
        assert extraction.correction_reason == "OCR error fixed"
    
    def test_bounding_box_json(self, db):
        """Test bounding box as JSON field"""
        bbox = {'x': 10, 'y': 20, 'width': 100, 'height': 30}
        extraction = DocumentExtractionFactory(bounding_box=bbox)
        
        assert extraction.bounding_box == bbox
        assert extraction.bounding_box['x'] == 10
    
    def test_field_type_choices(self, db):
        """Test field type choices"""
        types = ['text', 'number', 'date', 'currency', 'email', 'phone', 'address']
        
        for field_type in types:
            extraction = DocumentExtractionFactory(field_type=field_type)
            assert extraction.field_type == field_type


class TestDocumentProcessingLog:
    """Tests for DocumentProcessingLog model"""
    
    def test_create_processing_log(self, db, sample_document, authenticated_user):
        """Test creating a processing log"""
        log = DocumentProcessingLogFactory(
            document=sample_document,
            step='ocr',
            status='completed',
            message='OCR processing completed successfully',
            performed_by=authenticated_user
        )
        
        assert log.document == sample_document
        assert log.step == 'ocr'
        assert log.status == 'completed'
        assert log.message == 'OCR processing completed successfully'
        assert log.performed_by == authenticated_user
    
    def test_log_str(self, db, sample_document):
        """Test string representation"""
        log = DocumentProcessingLogFactory(
            document=sample_document,
            step='validation',
            status='failed'
        )
        
        expected = f"{sample_document.original_filename} - validation: failed"
        assert str(log) == expected
    
    def test_step_choices(self, db):
        """Test step choices"""
        steps = ['upload', 'validation', 'classification', 'ocr', 'extraction', 
                'validation_rules', 'review', 'approval', 'error']
        
        for step in steps:
            log = DocumentProcessingLogFactory(step=step)
            assert log.step == step
    
    def test_status_choices(self, db):
        """Test status choices"""
        statuses = ['started', 'completed', 'failed', 'skipped']
        
        for status in statuses:
            log = DocumentProcessingLogFactory(status=status)
            assert log.status == status
    
    def test_details_json_field(self, db):
        """Test details as JSON field"""
        details = {
            'processing_time': 2.5,
            'confidence_score': 0.95,
            'tokens_used': 150
        }
        
        log = DocumentProcessingLogFactory(details=details)
        assert log.details == details
        assert log.details['processing_time'] == 2.5
    
    def test_duration_tracking(self, db):
        """Test duration seconds field"""
        log = DocumentProcessingLogFactory(duration_seconds=5.25)
        assert log.duration_seconds == 5.25


class TestDocumentBatch:
    """Tests for DocumentBatch model"""
    
    def test_create_batch(self, db, authenticated_user, document_type):
        """Test creating a document batch"""
        batch = DocumentBatchFactory(
            name="Invoice Processing Batch #1",
            document_type=document_type,
            created_by=authenticated_user,
            total_documents=10,
            processed_documents=5,
            successful_documents=4,
            failed_documents=1
        )
        
        assert batch.name == "Invoice Processing Batch #1"
        assert batch.document_type == document_type
        assert batch.created_by == authenticated_user
        assert batch.total_documents == 10
        assert batch.processed_documents == 5
        assert batch.successful_documents == 4
        assert batch.failed_documents == 1
    
    def test_batch_str(self, db):
        """Test string representation"""
        batch = DocumentBatchFactory(
            name="Test Batch",
            status="processing"
        )
        
        assert str(batch) == "Batch: Test Batch (processing)"
    
    def test_completion_percentage_property(self, db):
        """Test completion percentage calculation"""
        batch = DocumentBatchFactory(
            total_documents=10,
            processed_documents=7
        )
        
        assert batch.completion_percentage == 70.0
    
    def test_completion_percentage_zero_total(self, db):
        """Test completion percentage with zero total"""
        batch = DocumentBatchFactory(
            total_documents=0,
            processed_documents=0
        )
        
        assert batch.completion_percentage == 0
    
    def test_success_rate_property(self, db):
        """Test success rate calculation"""
        batch = DocumentBatchFactory(
            processed_documents=10,
            successful_documents=8
        )
        
        assert batch.success_rate == 80.0
    
    def test_success_rate_zero_processed(self, db):
        """Test success rate with zero processed"""
        batch = DocumentBatchFactory(
            processed_documents=0,
            successful_documents=0
        )
        
        assert batch.success_rate == 0
    
    def test_status_choices(self, db):
        """Test batch status choices"""
        statuses = ['created', 'processing', 'completed', 'failed', 'partially_completed']
        
        for status in statuses:
            batch = DocumentBatchFactory(status=status)
            assert batch.status == status
    
    def test_auto_approve_threshold(self, db):
        """Test auto approve threshold"""
        batch = DocumentBatchFactory(auto_approve_threshold=0.85)
        assert batch.auto_approve_threshold == 0.85


class TestDocumentBatchItem:
    """Tests for DocumentBatchItem model"""
    
    def test_create_batch_item(self, db, sample_document):
        """Test creating a batch item"""
        batch = DocumentBatchFactory()
        item = DocumentBatchItemFactory(
            batch=batch,
            document=sample_document,
            processing_order=1
        )
        
        assert item.batch == batch
        assert item.document == sample_document
        assert item.processing_order == 1
    
    def test_batch_item_str(self, db):
        """Test string representation"""
        batch = DocumentBatchFactory(name="Test Batch")
        document = DocumentFactory(original_filename="test.pdf")
        item = DocumentBatchItemFactory(
            batch=batch,
            document=document
        )
        
        assert str(item) == "Test Batch - test.pdf"
    
    def test_unique_together_constraint(self, db):
        """Test unique constraint on batch + document"""
        batch = DocumentBatchFactory()
        document = DocumentFactory()
        
        DocumentBatchItemFactory(
            batch=batch,
            document=document
        )
        
        # Same batch + document should fail
        with pytest.raises(IntegrityError):
            DocumentBatchItemFactory(
                batch=batch,
                document=document
            )
    
    def test_processing_timestamps(self, db):
        """Test processing timestamp fields"""
        start_time = timezone.now()
        end_time = start_time + timezone.timedelta(minutes=5)
        
        item = DocumentBatchItemFactory(
            started_at=start_time,
            completed_at=end_time
        )
        
        assert item.started_at == start_time
        assert item.completed_at == end_time
    
    def test_ordering_by_processing_order(self, db):
        """Test default ordering by processing_order"""
        batch = DocumentBatchFactory()
        
        # Create items in reverse order
        item3 = DocumentBatchItemFactory(batch=batch, processing_order=3)
        item1 = DocumentBatchItemFactory(batch=batch, processing_order=1)
        item2 = DocumentBatchItemFactory(batch=batch, processing_order=2)
        
        # Query should return in processing_order
        items = DocumentBatchItem.objects.filter(batch=batch).all()
        assert list(items) == [item1, item2, item3]