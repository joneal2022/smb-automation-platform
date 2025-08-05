"""
Integration tests for document API endpoints
"""
import pytest
import json
from django.urls import reverse
from rest_framework import status
from unittest.mock import patch, MagicMock
import tempfile
import os

from apps.documents.models import Document, DocumentExtraction, DocumentBatch
from tests.factories import (
    DocumentFactory, DocumentTypeFactory, DocumentExtractionFactory,
    DocumentBatchFactory, TestFileFactory, PendingDocumentFactory,
    ReviewRequiredDocumentFactory
)


class TestDocumentUploadAPI:
    """Tests for document upload endpoint"""
    
    def test_upload_document_success(
        self, authenticated_client, document_type, test_pdf_file, 
        mock_document_processing_service, temp_media_root
    ):
        """Test successful document upload"""
        url = '/api/upload/'
        data = {
            'file': test_pdf_file,
            'document_type': str(document_type.id),
            'auto_process': False
        }
        
        response = authenticated_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'document' in response.data
        assert response.data['message'] == 'Document uploaded successfully'
        
        # Check document was created
        document = Document.objects.get(id=response.data['document']['id'])
        assert document.original_filename == 'test.pdf'
        assert document.document_type == document_type
        assert document.status == 'uploaded'
    
    def test_upload_document_with_auto_process(
        self, authenticated_client, test_pdf_file, mock_document_processing_service,
        temp_media_root
    ):
        """Test document upload with auto-processing"""
        url = '/api/upload/'
        data = {
            'file': test_pdf_file,
            'auto_process': True,
            'use_openai': True
        }
        
        response = authenticated_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'processing' in response.data
        assert response.data['message'] == 'Document uploaded and processed'
        
        # Check processing service was called
        mock_document_processing_service.process_document.assert_called_once()
    
    def test_upload_document_no_file(self, authenticated_client):
        """Test upload without file"""
        url = '/api/upload/'
        data = {}
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'No file provided' in response.data['error']
    
    def test_upload_document_invalid_type(self, authenticated_client, test_pdf_file):
        """Test upload with invalid document type"""
        url = '/api/upload/'
        data = {
            'file': test_pdf_file,
            'document_type': 'invalid-uuid'
        }
        
        response = authenticated_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Invalid document type' in response.data['error']
    
    def test_upload_document_validation_failure(
        self, authenticated_client, mock_document_processing_service, temp_media_root
    ):
        """Test upload with validation failure"""
        # Mock validation failure
        mock_document_processing_service.validate_document.return_value = {
            'is_valid': False,
            'errors': ['File too large'],
            'warnings': []
        }
        
        large_file = TestFileFactory.create_large_file(size_mb=60)
        
        url = '/api/upload/'
        data = {'file': large_file}
        
        response = authenticated_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'File validation failed' in response.data['error']
        assert 'File too large' in response.data['details']
    
    def test_upload_document_duplicate_detection(
        self, authenticated_client, authenticated_user, test_pdf_file,
        mock_document_processing_service, temp_media_root
    ):
        """Test duplicate document detection"""
        # Create existing document with same hash
        existing_doc = DocumentFactory(
            uploaded_by=authenticated_user,
            file_hash='fake_hash_123',
            original_filename='existing.pdf'
        )
        
        url = '/api/upload/'
        data = {'file': test_pdf_file}
        
        response = authenticated_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_409_CONFLICT
        assert 'Duplicate file detected' in response.data['error']
        assert response.data['existing_document']['id'] == str(existing_doc.id)
    
    def test_upload_document_unauthenticated(self, api_client, test_pdf_file):
        """Test upload without authentication"""
        url = '/api/upload/'
        data = {'file': test_pdf_file}
        
        response = api_client.post(url, data, format='multipart')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestDocumentViewSetAPI:
    """Tests for DocumentViewSet API endpoints"""
    
    def test_list_documents(self, authenticated_client, authenticated_user):
        """Test listing documents"""
        # Create documents for the user
        docs = DocumentFactory.create_batch(3, uploaded_by=authenticated_user)
        
        # Create document for different user (should not appear)
        DocumentFactory()
        
        url = '/api/documents/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3
    
    def test_retrieve_document(self, authenticated_client, authenticated_user):
        """Test retrieving a specific document"""
        document = DocumentFactory(uploaded_by=authenticated_user)
        
        url = f'/api/documents/{document.id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(document.id)
        assert response.data['original_filename'] == document.original_filename
    
    def test_process_document_endpoint(
        self, authenticated_client, authenticated_user, mock_document_processing_service
    ):
        """Test document processing endpoint"""
        document = PendingDocumentFactory(uploaded_by=authenticated_user)
        
        url = f'/api/documents/{document.id}/process/'
        data = {'use_openai': True}
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'Document processing completed' in response.data['message']
        assert response.data['status'] == 'approved'
        
        # Check processing service was called
        mock_document_processing_service.process_document.assert_called_once_with(
            document, use_openai=True
        )
    
    def test_process_document_invalid_status(self, authenticated_client, authenticated_user):
        """Test processing document with invalid status"""
        document = DocumentFactory(uploaded_by=authenticated_user, status='approved')
        
        url = f'/api/documents/{document.id}/process/'
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot be processed' in response.data['error']
    
    def test_retry_document_processing(
        self, authenticated_client, authenticated_user, mock_document_processing_service
    ):
        """Test retrying failed document processing"""
        document = DocumentFactory(
            uploaded_by=authenticated_user,
            status='error',
            retry_count=1,
            max_retries=3
        )
        
        url = f'/api/documents/{document.id}/retry/'
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'retry completed' in response.data['message']
        
        # Check retry count was incremented
        document.refresh_from_db()
        assert document.retry_count == 2
    
    def test_retry_document_cannot_retry(self, authenticated_client, authenticated_user):
        """Test retrying document that cannot be retried"""
        document = DocumentFactory(
            uploaded_by=authenticated_user,
            status='approved'  # Cannot retry approved documents
        )
        
        url = f'/api/documents/{document.id}/retry/'
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot be retried' in response.data['error']
    
    def test_get_document_extractions(self, authenticated_client, authenticated_user):
        """Test getting document extractions"""
        document = DocumentFactory(uploaded_by=authenticated_user)
        extractions = DocumentExtractionFactory.create_batch(3, document=document)
        
        url = f'/api/documents/{document.id}/extractions/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3
        assert response.data[0]['field_name'] == extractions[0].field_name
    
    def test_get_document_processing_logs(self, authenticated_client, authenticated_user):
        """Test getting document processing logs"""
        document = DocumentFactory(uploaded_by=authenticated_user)
        
        # Create processing logs
        from tests.factories import DocumentProcessingLogFactory
        logs = DocumentProcessingLogFactory.create_batch(2, document=document)
        
        url = f'/api/documents/{document.id}/processing_logs/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2


