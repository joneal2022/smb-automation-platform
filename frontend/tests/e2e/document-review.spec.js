import { test, expect } from '@playwright/test'

test.describe('Document Review Flow', () => {
  const mockDocument = {
    id: 'test-doc-123',
    original_filename: 'invoice_test.pdf',
    status: 'review_required',
    ocr_confidence: 0.72,
    ocr_text: 'INVOICE #12345\nDate: 2025-08-01\nAmount: $1,234.56\nVendor: Test Company Inc.',
    file_size_mb: 2.4,
    document_type_name: 'Invoice',
    created_at: '2025-08-01T10:30:00Z',
    unverified_extractions_count: 2
  }

  const mockExtractions = [
    {
      id: 'ext-1',
      field_name: 'invoice_number',
      field_value: '#12345',
      field_type: 'text',
      confidence: 0.95,
      is_verified: false,
      original_value: '#12345'
    },
    {
      id: 'ext-2',
      field_name: 'amount',
      field_value: '$1,234.56',
      field_type: 'currency',
      confidence: 0.88,
      is_verified: false,
      original_value: '$1,234.56'
    },
    {
      id: 'ext-3',
      field_name: 'date',
      field_value: '2025-08-01',
      field_type: 'date',
      confidence: 0.65,
      is_verified: false,
      original_value: '2025-08-01'
    }
  ]

  const mockProcessingLogs = [
    {
      id: 'log-1',
      step: 'upload',
      step_display: 'File Upload',
      status: 'completed',
      status_display: 'Completed',
      message: 'File uploaded successfully',
      created_at: '2025-08-01T10:30:00Z',
      duration_seconds: 0.5
    },
    {
      id: 'log-2',
      step: 'ocr',
      step_display: 'OCR Processing',
      status: 'completed',
      status_display: 'Completed',
      message: 'OCR processing completed with 72% confidence',
      created_at: '2025-08-01T10:31:00Z',
      duration_seconds: 2.8
    }
  ]

  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.route('**/api/auth/login/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access: 'mock-access-token',
          user: {
            id: 1,
            email: 'test@example.com',
            first_name: 'Test',
            last_name: 'User'
          }
        })
      })
    })

    // Mock document details API
    await page.route(`**/api/documents/${mockDocument.id}/`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockDocument)
      })
    })

    // Mock extractions API
    await page.route(`**/api/documents/${mockDocument.id}/extractions/`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockExtractions)
      })
    })

    // Mock processing logs API
    await page.route(`**/api/documents/${mockDocument.id}/processing_logs/`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(mockProcessingLogs)
      })
    })

    // Login
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
  })

  test('should load document review interface', async ({ page }) => {
    await page.goto(`/documents/review/${mockDocument.id}`)
    
    // Wait for document to load
    await expect(page.getByTestId('document-review-interface')).toBeVisible()
    
    // Verify document header information
    await expect(page.getByText('invoice_test.pdf')).toBeVisible()
    await expect(page.getByText('2.4 MB')).toBeVisible()
    await expect(page.getByText('Invoice')).toBeVisible()
    
    // Verify review progress
    await expect(page.getByTestId('review-progress-card')).toBeVisible()
    await expect(page.getByText(/0 of 3 fields verified/)).toBeVisible()
  })

  test('should display extracted fields with confidence scores', async ({ page }) => {
    await page.goto(`/documents/review/${mockDocument.id}`)
    
    await expect(page.getByTestId('extraction-fields-list')).toBeVisible()
    
    // Check all extracted fields are displayed
    await expect(page.getByTestId('extraction-field-invoice_number')).toBeVisible()
    await expect(page.getByTestId('extraction-field-amount')).toBeVisible()
    await expect(page.getByTestId('extraction-field-date')).toBeVisible()
    
    // Verify field values
    await expect(page.getByText('#12345')).toBeVisible()
    await expect(page.getByText('$1,234.56')).toBeVisible()
    await expect(page.getByText('2025-08-01')).toBeVisible()
    
    // Verify confidence scores are displayed
    await expect(page.getByText('95.0%')).toBeVisible() // Invoice number
    await expect(page.getByText('88.0%')).toBeVisible() // Amount
    await expect(page.getByText('65.0%')).toBeVisible() // Date (low confidence)
  })

  test('should verify a field successfully', async ({ page }) => {
    // Mock successful verification
    await page.route('**/api/extractions/ext-1/verify/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Extraction verified',
          document_status: 'review_required'
        })
      })
    })

    await page.goto(`/documents/review/${mockDocument.id}`)
    
    // Wait for fields to load
    await expect(page.getByTestId('extraction-fields-list')).toBeVisible()
    
    // Verify the invoice number field
    await page.click('[data-testid="verify-field-invoice_number"]')
    
    // Should show success indicator (field becomes verified)
    await expect(page.getByText('Verified')).toBeVisible()
    
    // Progress should update
    await expect(page.getByText(/1 of 3 fields verified/)).toBeVisible()
  })

  test('should edit and correct a field', async ({ page }) => {
    // Mock successful correction
    await page.route('**/api/extractions/ext-2/verify/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Extraction verified',
          document_status: 'review_required'
        })
      })
    })

    await page.goto(`/documents/review/${mockDocument.id}`)
    await expect(page.getByTestId('extraction-fields-list')).toBeVisible()
    
    // Start editing the amount field
    await page.click('[data-testid="edit-field-amount"]')
    
    // Should show edit form
    await expect(page.getByTestId('edit-field-amount')).toBeVisible()
    await expect(page.getByTestId('correction-reason-amount')).toBeVisible()
    
    // Clear and enter corrected value
    await page.fill('[data-testid="edit-field-amount"]', '$1,500.00')
    await page.fill('[data-testid="correction-reason-amount"]', 'OCR misread the decimal places')
    
    // Save changes
    await page.click('[data-testid="save-edit-amount"]')
    
    // Should show corrected value
    await expect(page.getByText('$1,500.00')).toBeVisible()
    await expect(page.getByText(/original: \$1,234\.56/i)).toBeVisible()
    await expect(page.getByText(/correction: ocr misread the decimal places/i)).toBeVisible()
  })

  test('should cancel field editing', async ({ page }) => {
    await page.goto(`/documents/review/${mockDocument.id}`)
    await expect(page.getByTestId('extraction-fields-list')).toBeVisible()
    
    // Start editing
    await page.click('[data-testid="edit-field-amount"]')
    
    // Enter some changes
    await page.fill('[data-testid="edit-field-amount"]', '$999.99')
    
    // Cancel editing
    await page.click('[data-testid="cancel-edit-amount"]')
    
    // Should return to original value
    await expect(page.getByText('$1,234.56')).toBeVisible()
    await expect(page.getByText('$999.99')).not.toBeVisible()
    
    // Should show verify/edit buttons again
    await expect(page.getByTestId('verify-field-amount')).toBeVisible()
    await expect(page.getByTestId('edit-field-amount')).toBeVisible()
  })

  test('should toggle OCR text display', async ({ page }) => {
    await page.goto(`/documents/review/${mockDocument.id}`)
    await expect(page.getByTestId('ocr-text-card')).toBeVisible()
    
    // OCR text should be hidden initially
    await expect(page.getByTestId('ocr-text-content')).not.toBeVisible()
    
    // Click show button
    await page.click('[data-testid="toggle-ocr-text"]')
    
    // OCR text should now be visible
    await expect(page.getByTestId('ocr-text-content')).toBeVisible()
    await expect(page.getByText('INVOICE #12345')).toBeVisible()
    await expect(page.getByText('Date: 2025-08-01')).toBeVisible()
    await expect(page.getByText('Amount: $1,234.56')).toBeVisible()
    
    // Click hide button
    await page.click('[data-testid="toggle-ocr-text"]')
    
    // OCR text should be hidden again
    await expect(page.getByTestId('ocr-text-content')).not.toBeVisible()
  })

  test('should display processing history', async ({ page }) => {
    await page.goto(`/documents/review/${mockDocument.id}`)
    
    await expect(page.getByTestId('processing-logs-card')).toBeVisible()
    await expect(page.getByTestId('processing-timeline')).toBeVisible()
    
    // Check processing steps are displayed
    await expect(page.getByText('File Upload')).toBeVisible()
    await expect(page.getByText('OCR Processing')).toBeVisible()
    
    // Check messages and durations
    await expect(page.getByText('File uploaded successfully')).toBeVisible()
    await expect(page.getByText('OCR processing completed with 72% confidence')).toBeVisible()
    await expect(page.getByText('0.50s')).toBeVisible()
    await expect(page.getByText('2.80s')).toBeVisible()
  })

  test('should complete document review when all fields verified', async ({ page }) => {
    // Mock that verification completes the document
    await page.route('**/api/extractions/*/verify/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Extraction verified',
          document_status: 'approved'
        })
      })
    })

    await page.goto(`/documents/review/${mockDocument.id}`)
    await expect(page.getByTestId('extraction-fields-list')).toBeVisible()
    
    // Verify all fields
    await page.click('[data-testid="verify-field-invoice_number"]')
    await page.click('[data-testid="verify-field-amount"]')
    await page.click('[data-testid="verify-field-date"]')
    
    // Should show completion alert
    await expect(page.getByTestId('review-complete-alert')).toBeVisible()
    await expect(page.getByText(/review complete/i)).toBeVisible()
    await expect(page.getByText(/document has been approved/i)).toBeVisible()
  })

  test('should navigate back to document processing', async ({ page }) => {
    await page.goto(`/documents/review/${mockDocument.id}`)
    
    // Click back button
    await page.click('[data-testid="back-to-processing-btn"]')
    
    // Should navigate to processing page
    await expect(page).toHaveURL(/.*documents.*processing/)
  })

  test('should handle API errors gracefully', async ({ page }) => {
    // Mock API error
    await page.route(`**/api/documents/${mockDocument.id}/`, async route => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Server error' })
      })
    })

    await page.goto(`/documents/review/${mockDocument.id}`)
    
    // Should show error message
    await expect(page.getByTestId('document-review-error')).toBeVisible()
    await expect(page.getByText(/error/i)).toBeVisible()
  })

  test('should show no extractions message when document has no fields', async ({ page }) => {
    // Mock empty extractions
    await page.route(`**/api/documents/${mockDocument.id}/extractions/`, async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([])
      })
    })

    await page.goto(`/documents/review/${mockDocument.id}`)
    
    await expect(page.getByTestId('no-extractions-alert')).toBeVisible()
    await expect(page.getByText(/no data fields were extracted/i)).toBeVisible()
  })

  test('should highlight low confidence fields', async ({ page }) => {
    await page.goto(`/documents/review/${mockDocument.id}`)
    await expect(page.getByTestId('extraction-fields-list')).toBeVisible()
    
    // Date field has 65% confidence (low) - should have warning styling
    const dateField = page.getByTestId('extraction-field-date')
    await expect(dateField).toBeVisible()
    
    // Should contain confidence badge with warning styling
    const confidenceBadge = dateField.locator('text=65.0%')
    await expect(confidenceBadge).toBeVisible()
  })

  test('should preserve field types and formatting', async ({ page }) => {
    await page.goto(`/documents/review/${mockDocument.id}`)
    await expect(page.getByTestId('extraction-fields-list')).toBeVisible()
    
    // Check field types are displayed
    const invoiceField = page.getByTestId('extraction-field-invoice_number')
    await expect(invoiceField).toContainText('Text')
    
    const amountField = page.getByTestId('extraction-field-amount')
    await expect(amountField).toContainText('Currency')
    
    const dateField = page.getByTestId('extraction-field-date')
    await expect(dateField).toContainText('Date')
  })
})