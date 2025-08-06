import { http, HttpResponse } from 'msw'

// Mock data
const mockDocuments = [
  {
    id: '1',
    original_filename: 'invoice_001.pdf',
    document_type_name: 'Invoice',
    status: 'approved',
    created_at: '2025-08-01T10:30:00Z',
    processing_completed_at: '2025-08-01T10:31:15Z',
    ocr_confidence: 0.95,
    file_size_mb: 2.4,
    extractions_count: 12,
    unverified_extractions_count: 0,
    uploaded_by_name: 'Test User'
  },
  {
    id: '2',
    original_filename: 'contract_draft.docx',
    document_type_name: 'Contract',
    status: 'processing',
    created_at: '2025-08-01T11:15:00Z',
    ocr_confidence: null,
    file_size_mb: 1.8,
    extractions_count: 0,
    unverified_extractions_count: 0,
    uploaded_by_name: 'Test User'
  },
  {
    id: '3',
    original_filename: 'receipt_scan.jpg',
    document_type_name: 'Receipt',
    status: 'review_required',
    created_at: '2025-08-01T09:45:00Z',
    processing_completed_at: '2025-08-01T09:46:30Z',
    ocr_confidence: 0.72,
    file_size_mb: 3.1,
    extractions_count: 8,
    unverified_extractions_count: 3,
    uploaded_by_name: 'Test User'
  }
]

const mockExtractions = [
  {
    id: '1',
    field_name: 'document_title',
    field_value: 'Invoice #12345',
    field_type: 'text',
    confidence: 0.95,
    is_verified: false,
    original_value: 'Invoice #12345'
  },
  {
    id: '2',
    field_name: 'amount',
    field_value: '$1,234.56',
    field_type: 'currency',
    confidence: 0.98,
    is_verified: true,
    original_value: '$1,234.56'
  },
  {
    id: '3',
    field_name: 'date',
    field_value: '2025-08-01',
    field_type: 'date',
    confidence: 0.72,
    is_verified: false,
    original_value: '2025-08-01'
  }
]

const mockBatches = [
  {
    id: '1',
    name: 'Invoice Processing Batch #1',
    status: 'completed',
    total_documents: 10,
    processed_documents: 10,
    successful_documents: 9,
    failed_documents: 1,
    completion_percentage: 100,
    success_rate: 90,
    created_at: '2025-08-01T08:00:00Z'
  }
]

const mockProcessingStats = {
  total_documents: 25,
  status_breakdown: {
    uploaded: { label: 'Uploaded', count: 3 },
    processing: { label: 'Processing', count: 2 },
    approved: { label: 'Approved', count: 15 },
    review_required: { label: 'Review Required', count: 4 },
    error: { label: 'Error', count: 1 }
  },
  processing_summary: {
    pending: 3,
    processing: 2,
    completed: 15,
    review_required: 4,
    errors: 1
  },
  recent_activity: [
    {
      document_name: 'invoice_001.pdf',
      step: 'OCR Processing',
      status: 'Completed',
      message: 'OCR processing completed successfully',
      timestamp: '2025-08-01T10:31:00Z'
    }
  ]
}

export const handlers = [
  // Authentication handlers
  http.post('/api/auth/login/', () => {
    return HttpResponse.json({
      access: 'mock-access-token',
      refresh: 'mock-refresh-token',
      user: {
        id: 1,
        email: 'test@example.com',
        first_name: 'Test',
        last_name: 'User'
      }
    })
  }),

  http.post('/api/auth/logout/', () => {
    return HttpResponse.json({ message: 'Logged out successfully' })
  }),

  http.get('/api/auth/me/', () => {
    return HttpResponse.json({
      id: 1,
      email: 'test@example.com',
      first_name: 'Test',
      last_name: 'User',
      organization: {
        id: 1,
        name: 'Test Organization'
      },
      role: 'business_owner'
    })
  }),

  // Document handlers
  http.get('/api/documents/', () => {
    return HttpResponse.json({
      results: mockDocuments,
      count: mockDocuments.length
    })
  }),

  http.get('/api/documents/:id/', ({ params }) => {
    const document = mockDocuments.find(doc => doc.id === params.id)
    if (!document) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(document)
  }),

  http.post('/api/documents/:id/process/', () => {
    return HttpResponse.json({
      message: 'Document processing completed',
      status: 'approved',
      extractions_count: 3,
      review_required: false
    })
  }),

  http.post('/api/documents/:id/retry/', () => {
    return HttpResponse.json({
      message: 'Document processing retry completed',
      status: 'processing'
    })
  }),

  http.get('/api/documents/:id/extractions/', () => {
    return HttpResponse.json(mockExtractions)
  }),

  http.get('/api/documents/:id/processing_logs/', () => {
    return HttpResponse.json([
      {
        id: '1',
        step: 'upload',
        step_display: 'File Upload',
        status: 'completed',
        status_display: 'Completed',
        message: 'File uploaded successfully',
        created_at: '2025-08-01T10:30:00Z',
        duration_seconds: 0.5
      }
    ])
  }),

  // Document upload handler
  http.post('/api/upload/', async ({ request }) => {
    const formData = await request.formData()
    const file = formData.get('file')
    
    if (!file) {
      return HttpResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      )
    }

    return HttpResponse.json({
      document: {
        id: 'new-doc-id',
        original_filename: file.name,
        status: 'uploaded',
        created_at: new Date().toISOString()
      },
      message: 'Document uploaded successfully'
    }, { status: 201 })
  }),

  // Document extraction handlers
  http.post('/api/extractions/:id/verify/', () => {
    return HttpResponse.json({
      message: 'Extraction verified',
      document_status: 'approved'
    })
  }),

  // Batch processing handlers
  http.get('/api/batches/', () => {
    return HttpResponse.json({
      results: mockBatches,
      count: mockBatches.length
    })
  }),

  http.post('/api/batches/', async ({ request }) => {
    const data = await request.json()
    return HttpResponse.json({
      id: 'new-batch-id',
      ...data,
      status: 'created',
      created_at: new Date().toISOString()
    }, { status: 201 })
  }),

  http.post('/api/batches/:id/start_processing/', () => {
    return HttpResponse.json({
      message: 'Batch processing completed',
      status: 'completed',
      successful: 9,
      failed: 1
    })
  }),

  // Processing stats handler
  http.get('/api/stats/', () => {
    return HttpResponse.json(mockProcessingStats)
  }),

  // Document types handler
  http.get('/api/document-types/', () => {
    return HttpResponse.json({
      results: [
        {
          id: '1',
          name: 'Invoice',
          description: 'Business invoices',
          ocr_enabled: true,
          ai_extraction_enabled: true
        },
        {
          id: '2',
          name: 'Contract',
          description: 'Legal contracts',
          ocr_enabled: true,
          ai_extraction_enabled: true
        }
      ]
    })
  }),

  // Error handlers for testing error scenarios
  http.post('/api/upload/error', () => {
    return HttpResponse.json(
      { error: 'Upload failed', details: ['File too large'] },
      { status: 400 }
    )
  }),

  http.post('/api/documents/error/process/', () => {
    return HttpResponse.json(
      { error: 'Processing failed' },
      { status: 500 }
    )
  })
]