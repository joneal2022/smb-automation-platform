import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockBatch, createMockDocument } from '../../test/utils'
import BatchProcessingInterface from './BatchProcessingInterface'

// Mock fetch for API calls
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('BatchProcessingInterface', () => {
  const mockBatches = [
    createMockBatch({
      id: '1',
      name: 'Invoice Batch #1',
      status: 'completed',
      total_documents: 10,
      processed_documents: 10,
      successful_documents: 9,
      failed_documents: 1,
      completion_percentage: 100,
      success_rate: 90
    }),
    createMockBatch({
      id: '2',
      name: 'Contract Batch #2',
      status: 'processing',
      total_documents: 5,
      processed_documents: 3,
      successful_documents: 3,
      failed_documents: 0,
      completion_percentage: 60,
      success_rate: 100
    }),
    createMockBatch({
      id: '3',
      name: 'Receipt Batch #3',
      status: 'created',
      total_documents: 8,
      processed_documents: 0,
      successful_documents: 0,
      failed_documents: 0,
      completion_percentage: 0,
      success_rate: 0
    })
  ]

  const mockDocuments = [
    createMockDocument({
      id: '1',
      original_filename: 'invoice_001.pdf',
      status: 'uploaded'
    }),
    createMockDocument({
      id: '2',
      original_filename: 'invoice_002.pdf',
      status: 'uploaded'
    }),
    createMockDocument({
      id: '3',
      original_filename: 'contract_001.pdf',
      status: 'uploaded'
    })
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
    mockFetch.mockImplementation((url, options) => {
      if (url.includes('/api/batches/') && !options?.method) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ results: mockBatches })
        })
      }
      if (url.includes('/api/documents/?status=uploaded')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ results: mockDocuments })
        })
      }
      return Promise.reject(new Error('Unhandled API call'))
    })
  })

  it('renders loading state initially', () => {
    renderWithProviders(<BatchProcessingInterface />)
    
    expect(screen.getByTestId('batch-processing-loading')).toBeInTheDocument()
    expect(screen.getByText(/loading batch processing interface/i)).toBeInTheDocument()
  })

  it('renders main interface after loading', async () => {
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('batch-processing-interface')).toBeInTheDocument()
    })

    expect(screen.getByText('Batch Processing')).toBeInTheDocument()
    expect(screen.getByText(/process multiple documents together/i)).toBeInTheDocument()
    expect(screen.getByTestId('create-batch-btn')).toBeInTheDocument()
  })

  it('displays existing batches in table', async () => {
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('batches-table')).toBeInTheDocument()
    })

    // Check all batches are displayed
    expect(screen.getByTestId('batch-row-1')).toBeInTheDocument()
    expect(screen.getByTestId('batch-row-2')).toBeInTheDocument()
    expect(screen.getByTestId('batch-row-3')).toBeInTheDocument()

    // Check batch details
    expect(screen.getByText('Invoice Batch #1')).toBeInTheDocument()
    expect(screen.getByText('Contract Batch #2')).toBeInTheDocument()
    expect(screen.getByText('Receipt Batch #3')).toBeInTheDocument()

    // Check progress and success rates
    expect(screen.getByText('100%')).toBeInTheDocument() // Progress
    expect(screen.getByText('90%')).toBeInTheDocument() // Success rate
  })

  it('shows no batches message when empty', async () => {
    // Mock empty response
    mockFetch.mockImplementation((url) => {
      if (url.includes('/api/batches/')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ results: [] })
        })
      }
      return mockFetch(url)
    })

    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('no-batches-alert')).toBeInTheDocument()
    })

    expect(screen.getByText(/no batches created yet/i)).toBeInTheDocument()
  })

  it('opens create batch modal when create button is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-btn')).toBeInTheDocument()
    })

    const createButton = screen.getByTestId('create-batch-btn')
    await user.click(createButton)

    expect(screen.getByTestId('create-batch-modal')).toBeInTheDocument()
    expect(screen.getByText('Create New Batch')).toBeInTheDocument()
  })

  it('displays available documents in create modal', async () => {
    const user = userEvent.setup()
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-btn')).toBeInTheDocument()
    })

    const createButton = screen.getByTestId('create-batch-btn')
    await user.click(createButton)

    await waitFor(() => {
      expect(screen.getByTestId('document-selection-list')).toBeInTheDocument()
    })

    // Check documents are listed
    expect(screen.getByTestId('document-item-1')).toBeInTheDocument()
    expect(screen.getByTestId('document-item-2')).toBeInTheDocument()
    expect(screen.getByTestId('document-item-3')).toBeInTheDocument()

    expect(screen.getByText('invoice_001.pdf')).toBeInTheDocument()
    expect(screen.getByText('invoice_002.pdf')).toBeInTheDocument()
    expect(screen.getByText('contract_001.pdf')).toBeInTheDocument()
  })

  it('allows selecting documents for batch', async () => {
    const user = userEvent.setup()
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-btn')).toBeInTheDocument()
    })

    const createButton = screen.getByTestId('create-batch-btn')
    await user.click(createButton)

    await waitFor(() => {
      expect(screen.getByTestId('document-selection-list')).toBeInTheDocument()
    })

    // Select first two documents
    const checkbox1 = screen.getByTestId('document-checkbox-1')
    const checkbox2 = screen.getByTestId('document-checkbox-2')

    await user.click(checkbox1)
    await user.click(checkbox2)

    // Check that submit button shows selected count
    expect(screen.getByTestId('create-batch-submit')).toContainHTML('2 documents')
  })

  it('creates batch when form is submitted', async () => {
    const user = userEvent.setup()
    
    // Mock successful batch creation
    mockFetch.mockImplementation((url, options) => {
      if (url.includes('/api/batches/') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            id: 'new-batch-id',
            name: 'Test Batch',
            status: 'created'
          })
        })
      }
      if (url.includes('/api/batch-items/') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ id: 'item-id' })
        })
      }
      return mockFetch(url)
    })

    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-btn')).toBeInTheDocument()
    })

    // Open modal
    const createButton = screen.getByTestId('create-batch-btn')
    await user.click(createButton)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-modal')).toBeInTheDocument()
    })

    // Fill form
    const nameInput = screen.getByTestId('batch-name-input')
    await user.type(nameInput, 'Test Batch')

    const descriptionInput = screen.getByTestId('batch-description-input')
    await user.type(descriptionInput, 'Test batch description')

    // Select documents
    const checkbox1 = screen.getByTestId('document-checkbox-1')
    const checkbox2 = screen.getByTestId('document-checkbox-2')
    await user.click(checkbox1)
    await user.click(checkbox2)

    // Submit form
    const submitButton = screen.getByTestId('create-batch-submit')
    await user.click(submitButton)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/batches/',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: expect.stringContaining('Test Batch')
        })
      )
    })
  })

  it('validates batch creation form', async () => {
    const user = userEvent.setup()
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-btn')).toBeInTheDocument()
    })

    // Open modal
    const createButton = screen.getByTestId('create-batch-btn')
    await user.click(createButton)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-modal')).toBeInTheDocument()
    })

    // Try to submit without name or documents
    const submitButton = screen.getByTestId('create-batch-submit')
    expect(submitButton).toBeDisabled()

    // Add name but no documents
    const nameInput = screen.getByTestId('batch-name-input')
    await user.type(nameInput, 'Test Batch')
    expect(submitButton).toBeDisabled()

    // Add documents but clear name
    const checkbox1 = screen.getByTestId('document-checkbox-1')
    await user.click(checkbox1)
    await user.clear(nameInput)
    expect(submitButton).toBeDisabled()

    // Add both name and documents
    await user.type(nameInput, 'Test Batch')
    expect(submitButton).not.toBeDisabled()
  })

  it('starts batch processing', async () => {
    const user = userEvent.setup()
    
    // Mock successful batch start
    mockFetch.mockImplementation((url, options) => {
      if (url.includes('/start_processing/') && options?.method === 'POST') {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            message: 'Batch processing completed',
            status: 'completed',
            successful: 8,
            failed: 0
          })
        })
      }
      return mockFetch(url)
    })

    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('batches-table')).toBeInTheDocument()
    })

    // Find and click start button for created batch
    const startButton = screen.getByTestId('start-batch-3')
    await user.click(startButton)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/batches/3/start_processing/'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json'
          }),
          body: JSON.stringify({ use_openai: true })
        })
      )
    })
  })

  it('shows processing indicator during batch start', async () => {
    const user = userEvent.setup()
    
    // Mock slow batch start
    mockFetch.mockImplementation((url, options) => {
      if (url.includes('/start_processing/')) {
        return new Promise(resolve => 
          setTimeout(() => resolve({
            ok: true,
            json: () => Promise.resolve({ message: 'Completed' })
          }), 100)
        )
      }
      return mockFetch(url)
    })

    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('batches-table')).toBeInTheDocument()
    })

    const startButton = screen.getByTestId('start-batch-3')
    await user.click(startButton)

    // Should show spinner
    expect(startButton).toContainHTML('spinner')

    await waitFor(() => {
      expect(startButton).not.toContainHTML('spinner')
    }, { timeout: 200 })
  })

  it('deletes batch when delete button is clicked', async () => {
    const user = userEvent.setup()
    
    // Mock confirm dialog
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    
    // Mock successful deletion
    mockFetch.mockImplementation((url, options) => {
      if (options?.method === 'DELETE') {
        return Promise.resolve({ ok: true })
      }
      return mockFetch(url)
    })

    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('batches-table')).toBeInTheDocument()
    })

    const deleteButton = screen.getByTestId('delete-batch-1')
    await user.click(deleteButton)

    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this batch?')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/batches/1/'),
        expect.objectContaining({
          method: 'DELETE'
        })
      )
    })
  })

  it('cancels deletion when user confirms no', async () => {
    const user = userEvent.setup()
    
    // Mock confirm dialog - user says no
    vi.spyOn(window, 'confirm').mockReturnValue(false)

    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('batches-table')).toBeInTheDocument()
    })

    const deleteButton = screen.getByTestId('delete-batch-1')
    await user.click(deleteButton)

    expect(window.confirm).toHaveBeenCalled()
    
    // Should not make DELETE request
    expect(mockFetch).not.toHaveBeenCalledWith(
      expect.stringContaining('/api/batches/1/'),
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('displays progress bars with correct values', async () => {
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('batches-table')).toBeInTheDocument()
    })

    // Check progress bars are rendered
    const progressBars = screen.getAllByRole('progressbar')
    expect(progressBars.length).toBeGreaterThan(0)

    // First batch should be 100% complete
    const completedBatch = screen.getByTestId('batch-row-1')
    expect(completedBatch).toContainHTML('100%')

    // Second batch should be 60% complete
    const processingBatch = screen.getByTestId('batch-row-2')
    expect(processingBatch).toContainHTML('60%')
  })

  it('shows appropriate action buttons based on batch status', async () => {
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('batches-table')).toBeInTheDocument()
    })

    // Completed batch (1) should only have delete button
    expect(screen.queryByTestId('start-batch-1')).not.toBeInTheDocument()
    expect(screen.getByTestId('delete-batch-1')).toBeInTheDocument()

    // Processing batch (2) should only have delete button
    expect(screen.queryByTestId('start-batch-2')).not.toBeInTheDocument()
    expect(screen.getByTestId('delete-batch-2')).toBeInTheDocument()

    // Created batch (3) should have both start and delete buttons
    expect(screen.getByTestId('start-batch-3')).toBeInTheDocument()
    expect(screen.getByTestId('delete-batch-3')).toBeInTheDocument()
  })

  it('updates auto-approve threshold slider', async () => {
    const user = userEvent.setup()
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-btn')).toBeInTheDocument()
    })

    // Open modal
    const createButton = screen.getByTestId('create-batch-btn')
    await user.click(createButton)

    await waitFor(() => {
      expect(screen.getByTestId('auto-approve-threshold')).toBeInTheDocument()
    })

    const slider = screen.getByTestId('auto-approve-threshold')
    
    // Change threshold to 90%
    fireEvent.change(slider, { target: { value: '0.9' } })

    // Should update the display text
    expect(screen.getByText(/documents with confidence above 90% will be auto-approved/i)).toBeInTheDocument()
  })

  it('shows no documents message when no uploaded documents available', async () => {
    // Mock empty documents response
    mockFetch.mockImplementation((url) => {
      if (url.includes('/api/documents/?status=uploaded')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ results: [] })
        })
      }
      return mockFetch(url)
    })

    const user = userEvent.setup()
    renderWithProviders(<BatchProcessingInterface />)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-btn')).toBeInTheDocument()
    })

    // Open modal
    const createButton = screen.getByTestId('create-batch-btn')
    await user.click(createButton)

    await waitFor(() => {
      expect(screen.getByTestId('create-batch-modal')).toBeInTheDocument()
    })

    expect(screen.getByText(/no uploaded documents available/i)).toBeInTheDocument()
  })
})