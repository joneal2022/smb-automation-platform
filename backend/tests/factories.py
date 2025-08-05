"""
Factory classes for generating test data
"""
import factory
import factory.fuzzy
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.documents.models import (
    DocumentType, Document, DocumentExtraction, 
    DocumentProcessingLog, DocumentBatch, DocumentBatchItem
)
from apps.users.models import Organization, Role
import uuid
from datetime import datetime, timezone

User = get_user_model()


class OrganizationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Organization
    
    name = factory.Faker('company')
    domain = factory.Faker('domain_name')
    max_users = factory.fuzzy.FuzzyInteger(10, 1000)
    is_active = True


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role
    
    name = factory.Iterator(['admin', 'manager', 'user', 'viewer', 'processor'])
    description = factory.Faker('text', max_nb_chars=200)
    permissions = factory.LazyFunction(lambda: ['documents.view', 'documents.add'])


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
    
    email = factory.Faker('email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    organization = factory.SubFactory(OrganizationFactory)
    role = factory.SubFactory(RoleFactory)
    
    @factory.post_generation
    def set_password(self, create, extracted, **kwargs):
        if create:
            self.set_password('testpass123')
            self.save()


class DocumentTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentType
    
    name = factory.Iterator(['Invoice', 'Contract', 'Receipt', 'Form', 'Report'])
    description = factory.Faker('text', max_nb_chars=200)
    ocr_enabled = True
    ai_extraction_enabled = True
    extraction_template = factory.LazyFunction(lambda: {
        "fields": [
            {"name": "document_title", "type": "text", "description": "Main title"},
            {"name": "date", "type": "date", "description": "Document date"},
            {"name": "amount", "type": "currency", "description": "Total amount"}
        ]
    })
    validation_rules = factory.LazyFunction(lambda: {"required_fields": ["amount"]})
    required_fields = factory.LazyFunction(lambda: ["amount"])
    max_file_size_mb = 50
    allowed_extensions = factory.LazyFunction(lambda: ['pdf', 'png', 'jpg', 'jpeg'])
    is_active = True


class DocumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Document
    
    original_filename = factory.Faker('file_name', extension='pdf')
    file = factory.LazyAttribute(lambda obj: SimpleUploadedFile(
        obj.original_filename,
        b'fake file content',
        content_type='application/pdf'
    ))
    file_size = factory.fuzzy.FuzzyInteger(1024, 10*1024*1024)  # 1KB to 10MB
    file_hash = factory.LazyFunction(lambda: uuid.uuid4().hex)
    mime_type = factory.Iterator(['application/pdf', 'image/png', 'image/jpeg'])
    document_type = factory.SubFactory(DocumentTypeFactory)
    status = factory.Iterator([
        'uploaded', 'processing', 'ocr_complete', 'extraction_complete',
        'review_required', 'approved', 'rejected', 'error'
    ])
    priority = factory.Iterator(['low', 'normal', 'high', 'urgent'])
    ocr_text = factory.Faker('text', max_nb_chars=1000)
    ocr_confidence = factory.fuzzy.FuzzyFloat(0.5, 1.0)
    ocr_language = 'en'
    uploaded_by = factory.SubFactory(UserFactory)
    tags = factory.LazyFunction(lambda: ['invoice', 'business'])
    metadata = factory.LazyFunction(lambda: {'source': 'upload', 'version': '1.0'})
    contains_pii = factory.Faker('boolean', chance_of_getting_true=30)
    contains_phi = factory.Faker('boolean', chance_of_getting_true=10)
    data_classification = factory.Iterator(['public', 'internal', 'confidential', 'restricted'])


class DocumentExtractionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentExtraction
    
    document = factory.SubFactory(DocumentFactory)
    field_name = factory.Iterator(['document_title', 'date', 'amount', 'vendor_name', 'total'])
    field_value = factory.Faker('word')
    field_type = factory.Iterator(['text', 'number', 'date', 'currency', 'email'])
    confidence = factory.fuzzy.FuzzyFloat(0.6, 1.0)
    bounding_box = factory.LazyFunction(lambda: {'x': 10, 'y': 20, 'width': 100, 'height': 30})
    is_verified = factory.Faker('boolean', chance_of_getting_true=70)
    original_value = factory.SelfAttribute('field_value')
    
    @factory.post_generation
    def set_verified_data(self, create, extracted, **kwargs):
        if create and self.is_verified:
            self.verified_by = UserFactory()
            self.verified_at = factory.Faker('date_time', tzinfo=timezone.utc).generate()
            self.save()


class DocumentProcessingLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentProcessingLog
    
    document = factory.SubFactory(DocumentFactory)
    step = factory.Iterator([
        'upload', 'validation', 'classification', 'ocr', 
        'extraction', 'validation_rules', 'review', 'approval', 'error'
    ])
    status = factory.Iterator(['started', 'completed', 'failed', 'skipped'])
    message = factory.Faker('sentence')
    details = factory.LazyFunction(lambda: {'processing_time': 2.5, 'confidence': 0.95})
    duration_seconds = factory.fuzzy.FuzzyFloat(0.1, 10.0)
    performed_by = factory.SubFactory(UserFactory)


class DocumentBatchFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentBatch
    
    name = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text', max_nb_chars=300)
    document_type = factory.SubFactory(DocumentTypeFactory)
    auto_approve_threshold = factory.fuzzy.FuzzyFloat(0.8, 0.95)
    status = factory.Iterator(['created', 'processing', 'completed', 'failed', 'partially_completed'])
    total_documents = factory.fuzzy.FuzzyInteger(1, 50)
    processed_documents = factory.LazyAttribute(lambda obj: min(obj.total_documents, 
                                                               factory.fuzzy.FuzzyInteger(0, obj.total_documents).fuzz()))
    successful_documents = factory.LazyAttribute(lambda obj: min(obj.processed_documents,
                                                               factory.fuzzy.FuzzyInteger(0, obj.processed_documents).fuzz()))
    failed_documents = factory.LazyAttribute(lambda obj: obj.processed_documents - obj.successful_documents)
    created_by = factory.SubFactory(UserFactory)


class DocumentBatchItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DocumentBatchItem
    
    batch = factory.SubFactory(DocumentBatchFactory)
    document = factory.SubFactory(DocumentFactory)
    processing_order = factory.Sequence(lambda n: n + 1)


# Specialized factories for specific test scenarios
class PendingDocumentFactory(DocumentFactory):
    """Factory for documents needing processing"""
    status = 'uploaded'
    ocr_text = ''
    ocr_confidence = None


class ReviewRequiredDocumentFactory(DocumentFactory):
    """Factory for documents requiring manual review"""
    status = 'review_required'
    ocr_confidence = factory.fuzzy.FuzzyFloat(0.5, 0.79)  # Low confidence


class CompletedDocumentFactory(DocumentFactory):
    """Factory for fully processed documents"""
    status = 'approved'
    ocr_confidence = factory.fuzzy.FuzzyFloat(0.9, 1.0)  # High confidence
    processing_completed_at = factory.Faker('date_time', tzinfo=timezone.utc)


class ErrorDocumentFactory(DocumentFactory):
    """Factory for documents with processing errors"""
    status = 'error'
    error_message = factory.Faker('sentence')
    retry_count = factory.fuzzy.FuzzyInteger(1, 3)


# Test file factories
class TestFileFactory:
    """Factory for creating test files"""
    
    @staticmethod
    def create_pdf_file(filename='test.pdf', content=b'%PDF-1.4 fake pdf content'):
        return SimpleUploadedFile(filename, content, content_type='application/pdf')
    
    @staticmethod
    def create_image_file(filename='test.jpg', content=b'fake image content'):
        return SimpleUploadedFile(filename, content, content_type='image/jpeg')
    
    @staticmethod
    def create_png_file(filename='test.png', content=b'fake png content'):
        return SimpleUploadedFile(filename, content, content_type='image/png')
    
    @staticmethod
    def create_large_file(filename='large.pdf', size_mb=60):
        content = b'0' * (size_mb * 1024 * 1024)
        return SimpleUploadedFile(filename, content, content_type='application/pdf')
    
    @staticmethod
    def create_invalid_file(filename='invalid.txt', content=b'invalid file type'):
        return SimpleUploadedFile(filename, content, content_type='text/plain')