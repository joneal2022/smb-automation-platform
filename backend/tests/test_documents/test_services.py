"""
Unit tests for document processing services
"""
import pytest
from unittest.mock import patch, MagicMock, mock_open
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
import json
import tempfile
import os

from apps.documents.services import DocumentProcessingService, document_processing_service
from apps.documents.models import Document, DocumentExtraction, DocumentProcessingLog
from tests.factories import (
    DocumentFactory, DocumentTypeFactory, UserFactory, TestFileFactory
)


class TestDocumentProcessingService:
    """Tests for DocumentProcessingService class"""
    
    def test_service_initialization(self):
        """Test service initialization"""
        service = DocumentProcessingService()
        
        assert service.supported_image_formats == [
            'image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif'
        ]
        assert service.supported_document_formats == ['application/pdf']
    
    def test_calculate_file_hash(self, temp_media_root):
        """Test file hash calculation"""
        service = DocumentProcessingService()
        
        # Create a temporary file
        test_content = b"test file content for hashing"
        temp_file = os.path.join(temp_media_root, "test_file.txt")
        
        with open(temp_file, 'wb') as f:
            f.write(test_content)
        
        file_hash = service.calculate_file_hash(temp_file)
        
        # Hash should be consistent
        assert len(file_hash) == 64  # SHA-256 hex length
        assert file_hash == service.calculate_file_hash(temp_file)
    
    def test_validate_document_valid_file(self, db):
        """Test document validation with valid file"""
        service = DocumentProcessingService()
        document_type = DocumentTypeFactory(
            max_file_size_mb=10,
            allowed_extensions=['pdf', 'png']
        )
        
        uploaded_file = TestFileFactory.create_pdf_file("test.pdf")
        uploaded_file.size = 5 * 1024 * 1024  # 5MB
        
        result = service.validate_document(uploaded_file, document_type)
        
        assert result['is_valid'] is True
        assert result['errors'] == []
        assert result['mime_type'] == 'application/pdf'
        assert result['file_extension'] == 'pdf'
    
    def test_validate_document_file_too_large(self, db):
        """Test document validation with oversized file"""
        service = DocumentProcessingService()
        document_type = DocumentTypeFactory(max_file_size_mb=1)
        
        uploaded_file = TestFileFactory.create_pdf_file("large.pdf")
        uploaded_file.size = 5 * 1024 * 1024  # 5MB
        
        result = service.validate_document(uploaded_file, document_type)
        
        assert result['is_valid'] is False
        assert len(result['errors']) == 1
        assert "exceeds maximum allowed" in result['errors'][0]
    
    def test_validate_document_invalid_extension(self, db):
        """Test document validation with invalid extension"""
        service = DocumentProcessingService()
        document_type = DocumentTypeFactory(allowed_extensions=['pdf', 'png'])
        
        uploaded_file = TestFileFactory.create_invalid_file("test.txt")
        
        result = service.validate_document(uploaded_file, document_type)
        
        assert result['is_valid'] is False
        assert len(result['errors']) == 1
        assert "not allowed" in result['errors'][0]
    
    def test_validate_document_no_document_type(self):
        """Test document validation without document type"""
        service = DocumentProcessingService()
        uploaded_file = TestFileFactory.create_pdf_file("test.pdf")
        uploaded_file.size = 1024 * 1024  # 1MB
        
        result = service.validate_document(uploaded_file, None)
        
        assert result['is_valid'] is True
        assert result['file_extension'] == 'pdf'
    
    def test_create_processing_log(self, db, sample_document, authenticated_user):
        """Test creating processing log entries"""
        service = DocumentProcessingService()
        
        service.create_processing_log(
            document=sample_document,
            step='ocr',
            status='completed',
            message='OCR processing completed',
            details={'confidence': 0.95},
            user=authenticated_user,
            duration=2.5
        )
        
        # Check log was created
        log = DocumentProcessingLog.objects.filter(document=sample_document).first()
        assert log is not None
        assert log.step == 'ocr'
        assert log.status == 'completed'
        assert log.message == 'OCR processing completed'
        assert log.details['confidence'] == 0.95
        assert log.performed_by == authenticated_user
        assert log.duration_seconds == 2.5
    
    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    @patch('PIL.Image.open')
    def test_process_with_tesseract_ocr_success(
        self, mock_image_open, mock_image_to_data, mock_image_to_string, 
        db, sample_document
    ):
        """Test Tesseract OCR processing success"""
        service = DocumentProcessingService()
        
        # Mock PIL Image
        mock_img = MagicMock()
        mock_image_open.return_value.__enter__.return_value = mock_img
        
        # Mock Tesseract responses
        mock_image_to_string.return_value = "Sample OCR text content"
        mock_image_to_data.return_value = {
            'conf': ['95', '90', '85', '92'],
            'text': ['Sample', 'OCR', 'text', 'content']
        }
        
        # Set document as image
        sample_document.mime_type = 'image/png'
        sample_document.save()
        
        result = service.process_with_tesseract_ocr(sample_document)
        
        assert 'error' not in result
        assert result['text'] == "Sample OCR text content"
        assert result['confidence'] > 0.8  # Average of mock confidences
        assert result['method'] == 'tesseract'
        assert 'processing_time' in result
    
    @patch('PIL.Image.open', side_effect=Exception("Image processing failed"))
    def test_process_with_tesseract_ocr_failure(self, mock_image_open, db, sample_document):
        """Test Tesseract OCR processing failure"""
        service = DocumentProcessingService()
        
        sample_document.mime_type = 'image/png'
        sample_document.save()
        
        result = service.process_with_tesseract_ocr(sample_document)
        
        assert 'error' in result
        assert "Tesseract OCR failed" in result['error']
        assert result['method'] == 'tesseract'
    
    def test_process_with_tesseract_unsupported_format(self, db, sample_document):
        """Test Tesseract OCR with unsupported format"""
        service = DocumentProcessingService()
        
        sample_document.mime_type = 'application/pdf'
        sample_document.save()
        
        result = service.process_with_tesseract_ocr(sample_document)
        
        assert 'error' in result
        assert "not supported" in result['error']
    
    @patch('openai.chat.completions.create')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake image data')
    def test_process_with_openai_vision_success(
        self, mock_file_open, mock_openai_create, db, sample_document
    ):
        """Test OpenAI Vision processing success"""
        service = DocumentProcessingService()
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Extracted text from image"
        mock_response.usage.total_tokens = 150
        mock_openai_create.return_value = mock_response
        
        sample_document.mime_type = 'image/png'
        sample_document.save()
        
        with patch('apps.documents.services.openai.api_key', 'test-key'):
            result = service.process_with_openai_vision(sample_document)
        
        assert 'error' not in result
        assert result['text'] == "Extracted text from image"
        assert result['confidence'] == 0.95  # High confidence estimate
        assert result['method'] == 'openai_vision'
        assert result['tokens_used'] == 150
    
    @patch('apps.documents.services.openai.api_key', '')
    def test_process_with_openai_vision_no_api_key(self, db, sample_document):
        """Test OpenAI Vision without API key"""
        service = DocumentProcessingService()
        
        sample_document.mime_type = 'image/png'
        sample_document.save()
        
        result = service.process_with_openai_vision(sample_document)
        
        assert 'error' in result
        assert "API key not configured" in result['error']
    
    def test_process_with_openai_vision_unsupported_format(self, db, sample_document):
        """Test OpenAI Vision with unsupported format"""
        service = DocumentProcessingService()
        
        sample_document.mime_type = 'application/pdf'
        sample_document.save()
        
        with patch('apps.documents.services.openai.api_key', 'test-key'):
            result = service.process_with_openai_vision(sample_document)
        
        assert 'error' in result
        assert "not supported" in result['error']
    
    @patch('openai.chat.completions.create')
    def test_extract_structured_data_success(
        self, mock_openai_create, db, sample_document
    ):
        """Test AI data extraction success"""
        service = DocumentProcessingService()
        
        # Mock OpenAI response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "document_title": {
                "value": "Invoice #12345",
                "confidence": 0.95,
                "type": "text"
            },
            "amount": {
                "value": "$1,234.56",
                "confidence": 0.98,
                "type": "currency"
            }
        })
        mock_openai_create.return_value = mock_response
        
        ocr_text = "Invoice #12345\nAmount: $1,234.56"
        
        with patch('apps.documents.services.openai.api_key', 'test-key'):
            result = service.extract_structured_data(sample_document, ocr_text)
        
        assert len(result) == 2
        assert result[0]['field_name'] == 'document_title'
        assert result[0]['field_value'] == 'Invoice #12345'
        assert result[0]['confidence'] == 0.95
        assert result[1]['field_name'] == 'amount'
        assert result[1]['field_value'] == '$1,234.56'
        assert result[1]['confidence'] == 0.98
    
    @patch('apps.documents.services.openai.api_key', '')
    def test_extract_structured_data_no_api_key(self, db, sample_document):
        """Test AI data extraction without API key"""
        service = DocumentProcessingService()
        
        result = service.extract_structured_data(sample_document, "test text")
        
        assert result == []
    
    def test_extract_structured_data_with_template(self, db, sample_document):
        """Test AI data extraction with custom template"""
        service = DocumentProcessingService()
        
        # Set up document type with custom template
        document_type = DocumentTypeFactory(
            extraction_template={
                "fields": [
                    {"name": "vendor_name", "type": "text", "description": "Vendor name"},
                    {"name": "invoice_number", "type": "text", "description": "Invoice number"}
                ]
            }
        )
        sample_document.document_type = document_type
        sample_document.save()
        
        with patch('apps.documents.services.openai.api_key', ''), \
             patch.object(service, 'create_processing_log') as mock_log:
            
            result = service.extract_structured_data(sample_document, "test text")
            
            # Should fail due to no API key, but template should be used
            mock_log.assert_called()
            assert result == []
    
    @patch.object(DocumentProcessingService, 'process_with_openai_vision')
    @patch.object(DocumentProcessingService, 'extract_structured_data')
    def test_process_document_success_flow(
        self, mock_extract, mock_vision, db, sample_document
    ):
        """Test complete document processing success flow"""
        service = DocumentProcessingService()
        
        # Mock OCR result
        mock_vision.return_value = {
            'text': 'Sample OCR text',
            'confidence': 0.95,
            'language': 'en',
            'method': 'openai_vision'
        }
        
        # Mock extraction result
        mock_extract.return_value = [
            {
                'field_name': 'amount',
                'field_value': '$100.00',
                'field_type': 'currency',
                'confidence': 0.95,
                'original_value': '$100.00'
            }
        ]
        
        sample_document.mime_type = 'image/png'
        sample_document.document_type = DocumentTypeFactory(ai_extraction_enabled=True)
        sample_document.save()
        
        result = service.process_document(sample_document, use_openai=True)
        
        assert result['success'] is True
        assert result['status'] == 'approved'  # High confidence, no review needed
        assert result['extractions_count'] == 1
        assert result['review_required'] is False
        
        # Check document was updated
        sample_document.refresh_from_db()
        assert sample_document.status == 'approved'
        assert sample_document.ocr_text == 'Sample OCR text'
        assert sample_document.ocr_confidence == 0.95
        assert sample_document.processing_completed_at is not None
        
        # Check extraction was created
        extraction = DocumentExtraction.objects.filter(document=sample_document).first()
        assert extraction is not None
        assert extraction.field_name == 'amount'
        assert extraction.field_value == '$100.00'
    
    @patch.object(DocumentProcessingService, 'process_with_openai_vision')
    def test_process_document_ocr_failure(self, mock_vision, db, sample_document):
        """Test document processing with OCR failure"""
        service = DocumentProcessingService()
        
        # Mock OCR failure
        mock_vision.return_value = {'error': 'OCR processing failed'}
        
        sample_document.mime_type = 'image/png'
        sample_document.save()
        
        result = service.process_document(sample_document, use_openai=True)
        
        assert result['success'] is False
        assert result['error'] == 'OCR processing failed'
        
        # Check document status
        sample_document.refresh_from_db()
        assert sample_document.status == 'error'
        assert sample_document.error_message == 'OCR processing failed'
    
    @patch.object(DocumentProcessingService, 'process_with_openai_vision')
    @patch.object(DocumentProcessingService, 'extract_structured_data')
    def test_process_document_low_confidence_review(
        self, mock_extract, mock_vision, db, sample_document
    ):
        """Test document processing triggering review for low confidence"""
        service = DocumentProcessingService()
        
        # Mock OCR result
        mock_vision.return_value = {
            'text': 'Sample OCR text',
            'confidence': 0.95,
            'language': 'en',
            'method': 'openai_vision'
        }
        
        # Mock low confidence extraction
        mock_extract.return_value = [
            {
                'field_name': 'amount',
                'field_value': '$100.00',
                'field_type': 'currency',
                'confidence': 0.7,  # Low confidence
                'original_value': '$100.00'
            }
        ]
        
        sample_document.mime_type = 'image/png'
        sample_document.document_type = DocumentTypeFactory(ai_extraction_enabled=True)
        sample_document.save()
        
        result = service.process_document(sample_document, use_openai=True)
        
        assert result['success'] is True
        assert result['status'] == 'review_required'
        assert result['review_required'] is True
        
        # Check document status
        sample_document.refresh_from_db()
        assert sample_document.status == 'review_required'
    
    @patch.object(DocumentProcessingService, 'process_with_tesseract_ocr')
    def test_process_document_fallback_to_tesseract(
        self, mock_tesseract, db, sample_document
    ):
        """Test document processing fallback to Tesseract"""
        service = DocumentProcessingService()
        
        # Mock Tesseract result
        mock_tesseract.return_value = {
            'text': 'Tesseract OCR text',
            'confidence': 0.85,
            'language': 'en',
            'method': 'tesseract'
        }
        
        sample_document.mime_type = 'application/pdf'  # Not supported by OpenAI Vision
        sample_document.save()
        
        result = service.process_document(sample_document, use_openai=True)
        
        assert result['success'] is True
        mock_tesseract.assert_called_once_with(sample_document)
    
    def test_process_document_unexpected_error(self, db, sample_document):
        """Test document processing with unexpected error"""
        service = DocumentProcessingService()
        
        # Cause an unexpected error by not setting up proper mocks
        sample_document.mime_type = 'application/pdf'
        sample_document.save()
        
        result = service.process_document(sample_document, use_openai=True)
        
        assert result['success'] is False
        assert 'error' in result
        
        # Check document status
        sample_document.refresh_from_db()
        assert sample_document.status == 'error'
        assert sample_document.error_message is not None


class TestDocumentProcessingServiceInstance:
    """Tests for the module-level service instance"""
    
    def test_service_instance_exists(self):
        """Test that the service instance is available"""
        assert document_processing_service is not None
        assert isinstance(document_processing_service, DocumentProcessingService)
    
    def test_service_instance_methods(self):
        """Test that service instance has expected methods"""
        assert hasattr(document_processing_service, 'validate_document')
        assert hasattr(document_processing_service, 'process_document')
        assert hasattr(document_processing_service, 'calculate_file_hash')
        assert hasattr(document_processing_service, 'create_processing_log')