class TestDocumentExtractionAPI:
    """Tests for DocumentExtraction API endpoints"""
    
    def test_verify_extraction(self, authenticated_client, authenticated_user):
        """Test verifying an extraction"""
        document = DocumentFactory(uploaded_by=authenticated_user, status='review_required')
        extraction = DocumentExtractionFactory(
            document=document,
            is_verified=False
        )
        
        url = f'/api/extractions/{extraction.id}/verify/'
        data = {
            'corrected_value': 'Corrected Value',
            'correction_reason': 'OCR error fixed'
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'Extraction verified' in response.data['message']
        
        # Check extraction was updated
        extraction.refresh_from_db()
        assert extraction.is_verified is True
        assert extraction.corrected_value == 'Corrected Value'
        assert extraction.correction_reason == 'OCR error fixed'
        assert extraction.verified_by == authenticated_user
    
    def test_verify_extraction_completes_document(self, authenticated_client, authenticated_user):
        """Test that verifying all extractions marks document as approved"""
        document = DocumentFactory(uploaded_by=authenticated_user, status='review_required')
        extraction1 = DocumentExtractionFactory(document=document, is_verified=True)
        extraction2 = DocumentExtractionFactory(document=document, is_verified=False)
        
        url = f'/api/extractions/{extraction2.id}/verify/'
        response = authenticated_client.post(url, {})
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['document_status'] == 'approved'
        
        # Check document status
        document.refresh_from_db()
        assert document.status == 'approved'


class TestDocumentBatchAPI:
    """Tests for DocumentBatch API endpoints"""
    
    def test_create_batch(self, authenticated_client, authenticated_user, document_type):
        """Test creating a document batch"""
        url = '/api/batches/'
        data = {
            'name': 'Test Batch',
            'description': 'Test batch description',
            'document_type': str(document_type.id),
            'auto_approve_threshold': 0.9,
            'total_documents': 5
        }
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Test Batch'
        assert response.data['created_by'] == authenticated_user.id
        
        # Check batch was created
        batch = DocumentBatch.objects.get(id=response.data['id'])
        assert batch.name == 'Test Batch'
        assert batch.created_by == authenticated_user
    
    def test_list_batches(self, authenticated_client, authenticated_user):
        """Test listing document batches"""
        batches = DocumentBatchFactory.create_batch(3, created_by=authenticated_user)
        
        # Create batch for different user (should not appear)
        DocumentBatchFactory()
        
        url = '/api/batches/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3
    
    def test_start_batch_processing(
        self, authenticated_client, authenticated_user, mock_document_processing_service
    ):
        """Test starting batch processing"""
        batch = DocumentBatchFactory(
            created_by=authenticated_user,
            status='created',
            total_documents=2
        )
        
        # Create batch items with documents
        from tests.factories import DocumentBatchItemFactory
        item1 = DocumentBatchItemFactory(batch=batch)
        item2 = DocumentBatchItemFactory(batch=batch)
        
        url = f'/api/batches/{batch.id}/start_processing/'
        data = {'use_openai': True}
        
        response = authenticated_client.post(url, data)
        
        assert response.status_code == status.HTTP_200_OK
        assert 'Batch processing completed' in response.data['message']
        
        # Check batch status
        batch.refresh_from_db()
        assert batch.status in ['completed', 'partially_completed', 'failed']
        
        # Check processing service was called for each document
        assert mock_document_processing_service.process_document.call_count == 2
    
    def test_start_batch_processing_invalid_status(self, authenticated_client, authenticated_user):
        """Test starting batch processing with invalid status"""
        batch = DocumentBatchFactory(
            created_by=authenticated_user,
            status='completed'  # Cannot start already completed batch
        )
        
        url = f'/api/batches/{batch.id}/start_processing/'
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'cannot be started' in response.data['error']


class TestProcessingStatsAPI:
    """Tests for processing statistics endpoint"""
    
    def test_get_processing_stats(self, authenticated_client, authenticated_user):
        """Test getting processing statistics"""
        # Create documents with different statuses
        DocumentFactory(uploaded_by=authenticated_user, status='uploaded')
        DocumentFactory(uploaded_by=authenticated_user, status='processing')
        DocumentFactory(uploaded_by=authenticated_user, status='approved')
        DocumentFactory(uploaded_by=authenticated_user, status='review_required')
        DocumentFactory(uploaded_by=authenticated_user, status='error')
        
        # Create processing logs
        from tests.factories import DocumentProcessingLogFactory
        doc = DocumentFactory(uploaded_by=authenticated_user)
        DocumentProcessingLogFactory.create_batch(3, document=doc)
        
        url = '/api/stats/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_documents'] == 6  # 5 + 1 from logs
        assert response.data['processing_summary']['pending'] == 1
        assert response.data['processing_summary']['processing'] == 1
        assert response.data['processing_summary']['completed'] == 1
        assert response.data['processing_summary']['review_required'] == 1
        assert response.data['processing_summary']['errors'] == 1
        assert len(response.data['recent_activity']) <= 10
    
    def test_processing_stats_empty(self, authenticated_client):
        """Test processing stats with no documents"""
        url = '/api/stats/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_documents'] == 0
        assert response.data['recent_activity'] == []


