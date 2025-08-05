import os
import hashlib
import mimetypes
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Document, DocumentType, DocumentExtraction, DocumentBatch, DocumentProcessingLog
from .services import document_processing_service
from .serializers import (
    DocumentSerializer, DocumentTypeSerializer, DocumentExtractionSerializer,
    DocumentBatchSerializer, DocumentProcessingLogSerializer
)


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet for managing documents"""
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    def get_queryset(self):
        """Filter documents by user's organization"""
        return Document.objects.filter(uploaded_by__organization=self.request.user.organization)
    
    def perform_create(self, serializer):
        """Handle document upload and initial processing"""
        serializer.save(uploaded_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def process(self, request, pk=None):
        """Trigger document processing"""
        document = self.get_object()
        
        if document.status not in ['uploaded', 'error']:
            return Response(
                {'error': f'Document cannot be processed. Current status: {document.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start processing asynchronously (in a real app, use Celery)
        use_openai = request.data.get('use_openai', True)
        result = document_processing_service.process_document(document, use_openai=use_openai)
        
        if result['success']:
            return Response({
                'message': 'Document processing completed',
                'status': result['status'],
                'extractions_count': result['extractions_count'],
                'review_required': result['review_required']
            })
        else:
            return Response(
                {'error': result['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'])
    def extractions(self, request, pk=None):
        """Get document extractions"""
        document = self.get_object()
        extractions = document.extractions.all()
        serializer = DocumentExtractionSerializer(extractions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def processing_logs(self, request, pk=None):
        """Get document processing logs"""
        document = self.get_object()
        logs = document.processing_logs.all()
        serializer = DocumentProcessingLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """Retry failed document processing"""
        document = self.get_object()
        
        if not document.can_retry():
            return Response(
                {'error': 'Document cannot be retried'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Increment retry count
        document.retry_count += 1
        document.error_message = ''
        document.save()
        
        # Retry processing
        use_openai = request.data.get('use_openai', True)
        result = document_processing_service.process_document(document, use_openai=use_openai)
        
        if result['success']:
            return Response({
                'message': 'Document processing retry completed',
                'status': result['status']
            })
        else:
            return Response(
                {'error': result['error']},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class DocumentTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing document types"""
    serializer_class = DocumentTypeSerializer
    permission_classes = [IsAuthenticated]
    queryset = DocumentType.objects.filter(is_active=True)


class DocumentExtractionViewSet(viewsets.ModelViewSet):
    """ViewSet for managing document extractions"""
    serializer_class = DocumentExtractionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter extractions by user's organization"""
        return DocumentExtraction.objects.filter(
            document__uploaded_by__organization=self.request.user.organization
        )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify an extraction"""
        extraction = self.get_object()
        
        # Update verification status
        extraction.is_verified = True
        extraction.verified_by = request.user
        extraction.verified_at = timezone.now()
        
        # Handle corrections
        if 'corrected_value' in request.data:
            extraction.corrected_value = request.data['corrected_value']
            extraction.correction_reason = request.data.get('correction_reason', '')
        
        extraction.save()
        
        # Check if all extractions for this document are verified
        document = extraction.document
        unverified_count = document.extractions.filter(is_verified=False).count()
        
        if unverified_count == 0 and document.status == 'review_required':
            document.status = 'approved'
            document.save()
            
            document_processing_service.create_processing_log(
                document, 'review', 'completed',
                'All extractions verified. Document approved.',
                user=request.user
            )
        
        return Response({
            'message': 'Extraction verified',
            'document_status': document.status
        })


class DocumentBatchViewSet(viewsets.ModelViewSet):
    """ViewSet for managing document batches"""
    serializer_class = DocumentBatchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter batches by user's organization"""
        return DocumentBatch.objects.filter(
            created_by__organization=self.request.user.organization
        )
    
    def perform_create(self, serializer):
        """Set the created_by user"""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def start_processing(self, request, pk=None):
        """Start batch processing"""
        batch = self.get_object()
        
        if batch.status != 'created':
            return Response(
                {'error': f'Batch cannot be started. Current status: {batch.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update batch status
        batch.status = 'processing'
        batch.started_at = timezone.now()
        batch.save()
        
        # Process each document in the batch
        # In a real application, this would be handled by Celery tasks
        use_openai = request.data.get('use_openai', True)
        
        for batch_item in batch.items.all():
            document = batch_item.document
            batch_item.started_at = timezone.now()
            batch_item.save()
            
            result = document_processing_service.process_document(document, use_openai=use_openai)
            
            batch_item.completed_at = timezone.now()
            batch_item.save()
            
            # Update batch counters
            batch.processed_documents += 1
            if result['success']:
                batch.successful_documents += 1
            else:
                batch.failed_documents += 1
            batch.save()
        
        # Final batch status
        if batch.failed_documents == 0:
            batch.status = 'completed'
        elif batch.successful_documents == 0:
            batch.status = 'failed'
        else:
            batch.status = 'partially_completed'
        
        batch.completed_at = timezone.now()
        batch.save()
        
        return Response({
            'message': 'Batch processing completed',
            'status': batch.status,
            'successful': batch.successful_documents,
            'failed': batch.failed_documents
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_document(request):
    """Handle document upload with validation"""
    if 'file' not in request.FILES:
        return Response(
            {'error': 'No file provided'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    uploaded_file = request.FILES['file']
    document_type_id = request.data.get('document_type')
    
    # Get document type if specified
    document_type = None
    if document_type_id:
        try:
            document_type = DocumentType.objects.get(id=document_type_id, is_active=True)
        except DocumentType.DoesNotExist:
            return Response(
                {'error': 'Invalid document type'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    # Validate document
    validation_result = document_processing_service.validate_document(uploaded_file, document_type)
    
    if not validation_result['is_valid']:
        return Response(
            {'error': 'File validation failed', 'details': validation_result['errors']},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Save file temporarily to calculate hash
        temp_path = default_storage.save(f'temp/{uploaded_file.name}', ContentFile(uploaded_file.read()))
        temp_full_path = os.path.join(default_storage.location, temp_path)
        
        # Calculate file hash for duplicate detection
        file_hash = document_processing_service.calculate_file_hash(temp_full_path)
        
        # Check for duplicates
        existing_document = Document.objects.filter(
            file_hash=file_hash,
            uploaded_by__organization=request.user.organization
        ).first()
        
        if existing_document:
            # Clean up temp file
            default_storage.delete(temp_path)
            return Response(
                {
                    'error': 'Duplicate file detected',
                    'existing_document': {
                        'id': existing_document.id,
                        'filename': existing_document.original_filename,
                        'uploaded_at': existing_document.created_at
                    }
                },
                status=status.HTTP_409_CONFLICT
            )
        
        # Create document record
        document = Document.objects.create(
            original_filename=uploaded_file.name,
            file_size=uploaded_file.size,
            file_hash=file_hash,
            mime_type=validation_result['mime_type'] or 'application/octet-stream',
            document_type=document_type,
            uploaded_by=request.user,
            status='uploaded'
        )
        
        # Move file to proper location
        final_path = f'documents/{request.user.organization.id}/{timezone.now().year}/{timezone.now().month:02d}/{document.id}_{uploaded_file.name}'
        document.file.save(uploaded_file.name, ContentFile(open(temp_full_path, 'rb').read()))
        
        # Clean up temp file
        default_storage.delete(temp_path)
        
        # Log upload
        document_processing_service.create_processing_log(
            document, 'upload', 'completed',
            f'Document uploaded successfully: {uploaded_file.name}',
            {
                'file_size': uploaded_file.size,
                'mime_type': validation_result['mime_type'],
                'document_type': document_type.name if document_type else None
            },
            user=request.user
        )
        
        # Auto-process if requested
        if request.data.get('auto_process', False):
            use_openai = request.data.get('use_openai', True)
            processing_result = document_processing_service.process_document(document, use_openai=use_openai)
            
            serializer = DocumentSerializer(document)
            return Response({
                'document': serializer.data,
                'processing': processing_result,
                'message': 'Document uploaded and processed'
            }, status=status.HTTP_201_CREATED)
        
        serializer = DocumentSerializer(document)
        return Response({
            'document': serializer.data,
            'message': 'Document uploaded successfully'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Upload failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def processing_stats(request):
    """Get document processing statistics"""
    user_org = request.user.organization
    
    # Base queryset for user's organization
    documents = Document.objects.filter(uploaded_by__organization=user_org)
    
    stats = {
        'total_documents': documents.count(),
        'status_breakdown': {},
        'processing_summary': {
            'pending': documents.filter(status='uploaded').count(),
            'processing': documents.filter(status='processing').count(),
            'completed': documents.filter(status__in=['approved', 'extraction_complete']).count(),
            'review_required': documents.filter(status='review_required').count(),
            'errors': documents.filter(status='error').count(),
        },
        'recent_activity': []
    }
    
    # Status breakdown
    for status_choice in Document.STATUS_CHOICES:
        status_key = status_choice[0]
        status_label = status_choice[1]
        count = documents.filter(status=status_key).count()
        if count > 0:
            stats['status_breakdown'][status_key] = {
                'label': status_label,
                'count': count
            }
    
    # Recent activity (last 10 processing logs)
    recent_logs = DocumentProcessingLog.objects.filter(
        document__uploaded_by__organization=user_org
    ).select_related('document').order_by('-created_at')[:10]
    
    for log in recent_logs:
        stats['recent_activity'].append({
            'document_name': log.document.original_filename,
            'step': log.get_step_display(),
            'status': log.get_status_display(),
            'message': log.message,
            'timestamp': log.created_at
        })
    
    return Response(stats)
