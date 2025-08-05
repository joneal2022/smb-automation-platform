import { test, expect } from '@playwright/test'
import path from 'path'

test.describe('Document Upload Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Mock authentication
    await page.route('**/api/auth/login/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access: 'mock-access-token',
          refresh: 'mock-refresh-token',
          user: {
            id: 1,
            email: 'test@example.com',
            first_name: 'Test',
            last_name: 'User',
            organization: { id: 1, name: 'Test Org' }
          }
        })
      })
    })

    // Mock document stats
    await page.route('**/api/stats/', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          total_documents: 5,
          processing_summary: {
            pending: 2,
            processing: 1,
            completed: 2,
            review_required: 0,
            errors: 0
          },
          recent_activity: []
        })
      })
    })

    // Mock document upload
    await page.route('**/api/upload/', async route => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          document: {
            id: 'test-doc-id',
            original_filename: 'test-document.pdf',
            status: 'uploaded',
            created_at: new Date().toISOString()
          },
          message: 'Document uploaded successfully'
        })
      })
    })

    // Navigate to login and authenticate
    await page.goto('/login')
    await page.fill('[data-testid="email-input"]', 'test@example.com')
    await page.fill('[data-testid="password-input"]', 'password123')
    await page.click('[data-testid="login-button"]')
    
    // Wait for redirect to dashboard
    await expect(page).toHaveURL(/.*dashboard/)
  })

  test('should navigate to document processing page', async ({ page }) => {
    // Navigate to document processing
    await page.click('text=Document Processing')
    await expect(page).toHaveURL(/.*documents\/processing/)
    
    // Verify page loaded correctly
    await expect(page.getByTestId('document-processing-page')).toBeVisible()
    await expect(page.getByText('Document Processing')).toBeVisible()
  })

  test('should upload single document via file input', async ({ page }) => {
    await page.goto('/documents/processing')
    
    // Go to upload tab
    await page.click('[data-testid="upload-tab"]')
    
    // Verify upload interface is visible
    await expect(page.getByTestId('document-upload-zone')).toBeVisible()
    
    // Create a test file path
    const testFilePath = path.join(process.cwd(), '../../example/docs/invoice.png')
    
    // Upload file
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(testFilePath)
    
    // Verify file appears in preview
    await expect(page.getByText('invoice.png')).toBeVisible()
    
    // Click upload button
    await page.click('[data-testid="upload-files-btn"]')
    
    // Verify success message
    await expect(page.getByTestId('upload-success-alert')).toBeVisible()
    await expect(page.getByText('Files uploaded successfully!')).toBeVisible()
  })

  test('should upload multiple documents in batch mode', async ({ page }) => {
    await page.goto('/documents/processing')
    
    // Go to upload tab
    await page.click('[data-testid="upload-tab"]')
    
    // Create multiple test files
    const testFiles = [
      path.join(process.cwd(), '../../example/docs/invoice.png'),
      path.join(process.cwd(), '../../example/docs/rooferi_invoice_1.pdf')
    ]
    
    // Upload multiple files
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(testFiles)
    
    // Verify both files appear
    await expect(page.getByText('invoice.png')).toBeVisible()
    await expect(page.getByText('rooferi_invoice_1.pdf')).toBeVisible()
    
    // Upload files
    await page.click('[data-testid="upload-files-btn"]')
    
    // Verify success
    await expect(page.getByTestId('upload-success-alert')).toBeVisible()
  })

  test('should handle drag and drop upload', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="upload-tab"]')
    
    const uploadZone = page.getByTestId('document-upload-zone')
    
    // Create a data transfer with files
    const testFilePath = path.join(process.cwd(), '../../example/docs/invoice.png')
    
    // Simulate drag enter
    await uploadZone.dispatchEvent('dragenter', {
      dataTransfer: {
        files: [{ name: 'invoice.png', type: 'image/png' }]
      }
    })
    
    // Verify drag over state
    await expect(uploadZone).toHaveClass(/drag-over/)
    
    // Simulate file drop
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(testFilePath)
    
    // Verify file was added
    await expect(page.getByText('invoice.png')).toBeVisible()
  })

  test('should validate file types', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="upload-tab"]')
    
    // Try to upload an invalid file type
    const fileInput = page.getByTestId('file-input')
    
    // Create a temporary text file for testing
    await page.evaluate(() => {
      const file = new File(['test content'], 'test.txt', { type: 'text/plain' })
      const fileInput = document.querySelector('[data-testid="file-input"]')
      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(file)
      fileInput.files = dataTransfer.files
      fileInput.dispatchEvent(new Event('change', { bubbles: true }))
    })
    
    // Should show error message
    await expect(page.getByText(/file type not supported/i)).toBeVisible()
  })

  test('should validate file size limits', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="upload-tab"]')
    
    // Create a large file for testing
    await page.evaluate(() => {
      // Create a 60MB file (exceeds 50MB limit)
      const largeFile = new File(['x'.repeat(60 * 1024 * 1024)], 'large.pdf', { 
        type: 'application/pdf' 
      })
      const fileInput = document.querySelector('[data-testid="file-input"]')
      const dataTransfer = new DataTransfer()
      dataTransfer.items.add(largeFile)
      fileInput.files = dataTransfer.files
      fileInput.dispatchEvent(new Event('change', { bubbles: true }))
    })
    
    // Should show error message
    await expect(page.getByText(/file size exceeds limit/i)).toBeVisible()
  })

  test('should remove files from upload queue', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="upload-tab"]')
    
    const testFilePath = path.join(process.cwd(), '../../example/docs/invoice.png')
    
    // Upload file
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(testFilePath)
    
    // Verify file is visible
    await expect(page.getByText('invoice.png')).toBeVisible()
    
    // Remove file
    await page.click('[data-testid="remove-file-invoice.png"]')
    
    // Verify file is removed
    await expect(page.getByText('invoice.png')).not.toBeVisible()
  })

  test('should clear all files', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="upload-tab"]')
    
    // Upload multiple files
    const testFiles = [
      path.join(process.cwd(), '../../example/docs/invoice.png'),
      path.join(process.cwd(), '../../example/docs/rooferi_invoice_1.pdf')
    ]
    
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(testFiles)
    
    // Verify files are visible
    await expect(page.getByText('invoice.png')).toBeVisible()
    await expect(page.getByText('rooferi_invoice_1.pdf')).toBeVisible()
    
    // Clear all files
    await page.click('[data-testid="clear-all-files"]')
    
    // Verify files are removed
    await expect(page.getByText('invoice.png')).not.toBeVisible()
    await expect(page.getByText('rooferi_invoice_1.pdf')).not.toBeVisible()
  })

  test('should show upload progress', async ({ page }) => {
    // Mock slow upload
    await page.route('**/api/upload/', async route => {
      // Delay response to show progress
      await new Promise(resolve => setTimeout(resolve, 1000))
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          document: { id: 'test-id', original_filename: 'test.pdf' },
          message: 'Upload successful'
        })
      })
    })

    await page.goto('/documents/processing')
    await page.click('[data-testid="upload-tab"]')
    
    const testFilePath = path.join(process.cwd(), '../../example/docs/invoice.png')
    
    // Upload file
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(testFilePath)
    
    // Start upload
    await page.click('[data-testid="upload-files-btn"]')
    
    // Should show progress indicator
    await expect(page.getByTestId('upload-progress')).toBeVisible()
    await expect(page.getByText(/uploading/i)).toBeVisible()
    
    // Wait for completion
    await expect(page.getByTestId('upload-progress')).not.toBeVisible({ timeout: 5000 })
  })

  test('should handle upload errors', async ({ page }) => {
    // Mock failed upload
    await page.route('**/api/upload/', async route => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Upload failed',
          details: ['File too large']
        })
      })
    })

    await page.goto('/documents/processing')
    await page.click('[data-testid="upload-tab"]')
    
    const testFilePath = path.join(process.cwd(), '../../example/docs/invoice.png')
    
    // Upload file
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(testFilePath)
    
    // Start upload
    await page.click('[data-testid="upload-files-btn"]')
    
    // Should show error message
    await expect(page.getByText(/upload failed/i)).toBeVisible()
  })

  test('should disable upload button when no files selected', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="upload-tab"]')
    
    // Upload button should be disabled initially
    const uploadButton = page.getByTestId('upload-files-btn')
    await expect(uploadButton).toBeDisabled()
  })

  test('should enable upload button when files are selected', async ({ page }) => {
    await page.goto('/documents/processing')
    await page.click('[data-testid="upload-tab"]')
    
    const testFilePath = path.join(process.cwd(), '../../example/docs/invoice.png')
    
    // Upload file
    const fileInput = page.getByTestId('file-input')
    await fileInput.setInputFiles(testFilePath)
    
    // Upload button should be enabled
    const uploadButton = page.getByTestId('upload-files-btn')
    await expect(uploadButton).not.toBeDisabled()
  })
})