class TestDocumentTypeAPI:
    """Tests for DocumentType API endpoints"""
    
    def test_list_document_types(self, authenticated_client):
        """Test listing active document types"""
        active_types = DocumentTypeFactory.create_batch(3, is_active=True)
        inactive_type = DocumentTypeFactory(is_active=False)
        
        url = '/api/document-types/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 3  # Only active types
    
    def test_retrieve_document_type(self, authenticated_client):
        """Test retrieving a specific document type"""
        doc_type = DocumentTypeFactory()
        
        url = f'/api/document-types/{doc_type.id}/'
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(doc_type.id)
        assert response.data['name'] == doc_type.name


class TestAPIPermissions:
    """Tests for API permission handling"""
    
    def test_unauthenticated_access_denied(self, api_client):
        """Test that unauthenticated requests are denied"""
        endpoints = [
            '/api/documents/',
            '/api/batches/',
            '/api/extractions/',
            '/api/stats/',
        ]
        
        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_cross_organization_access_denied(self, api_client):
        """Test that users cannot access other organization's data"""
        from tests.factories import UserFactory, OrganizationFactory
        
        # Create two different organizations
        org1 = OrganizationFactory()
        org2 = OrganizationFactory()
        
        user1 = UserFactory(organization=org1)
        user2 = UserFactory(organization=org2)
        
        # Create document for user1
        document = DocumentFactory(uploaded_by=user1)
        
        # User2 should not be able to access user1's document
        api_client.force_authenticate(user=user2)
        url = f'/api/documents/{document.id}/'
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND