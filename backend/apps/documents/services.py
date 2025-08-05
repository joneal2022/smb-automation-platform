import os
import hashlib
import mimetypes
import logging
from typing import Dict, List, Optional, Tuple
from PIL import Image
import pytesseract
import openai
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone
from .models import Document, DocumentExtraction, DocumentProcessingLog, DocumentType

logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = getattr(settings, 'OPENAI_API_KEY', '')


class DocumentProcessingService:
    """Service for handling document processing operations"""
    
    def __init__(self):
        self.supported_image_formats = ['image/jpeg', 'image/png', 'image/webp', 'image/heic', 'image/heif']
        self.supported_document_formats = ['application/pdf']
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file for duplicate detection"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def validate_document(self, uploaded_file: UploadedFile, document_type: Optional[DocumentType] = None) -> Dict:
        """Validate uploaded document against constraints"""
        errors = []
        warnings = []
        
        # Check file size
        max_size = (document_type.max_file_size_mb if document_type else 50) * 1024 * 1024
        if uploaded_file.size > max_size:
            errors.append(f"File size ({uploaded_file.size / (1024*1024):.1f}MB) exceeds maximum allowed ({max_size / (1024*1024)}MB)")
        
        # Check file extension
        file_extension = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else ''
        allowed_extensions = document_type.allowed_extensions if document_type and document_type.allowed_extensions else ['pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx']
        
        if file_extension not in allowed_extensions:
            errors.append(f"File extension '{file_extension}' not allowed. Allowed: {', '.join(allowed_extensions)}")
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(uploaded_file.name)
        if not mime_type:
            warnings.append("Could not determine file type")
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'mime_type': mime_type,
            'file_extension': file_extension
        }
    
    def create_processing_log(self, document: Document, step: str, status: str, message: str, 
                            details: Dict = None, user=None, duration: float = None):
        """Create a processing log entry"""
        DocumentProcessingLog.objects.create(
            document=document,
            step=step,
            status=status,
            message=message,
            details=details or {},
            performed_by=user,
            duration_seconds=duration
        )
    
    def process_with_tesseract_ocr(self, document: Document) -> Dict:
        """Process document using Tesseract OCR (fallback option)"""
        try:
            start_time = timezone.now()
            self.create_processing_log(document, 'ocr', 'started', 'Starting Tesseract OCR processing')
            
            # For images, use Tesseract directly
            if document.mime_type in self.supported_image_formats:
                with Image.open(document.file.path) as img:
                    # Get OCR text and confidence data
                    ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                    text = pytesseract.image_to_string(img)
                    
                    # Calculate average confidence
                    confidences = [int(conf) for conf in ocr_data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    # Detect language
                    detected_lang = pytesseract.image_to_string(img, config='--psm 0').split('\n')[0] if text.strip() else 'eng'
                    
                    duration = (timezone.now() - start_time).total_seconds()
                    
                    result = {
                        'text': text.strip(),
                        'confidence': avg_confidence / 100.0,  # Convert to 0-1 scale
                        'language': detected_lang[:2] if detected_lang else 'en',
                        'method': 'tesseract',
                        'processing_time': duration
                    }
                    
                    self.create_processing_log(
                        document, 'ocr', 'completed', 
                        f'Tesseract OCR completed. Extracted {len(text)} characters with {avg_confidence:.1f}% confidence',
                        {'characters_extracted': len(text), 'confidence': avg_confidence},
                        duration=duration
                    )
                    
                    return result
            else:
                raise Exception(f"Tesseract OCR not supported for {document.mime_type}")
                
        except Exception as e:
            duration = (timezone.now() - start_time).total_seconds()
            error_msg = f"Tesseract OCR failed: {str(e)}"
            logger.error(error_msg)
            
            self.create_processing_log(
                document, 'ocr', 'failed', error_msg,
                {'error': str(e)}, duration=duration
            )
            
            return {
                'error': error_msg,
                'method': 'tesseract',
                'processing_time': duration
            }
    
    def process_with_openai_vision(self, document: Document) -> Dict:
        """Process document using OpenAI Vision API"""
        try:
            start_time = timezone.now()
            self.create_processing_log(document, 'ocr', 'started', 'Starting OpenAI Vision OCR processing')
            
            if not openai.api_key:
                raise Exception("OpenAI API key not configured")
            
            # Only process images with OpenAI Vision
            if document.mime_type not in self.supported_image_formats:
                raise Exception(f"OpenAI Vision not supported for {document.mime_type}")
            
            # Read and encode image
            with open(document.file.path, "rb") as image_file:
                import base64
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Create OpenAI Vision request
            response = openai.chat.completions.create(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "content": "Extract all text from this document. Maintain the original formatting as much as possible. Return only the extracted text, no additional commentary."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{document.mime_type};base64,{image_data}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0
            )
            
            extracted_text = response.choices[0].message.content.strip()
            duration = (timezone.now() - start_time).total_seconds()
            
            # OpenAI doesn't provide confidence scores, so we estimate based on response quality
            confidence = 0.95 if len(extracted_text) > 10 else 0.7
            
            result = {
                'text': extracted_text,
                'confidence': confidence,
                'language': 'auto-detected',
                'method': 'openai_vision',
                'processing_time': duration,
                'tokens_used': response.usage.total_tokens if hasattr(response, 'usage') else None
            }
            
            self.create_processing_log(
                document, 'ocr', 'completed',
                f'OpenAI Vision OCR completed. Extracted {len(extracted_text)} characters',
                {
                    'characters_extracted': len(extracted_text),
                    'tokens_used': result.get('tokens_used'),
                    'confidence_estimate': confidence
                },
                duration=duration
            )
            
            return result
            
        except Exception as e:
            duration = (timezone.now() - start_time).total_seconds()
            error_msg = f"OpenAI Vision OCR failed: {str(e)}"
            logger.error(error_msg)
            
            self.create_processing_log(
                document, 'ocr', 'failed', error_msg,
                {'error': str(e)}, duration=duration
            )
            
            return {
                'error': error_msg,
                'method': 'openai_vision',
                'processing_time': duration
            }
    
    def extract_structured_data(self, document: Document, ocr_text: str) -> List[Dict]:
        """Extract structured data fields using AI"""
        try:
            start_time = timezone.now()
            self.create_processing_log(document, 'extraction', 'started', 'Starting AI data extraction')
            
            if not openai.api_key:
                raise Exception("OpenAI API key not configured")
            
            # Get extraction template from document type
            extraction_template = {}
            if document.document_type and document.document_type.extraction_template:
                extraction_template = document.document_type.extraction_template
            
            # Default extraction fields if no template
            if not extraction_template:
                extraction_template = {
                    "fields": [
                        {"name": "document_title", "type": "text", "description": "Main title or header of the document"},
                        {"name": "date", "type": "date", "description": "Any dates mentioned in the document"},
                        {"name": "amount", "type": "currency", "description": "Any monetary amounts"},
                        {"name": "contact_info", "type": "text", "description": "Email addresses, phone numbers, or addresses"},
                        {"name": "key_entities", "type": "text", "description": "Important names, organizations, or entities"}
                    ]
                }
            
            # Create extraction prompt
            fields_description = "\n".join([
                f"- {field['name']} ({field['type']}): {field['description']}"
                for field in extraction_template.get('fields', [])
            ])
            
            prompt = f"""
Extract the following information from this document text:

{fields_description}

Document Text:
{ocr_text}

Return the extracted data as a JSON object with the field names as keys. If a field is not found, use null as the value. Include a confidence score (0-1) for each field.

Format:
{{
    "field_name": {{
        "value": "extracted_value",
        "confidence": 0.95,
        "type": "text"
    }}
}}
"""
            
            response = openai.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=2000,
                temperature=0
            )
            
            import json
            extracted_data = json.loads(response.choices[0].message.content)
            duration = (timezone.now() - start_time).total_seconds()
            
            # Convert to list format for database storage
            extractions = []
            for field_name, field_data in extracted_data.items():
                if field_data and field_data.get('value'):
                    extractions.append({
                        'field_name': field_name,
                        'field_value': str(field_data['value']),
                        'field_type': field_data.get('type', 'text'),
                        'confidence': field_data.get('confidence', 0.8),
                        'original_value': str(field_data['value'])
                    })
            
            self.create_processing_log(
                document, 'extraction', 'completed',
                f'AI extraction completed. Extracted {len(extractions)} fields',
                {
                    'fields_extracted': len(extractions),
                    'template_used': bool(document.document_type and document.document_type.extraction_template)
                },
                duration=duration
            )
            
            return extractions
            
        except Exception as e:
            duration = (timezone.now() - start_time).total_seconds()
            error_msg = f"AI data extraction failed: {str(e)}"
            logger.error(error_msg)
            
            self.create_processing_log(
                document, 'extraction', 'failed', error_msg,
                {'error': str(e)}, duration=duration
            )
            
            return []
    
    def process_document(self, document: Document, use_openai: bool = True) -> Dict:
        """Main document processing pipeline"""
        try:
            # Update document status
            document.status = 'processing'
            document.processing_started_at = timezone.now()
            document.save()
            
            # Step 1: OCR Processing
            if use_openai and document.mime_type in self.supported_image_formats:
                ocr_result = self.process_with_openai_vision(document)
            else:
                ocr_result = self.process_with_tesseract_ocr(document)
            
            if 'error' in ocr_result:
                document.status = 'error'
                document.error_message = ocr_result['error']
                document.save()
                return {'success': False, 'error': ocr_result['error']}
            
            # Update document with OCR results
            document.ocr_text = ocr_result['text']
            document.ocr_confidence = ocr_result['confidence']
            document.ocr_language = ocr_result.get('language', 'en')
            document.status = 'ocr_complete'
            document.save()
            
            # Step 2: Data Extraction
            if document.document_type and document.document_type.ai_extraction_enabled:
                extractions = self.extract_structured_data(document, ocr_result['text'])
                
                # Save extractions to database
                for extraction_data in extractions:
                    DocumentExtraction.objects.create(
                        document=document,
                        field_name=extraction_data['field_name'],
                        field_value=extraction_data['field_value'],
                        field_type=extraction_data['field_type'],
                        confidence=extraction_data['confidence'],
                        original_value=extraction_data['original_value']
                    )
                
                document.status = 'extraction_complete'
            
            # Step 3: Determine if review is needed
            min_confidence = 0.8  # Configurable threshold
            low_confidence_extractions = DocumentExtraction.objects.filter(
                document=document,
                confidence__lt=min_confidence
            ).count()
            
            if low_confidence_extractions > 0:
                document.status = 'review_required'
            else:
                document.status = 'approved'
            
            document.processing_completed_at = timezone.now()
            document.save()
            
            self.create_processing_log(
                document, 'approval', 'completed',
                f'Document processing completed. Status: {document.status}',
                {
                    'final_status': document.status,
                    'ocr_confidence': ocr_result['confidence'],
                    'extraction_count': document.extractions.count(),
                    'low_confidence_count': low_confidence_extractions
                }
            )
            
            return {
                'success': True,
                'status': document.status,
                'ocr_result': ocr_result,
                'extractions_count': document.extractions.count(),
                'review_required': document.status == 'review_required'
            }
            
        except Exception as e:
            # Handle any unexpected errors
            document.status = 'error'
            document.error_message = str(e)
            document.processing_completed_at = timezone.now()
            document.save()
            
            self.create_processing_log(
                document, 'error', 'failed',
                f'Unexpected error during processing: {str(e)}',
                {'error': str(e)}
            )
            
            logger.error(f"Document processing failed for {document.id}: {str(e)}")
            return {'success': False, 'error': str(e)}


# Service instance
document_processing_service = DocumentProcessingService()