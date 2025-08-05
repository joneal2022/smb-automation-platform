import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockDocument, createMockExtraction } from '../../test/utils'
import DocumentReviewInterface from './DocumentReviewInterface'

// Mock fetch for API calls
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('DocumentReviewInterface', () => {
  const mockOnReviewComplete = vi.fn()
  const documentId = 'test-doc-id'

  const mockDocument = createMockDocument({
    id: documentId,
    status: 'review_required',
    ocr_confidence: 0.75,
    ocr_text: 'Sample OCR text from document',
    unverified_extractions_count: 2
  })

  const mockExtractions = [
    createMockExtraction({
      id: '1',
      field_name: 'amount',
      field_value: '$1,234.56',
      confidence: 0.95,
      is_verified: false
    }),
    createMockExtraction({
      id: '2',
      field_name: 'date',
      field_value: '2025-08-01',
      confidence: 0.72,
      is_verified: false
    }),
    createMockExtraction({
      id: '3',
      field_name: 'vendor_name',
      field_value: 'Test Company',
      confidence: 0.88,
      is_verified: true
    })
  ]

  const mockProcessingLogs = [
    {
      id: '1',
      step: 'upload',
      step_display: 'File Upload',
      status: 'completed',
      status_display: 'Completed',
      message: 'File uploaded successfully',
      created_at: '2025-08-01T10:30:00Z',
      duration_seconds: 0.5
    },
    {
      id: '2',
      step: 'ocr',
      step_display: 'OCR Processing',
      status: 'completed',
      status_display: 'Completed',
      message: 'OCR processing completed',
      created_at: '2025-08-01T10:31:00Z',
      duration_seconds: 2.5
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
    
    // Mock localStorage
    Object.defineProperty(window, 'localStorage', {
      value: {
        getItem: vi.fn(() => 'mock-token'),
        setItem: vi.fn(),
        removeItem: vi.fn()
      },
      writable: true
    })

    // Setup default API responses
    mockFetch.mockImplementation((url) => {
      if (url.includes(`/api/documents/${documentId}/`)) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockDocument)
        })
      }
      if (url.includes(`/api/documents/${documentId}/extractions/`)) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockExtractions)
        })
      }
      if (url.includes(`/api/documents/${documentId}/processing_logs/`)) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockProcessingLogs)
        })
      }
      return Promise.reject(new Error('Unknown endpoint'))
    })
  })

  it('renders loading state initially', () => {
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)
    
    expect(screen.getByTestId('document-review-loading')).toBeInTheDocument()
    expect(screen.getByText(/loading document details/i)).toBeInTheDocument()
  })

  it('renders document header after loading', async () => {
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('document-review-header')).toBeInTheDocument()
    })

    expect(screen.getByText(mockDocument.original_filename)).toBeInTheDocument()
    expect(screen.getByText(/2\.4 MB/)).toBeInTheDocument()
    expect(screen.getByText(/uploaded:/i)).toBeInTheDocument()
  })

  it('displays review progress correctly', async () => {
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('review-progress-card')).toBeInTheDocument()
    })

    // 1 of 3 fields verified (33%)
    expect(screen.getByText('1 of 3 fields verified')).toBeInTheDocument()
    expect(screen.getByText('33% complete')).toBeInTheDocument()
  })

  it('renders extracted fields with correct data', async () => {
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('extraction-fields-list')).toBeInTheDocument()
    })

    // Check all extractions are displayed
    expect(screen.getByTestId('extraction-field-amount')).toBeInTheDocument()
    expect(screen.getByTestId('extraction-field-date')).toBeInTheDocument()
    expect(screen.getByTestId('extraction-field-vendor_name')).toBeInTheDocument()

    // Check field values
    expect(screen.getByText('$1,234.56')).toBeInTheDocument()
    expect(screen.getByText('2025-08-01')).toBeInTheDocument()
    expect(screen.getByText('Test Company')).toBeInTheDocument()
  })

  it('shows confidence badges with correct colors', async () => {
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('extraction-fields-list')).toBeInTheDocument()
    })

    // High confidence (95%) should show as success
    const amountField = screen.getByTestId('extraction-field-amount')
    expect(amountField).toContainHTML('95.0%')
    
    // Low confidence (72%) should show as warning
    const dateField = screen.getByTestId('extraction-field-date')
    expect(dateField).toContainHTML('72.0%')
  })

  it('allows verifying a field', async () => {
    const user = userEvent.setup()
    
    // Mock successful verification
    mockFetch.mockImplementation((url, options) => {
      if (url.includes('/verify/') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            message: 'Extraction verified',
            document_status: 'review_required'
          })
        })
      }
      // Fall back to default mocks
      return mockFetch(url)
    })

    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('extraction-fields-list')).toBeInTheDocument()
    })

    const verifyButton = screen.getByTestId('verify-field-amount')
    await user.click(verifyButton)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/extractions/1/verify/'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          })
        })
      )
    })
  })

  it('allows editing a field', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('extraction-fields-list')).toBeInTheDocument()
    })

    const editButton = screen.getByTestId('edit-field-amount')
    await user.click(editButton)

    // Should show edit form
    expect(screen.getByTestId('edit-field-amount')).toBeInTheDocument()
    expect(screen.getByTestId('correction-reason-amount')).toBeInTheDocument()

    // Should show save and cancel buttons
    expect(screen.getByTestId('save-edit-amount')).toBeInTheDocument()
    expect(screen.getByTestId('cancel-edit-amount')).toBeInTheDocument()
  })

  it('saves field corrections', async () => {
    const user = userEvent.setup()
    
    // Mock successful save
    mockFetch.mockImplementation((url, options) => {
      if (url.includes('/verify/') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            message: 'Extraction verified',
            document_status: 'approved'
          })
        })
      }
      return mockFetch(url)
    })

    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('extraction-fields-list')).toBeInTheDocument()
    })

    // Start editing
    const editButton = screen.getByTestId('edit-field-amount')
    await user.click(editButton)

    // Enter corrected value
    const valueInput = screen.getByTestId('edit-field-amount')
    await user.clear(valueInput)
    await user.type(valueInput, '$1,500.00')

    // Enter correction reason
    const reasonInput = screen.getByTestId('correction-reason-amount')
    await user.type(reasonInput, 'OCR misread the amount')

    // Save changes
    const saveButton = screen.getByTestId('save-edit-amount')
    await user.click(saveButton)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/extractions/1/verify/'),
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            corrected_value: '$1,500.00',
            correction_reason: 'OCR misread the amount'
          })
        })
      )
    })
  })

  it('cancels field editing', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('extraction-fields-list')).toBeInTheDocument()
    })

    // Start editing
    const editButton = screen.getByTestId('edit-field-amount')
    await user.click(editButton)

    // Cancel editing
    const cancelButton = screen.getByTestId('cancel-edit-amount')
    await user.click(cancelButton)

    // Should return to view mode
    expect(screen.queryByTestId('edit-field-amount')).not.toBeInTheDocument()
    expect(screen.getByTestId('verify-field-amount')).toBeInTheDocument()
  })

  it('shows OCR text when toggled', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('ocr-text-card')).toBeInTheDocument()
    })

    // OCR text should be hidden initially
    expect(screen.queryByTestId('ocr-text-content')).not.toBeInTheDocument()

    // Click toggle button
    const toggleButton = screen.getByTestId('toggle-ocr-text')
    await user.click(toggleButton)

    // OCR text should now be visible
    expect(screen.getByTestId('ocr-text-content')).toBeInTheDocument()
    expect(screen.getByText(mockDocument.ocr_text)).toBeInTheDocument()
  })

  it('displays processing logs', async () => {
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('processing-logs-card')).toBeInTheDocument()
    })

    expect(screen.getByTestId('processing-timeline')).toBeInTheDocument()
    expect(screen.getByText('File Upload')).toBeInTheDocument()
    expect(screen.getByText('OCR Processing')).toBeInTheDocument()
    expect(screen.getByText('File uploaded successfully')).toBeInTheDocument()
    expect(screen.getByText('0.50s')).toBeInTheDocument() // Duration
  })

  it('calls onReviewComplete when document is approved', async () => {
    const user = userEvent.setup()
    
    // Mock that verification completes the document
    mockFetch.mockImplementation((url, options) => {
      if (url.includes('/verify/') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            message: 'Extraction verified',
            document_status: 'approved'
          })
        })
      }
      return mockFetch(url)
    })

    renderWithProviders(
      <DocumentReviewInterface 
        documentId={documentId} 
        onReviewComplete={mockOnReviewComplete}
      />
    )

    await waitFor(() => {
      expect(screen.getByTestId('extraction-fields-list')).toBeInTheDocument()
    })

    // Verify a field (this should complete the document)
    const verifyButton = screen.getByTestId('verify-field-amount')
    await user.click(verifyButton)

    await waitFor(() => {
      expect(mockOnReviewComplete).toHaveBeenCalledWith(expect.objectContaining({
        id: documentId
      }))
    })
  })

  it('handles API errors gracefully', async () => {
    // Mock API error
    mockFetch.mockRejectedValueOnce(new Error('API Error'))

    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('document-review-error')).toBeInTheDocument()
    })

    expect(screen.getByText(/error: api error/i)).toBeInTheDocument()
  })

  it('shows no extractions message when no fields extracted', async () => {
    // Mock empty extractions
    mockFetch.mockImplementation((url) => {
      if (url.includes('/extractions/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve([])
        })
      }
      return mockFetch(url)
    })

    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('no-extractions-alert')).toBeInTheDocument()
    })

    expect(screen.getByText(/no data fields were extracted/i)).toBeInTheDocument()
  })

  it('shows document not found when document ID is invalid', async () => {
    // Mock 404 response
    mockFetch.mockImplementation((url) => {
      if (url.includes('/api/documents/')) {
        return Promise.resolve({
          ok: false,
          status: 404
        })
      }
      return mockFetch(url)
    })

    renderWithProviders(<DocumentReviewInterface documentId="invalid-id" />)

    await waitFor(() => {
      expect(screen.getByTestId('document-review-error')).toBeInTheDocument()
    })
  })

  it('shows verified badge for verified extractions', async () => {
    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('extraction-fields-list')).toBeInTheDocument()
    })

    // Vendor name extraction should show as verified
    const vendorField = screen.getByTestId('extraction-field-vendor_name')
    expect(vendorField).toContainHTML('Verified')
    
    // Amount field should show verify/edit buttons (not verified)
    const amountField = screen.getByTestId('extraction-field-amount')
    expect(screen.getByTestId('verify-field-amount')).toBeInTheDocument()
    expect(screen.getByTestId('edit-field-amount')).toBeInTheDocument()
  })

  it('shows corrected values when field has been corrected', async () => {
    // Mock extraction with correction
    const correctedExtractions = [
      {
        ...mockExtractions[0],
        corrected_value: '$1,500.00',
        correction_reason: 'OCR error fixed',
        is_verified: true
      }
    ]

    mockFetch.mockImplementation((url) => {
      if (url.includes('/extractions/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(correctedExtractions)
        })
      }
      return mockFetch(url)
    })

    renderWithProviders(<DocumentReviewInterface documentId={documentId} />)

    await waitFor(() => {
      expect(screen.getByTestId('extraction-fields-list')).toBeInTheDocument()
    })

    // Should show corrected value
    expect(screen.getByText('$1,500.00')).toBeInTheDocument()
    // Should show original value
    expect(screen.getByText(/original: \$1,234\.56/i)).toBeInTheDocument()
    // Should show correction reason
    expect(screen.getByText(/correction: ocr error fixed/i)).toBeInTheDocument()
  })
})