import { test, expect } from '@playwright/test'

test.describe('Batch Processing Flow', () => {
  const mockBatches = [
    {
      id: 'batch-1',
      name: 'Invoice Processing Batch #1',
      description: 'Monthly invoice processing',
      status: 'completed',
      total_documents: 10,
      processed_documents: 10,
      successful_documents: 9,
      failed_documents: 1,
      completion_percentage: 100,
      success_rate: 90,
      created_at: '2025-08-01T08:00:00Z'
    },
    {
      id: 'batch-2',
      name: 'Contract Review Batch #2',
      description: 'Quarterly contract review',
      status: 'processing',
      total_documents: 5,
      processed_documents: 3,
      successful_documents: 3,
      failed_documents: 0,
      completion_percentage: 60,
      success_rate: 100,
      created_at: '2025-08-01T09:00:00Z'
    },
    {
      id: 'batch-3',
      name: 'Receipt Batch #3',
      description: 'Weekly receipt processing',
      status: 'created',
      total_documents: 8,
      processed_documents: 0,
      successful_documents: 0,
      failed_documents: 0,
      completion_percentage: 0,
      success_rate: 0,
      created_at: '2025-08-01T10:00:00Z'
    }
  ]

  const mockDocuments = [
    {
      id: 'doc-1',
      original_filename: 'invoice_001.pdf',
      status: 'uploaded',
      file_size_mb: 2.1,
      document_type_name: 'Invoice',
      created_at: '2025-08-01T10:30:00Z'
    },
    {
      id: 'doc-2',
      original_filename: 'invoice_002.pdf',
      status: 'uploaded',
      file_size_mb: 1.8,
      document_type_name: 'Invoice',
      created_at: '2025-08-01T10:35:00Z'
    },
    {
      id: 'doc-3',
      original_filename: 'contract_001.pdf',
      status: 'uploaded',
      file_size_mb: 3.2,
      document_type_name: 'Contract',
      created_at: '2025-08-01T10:40:00Z'
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

    // Mock batches API
    await page.route('**/api/batches/', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ results: mockBatches })
        })
      } else if (route.request().method() === 'POST') {
        const postData = await route.request().postDataJSON()
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'new-batch-id',
            ...postData,
            status: 'created',
            created_at: new Date().toISOString()
          })
        })
      }
    })

    // Mock uploaded documents API
    await page.route('**/api/documents/?status=uploaded', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ results: mockDocuments })
      })
    })

    // Mock batch items API
    await page.route('**/api/batch-items/', async route => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: 'item-id', message: 'Item created' })
      })
    })

    // Mock batch processing start
    await page.route('**/api/batches/*/start_processing/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Batch processing completed',
          status: 'completed',
          successful: 7,
          failed: 1
        })
      })
    })

    // Mock batch deletion
    await page.route('**/api/batches/*/DELETE', async route => {
      await route.fulfill({ status: 204 })
    })

    // Login
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
  })

  test('should display batch processing interface', async ({ page }) => {
    await page.goto('/documents/processing')
    
    // Navigate to batch tab
    await page.click('[data-testid="batch-tab"]')
    
    // Verify interface loaded
    await expect(page.getByTestId('batch-processing-interface')).toBeVisible()
    await expect(page.getByText('Batch Processing')).toBeVisible()
    await expect(page.getByText(/process multiple documents together/i)).toBeVisible()
    await expect(page.getByTestId('create-batch-btn')).toBeVisible()
  })

  test('should display existing batches in table', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    
    // Wait for batches to load
    await expect(page.getByTestId('batches-table')).toBeVisible()
    
    // Check all batches are displayed
    await expect(page.getByTestId('batch-row-batch-1')).toBeVisible()
    await expect(page.getByTestId('batch-row-batch-2')).toBeVisible()
    await expect(page.getByTestId('batch-row-batch-3')).toBeVisible()
    
    // Verify batch information
    await expect(page.getByText('Invoice Processing Batch #1')).toBeVisible()
    await expect(page.getByText('Contract Review Batch #2')).toBeVisible()
    await expect(page.getByText('Receipt Batch #3')).toBeVisible()
    
    // Check progress and success rates
    await expect(page.getByText('100%')).toBeVisible() // Progress for batch 1
    await expect(page.getByText('90%')).toBeVisible()  // Success rate for batch 1
    await expect(page.getByText('60%')).toBeVisible()  // Progress for batch 2
  })

  test('should open create batch modal', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    
    // Click create batch button
    await page.click('[data-testid="create-batch-btn"]')
    
    // Verify modal opened
    await expect(page.getByTestId('create-batch-modal')).toBeVisible()
    await expect(page.getByText('Create New Batch')).toBeVisible()
    
    // Verify form fields are present
    await expect(page.getByTestId('batch-name-input')).toBeVisible()
    await expect(page.getByTestId('batch-description-input')).toBeVisible()
    await expect(page.getByTestId('auto-approve-threshold')).toBeVisible()
    await expect(page.getByTestId('document-selection-list')).toBeVisible()
  })

  test('should display available documents for selection', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await page.click('[data-testid="create-batch-btn"]')
    
    // Wait for modal and documents to load
    await expect(page.getByTestId('document-selection-list')).toBeVisible()
    
    // Check documents are listed
    await expect(page.getByTestId('document-item-doc-1')).toBeVisible()
    await expect(page.getByTestId('document-item-doc-2')).toBeVisible()
    await expect(page.getByTestId('document-item-doc-3')).toBeVisible()
    
    // Verify document information
    await expect(page.getByText('invoice_001.pdf')).toBeVisible()
    await expect(page.getByText('invoice_002.pdf')).toBeVisible()
    await expect(page.getByText('contract_001.pdf')).toBeVisible()
    
    // Check file sizes and types
    await expect(page.getByText('2.1 MB')).toBeVisible()
    await expect(page.getByText('Invoice')).toBeVisible()
    await expect(page.getByText('Contract')).toBeVisible()
  })

  test('should create new batch successfully', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await page.click('[data-testid="create-batch-btn"]')
    
    // Fill batch details
    await page.fill('[data-testid="batch-name-input"]', 'Test Batch')
    await page.fill('[data-testid="batch-description-input"]', 'Test batch for automation')
    
    // Adjust auto-approve threshold
    await page.fill('[data-testid="auto-approve-threshold"]', '0.9')
    
    // Select documents
    await page.check('[data-testid="document-checkbox-doc-1"]')
    await page.check('[data-testid="document-checkbox-doc-2"]')
    
    // Verify submit button shows selected count
    await expect(page.getByTestId('create-batch-submit')).toContainText('2 documents')
    
    // Create batch
    await page.click('[data-testid="create-batch-submit"]')
    
    // Modal should close
    await expect(page.getByTestId('create-batch-modal')).not.toBeVisible()
    
    // Should refresh batches list (new batch should appear)
    await expect(page.getByTestId('batches-table')).toBeVisible()
  })

  test('should validate batch creation form', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await page.click('[data-testid="create-batch-btn"]')
    
    // Submit button should be disabled initially
    await expect(page.getByTestId('create-batch-submit')).toBeDisabled()
    
    // Add name but no documents
    await page.fill('[data-testid="batch-name-input"]', 'Test Batch')
    await expect(page.getByTestId('create-batch-submit')).toBeDisabled()
    
    // Add documents but clear name
    await page.check('[data-testid="document-checkbox-doc-1"]')
    await page.fill('[data-testid="batch-name-input"]', '')
    await expect(page.getByTestId('create-batch-submit')).toBeDisabled()
    
    // Add both name and documents
    await page.fill('[data-testid="batch-name-input"]', 'Test Batch')
    await expect(page.getByTestId('create-batch-submit')).not.toBeDisabled()
  })

  test('should start batch processing', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    
    // Wait for batches to load
    await expect(page.getByTestId('batches-table')).toBeVisible()
    
    // Start processing for created batch
    await page.click('[data-testid="start-batch-batch-3"]')
    
    // Should show completion message or redirect
    await expect(page.getByText(/batch processing completed/i)).toBeVisible()
  })

  test('should delete batch with confirmation', async ({ page }) => {
    // Mock confirmation dialog
    page.on('dialog', async dialog => {
      expect(dialog.message()).toContain('Are you sure you want to delete this batch?')
      await dialog.accept()
    })
    
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await expect(page.getByTestId('batches-table')).toBeVisible()
    
    // Delete batch
    await page.click('[data-testid="delete-batch-batch-1"]')
    
    // Confirmation dialog should have been handled by the event listener
  })

  test('should cancel batch deletion', async ({ page }) => {
    // Mock confirmation dialog - user cancels
    page.on('dialog', async dialog => {
      await dialog.dismiss()
    })
    
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await expect(page.getByTestId('batches-table')).toBeVisible()
    
    // Attempt to delete batch
    await page.click('[data-testid="delete-batch-batch-1"]')
    
    // Batch should still be visible (deletion was cancelled)
    await expect(page.getByTestId('batch-row-batch-1')).toBeVisible()
  })

  test('should show appropriate action buttons based on status', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await expect(page.getByTestId('batches-table')).toBeVisible()
    
    // Completed batch should only have delete button
    await expect(page.getByTestId('delete-batch-batch-1')).toBeVisible()
    await expect(page.queryByTestId('start-batch-batch-1')).not.toBeVisible()
    
    // Processing batch should only have delete button
    await expect(page.getByTestId('delete-batch-batch-2')).toBeVisible()
    await expect(page.queryByTestId('start-batch-batch-2')).not.toBeVisible()
    
    // Created batch should have both start and delete buttons
    await expect(page.getByTestId('start-batch-batch-3')).toBeVisible()
    await expect(page.getByTestId('delete-batch-batch-3')).toBeVisible()
  })

  test('should show no batches message when empty', async ({ page }) => {
    // Mock empty batches response
    await page.route('**/api/batches/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ results: [] })
      })
    })
    
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    
    await expect(page.getByTestId('no-batches-alert')).toBeVisible()
    await expect(page.getByText(/no batches created yet/i)).toBeVisible()
  })

  test('should show no documents message when no uploaded documents', async ({ page }) => {
    // Mock empty documents response
    await page.route('**/api/documents/?status=uploaded', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ results: [] })
      })
    })
    
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await page.click('[data-testid="create-batch-btn"]')
    
    await expect(page.getByText(/no uploaded documents available/i)).toBeVisible()
  })

  test('should update auto-approve threshold display', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await page.click('[data-testid="create-batch-btn"]')
    
    const slider = page.getByTestId('auto-approve-threshold')
    
    // Change threshold to 85%
    await slider.fill('0.85')
    
    // Should update display text
    await expect(page.getByText(/documents with confidence above 85% will be auto-approved/i)).toBeVisible()
  })

  test('should show processing indicator during batch start', async ({ page }) => {
    // Mock slow batch processing
    await page.route('**/api/batches/batch-3/start_processing/', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'Batch processing completed',
          status: 'completed'
        })
      })
    })
    
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await expect(page.getByTestId('batches-table')).toBeVisible()
    
    const startButton = page.getByTestId('start-batch-batch-3')
    await startButton.click()
    
    // Should show spinner
    await expect(startButton.locator('svg')).toBeVisible() // Spinner icon
    
    // Wait for completion
    await expect(startButton.locator('svg')).not.toBeVisible({ timeout: 2000 })
  })

  test('should handle selected document count updates', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="batch-tab"]')
    await page.click('[data-testid="create-batch-btn"]')
    
    const submitButton = page.getByTestId('create-batch-submit')
    
    // Initially no documents selected
    await expect(submitButton).toContainText('0 documents')
    
    // Select one document
    await page.check('[data-testid="document-checkbox-doc-1"]')
    await expect(submitButton).toContainText('1 documents')
    
    // Select another document
    await page.check('[data-testid="document-checkbox-doc-2"]')
    await expect(submitButton).toContainText('2 documents')
    
    // Unselect one document
    await page.uncheck('[data-testid="document-checkbox-doc-1"]')
    await expect(submitButton).toContainText('1 documents')
  })
})