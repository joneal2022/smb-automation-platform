"""
Global pytest fixtures and configuration
"""
import pytest
import responses
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from unittest.mock import patch, MagicMock
import tempfile
import os
from tests.factories import (
    UserFactory, OrganizationFactory, DocumentTypeFactory, 
    DocumentFactory, TestFileFactory
)


@pytest.fixture
def api_client():
    """
    API client for testing REST endpoints
    """
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_user(db):
    """
    Create an authenticated user for testing
    """
    user = UserFactory()
    return user


@pytest.fixture
def authenticated_client(api_client, authenticated_user):
    """
    API client with an authenticated user
    """
    api_client.force_authenticate(user=authenticated_user)
    return api_client


@pytest.fixture
def admin_user(db):
    """
    Create an admin user for testing
    """
    from tests.factories import RoleFactory
    admin_role = RoleFactory(name='admin')
    user = UserFactory(role=admin_role)
    return user


@pytest.fixture
def admin_client(api_client, admin_user):
    """
    API client with an admin user
    """
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def organization(db):
    """
    Create a test organization
    """
    return OrganizationFactory()


@pytest.fixture
def document_type(db):
    """
    Create a test document type
    """
    return DocumentTypeFactory(name='Invoice')


@pytest.fixture
def sample_document(db, authenticated_user, document_type):
    """
    Create a sample document for testing
    """
    return DocumentFactory(
        uploaded_by=authenticated_user,
        document_type=document_type,
        status='uploaded'
    )


@pytest.fixture
def test_pdf_file():
    """
    Create a test PDF file
    """
    return TestFileFactory.create_pdf_file()


@pytest.fixture
def test_image_file():
    """
    Create a test image file
    """
    return TestFileFactory.create_image_file()


@pytest.fixture
def example_invoice_file():
    """
    Load the actual example invoice file for testing
    """
    example_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'example', 'docs', 'invoice.png'
    )
    
    if os.path.exists(example_path):
        with open(example_path, 'rb') as f:
            content = f.read()
        return SimpleUploadedFile('invoice.png', content, content_type='image/png')
    else:
        # Fallback to fake image if example doesn't exist
        return TestFileFactory.create_png_file('invoice.png')


@pytest.fixture
def example_pdf_file():
    """
    Load the actual example PDF file for testing
    """
    example_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'example', 'docs', 'rooferi_invoice_1.pdf'
    )
    
    if os.path.exists(example_path):
        with open(example_path, 'rb') as f:
            content = f.read()
        return SimpleUploadedFile('rooferi_invoice_1.pdf', content, content_type='application/pdf')
    else:
        # Fallback to fake PDF if example doesn't exist
        return TestFileFactory.create_pdf_file('rooferi_invoice_1.pdf')


@pytest.fixture
def temp_media_root():
    """
    Create a temporary media root for file uploads during testing
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        with override_settings(MEDIA_ROOT=temp_dir):
            yield temp_dir


@pytest.fixture
def mock_openai_api():
    """
    Mock OpenAI API responses
    """
    with responses.RequestsMock() as rsps:
        # Mock OCR Vision API response
        rsps.add(
            responses.POST,
            'https://api.openai.com/v1/chat/completions',
            json={
                'choices': [{
                    'message': {
                        'content': 'Invoice #12345\nDate: 2025-08-01\nAmount: $1,234.56\nVendor: Test Company'
                    }
                }],
                'usage': {'total_tokens': 150}
            },
            status=200
        )
        
        # Mock data extraction API response
        rsps.add(
            responses.POST,
            'https://api.openai.com/v1/chat/completions',
            json={
                'choices': [{
                    'message': {
                        'content': '{"document_title": {"value": "Invoice #12345", "confidence": 0.95, "type": "text"}, "date": {"value": "2025-08-01", "confidence": 0.92, "type": "date"}, "amount": {"value": "$1,234.56", "confidence": 0.98, "type": "currency"}}'
                    }
                }],
                'usage': {'total_tokens': 200}
            },
            status=200
        )
        
        yield rsps


@pytest.fixture
def mock_tesseract():
    """
    Mock Tesseract OCR functionality
    """
    with patch('pytesseract.image_to_string') as mock_string, \
         patch('pytesseract.image_to_data') as mock_data:
        
        mock_string.return_value = "Sample OCR text from Tesseract"
        mock_data.return_value = {
            'conf': ['95', '90', '88', '92'],
            'text': ['Sample', 'OCR', 'text', 'from']
        }
        
        yield mock_string, mock_data


@pytest.fixture
def mock_document_processing_service():
    """
    Mock the document processing service for isolated testing
    """
    with patch('apps.documents.services.document_processing_service') as mock_service:
        mock_service.validate_document.return_value = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'mime_type': 'application/pdf',
            'file_extension': 'pdf'
        }
        
        mock_service.calculate_file_hash.return_value = 'fake_hash_123'
        
        mock_service.process_document.return_value = {
            'success': True,
            'status': 'approved',
            'ocr_result': {
                'text': 'Sample extracted text',
                'confidence': 0.95,
                'method': 'openai_vision'
            },
            'extractions_count': 3,
            'review_required': False
        }
        
        yield mock_service


@pytest.fixture
def sample_ocr_result():
    """
    Sample OCR result for testing
    """
    return {
        'text': 'Invoice #12345\nDate: 2025-08-01\nAmount: $1,234.56\nVendor: Test Company',
        'confidence': 0.95,
        'language': 'en',
        'method': 'openai_vision',
        'processing_time': 2.5
    }


@pytest.fixture
def sample_extraction_data():
    """
    Sample extraction data for testing
    """
    return [
        {
            'field_name': 'document_title',
            'field_value': 'Invoice #12345',
            'field_type': 'text',
            'confidence': 0.95,
            'original_value': 'Invoice #12345'
        },
        {
            'field_name': 'date',
            'field_value': '2025-08-01',
            'field_type': 'date',
            'confidence': 0.92,
            'original_value': '2025-08-01'
        },
        {
            'field_name': 'amount',
            'field_value': '$1,234.56',
            'field_type': 'currency',
            'confidence': 0.98,
            'original_value': '$1,234.56'
        }
    ]


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    Enable database access for all tests
    """
    pass


@pytest.fixture
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Custom database setup for tests
    """
    with django_db_blocker.unblock():
        # Create any necessary test data that should exist for all tests
        pass


# Performance testing fixtures
@pytest.fixture
def load_testing_data(db):
    """
    Create bulk data for load testing
    """
    from tests.factories import DocumentFactory
    
    # Create 100 test documents
    documents = DocumentFactory.create_batch(100)
    return documents


@pytest.fixture
def concurrent_users(db):
    """
    Create multiple users for concurrent testing
    """
    users = UserFactory.create_batch(10)
    return users