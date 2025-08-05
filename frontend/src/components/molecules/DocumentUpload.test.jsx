import { describe, it, expect, vi, beforeEach } from 'vitest'
import { screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders, createMockFile, createMockDragEvent, createMockFileList } from '../../test/utils'
import DocumentUpload from './DocumentUpload'

// Mock the global fetch for file uploads
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('DocumentUpload', () => {
  const mockOnUploadComplete = vi.fn()
  const mockOnUploadError = vi.fn()

  const defaultProps = {
    onUploadComplete: mockOnUploadComplete,
    onUploadError: mockOnUploadError,
    maxFiles: 5,
    batchMode: true
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        document: {
          id: 'test-id',
          original_filename: 'test.pdf',
          status: 'uploaded'
        },
        message: 'Document uploaded successfully'
      })
    })
  })

  it('renders upload area with correct elements', () => {
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    expect(screen.getByTestId('document-upload-zone')).toBeInTheDocument()
    expect(screen.getByText(/drag and drop files here/i)).toBeInTheDocument()
    expect(screen.getByText(/or click to browse/i)).toBeInTheDocument()
    expect(screen.getByText(/supported formats/i)).toBeInTheDocument()
  })

  it('handles file selection via input', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const file = createMockFile('test.pdf', 'application/pdf')

    await user.upload(fileInput, file)

    expect(screen.getByText('test.pdf')).toBeInTheDocument()
    expect(screen.getByTestId('file-preview-test.pdf')).toBeInTheDocument()
  })

  it('handles multiple file selection', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const files = [
      createMockFile('file1.pdf', 'application/pdf'),
      createMockFile('file2.png', 'image/png'),
      createMockFile('file3.jpg', 'image/jpeg')
    ]

    await user.upload(fileInput, files)

    expect(screen.getByText('file1.pdf')).toBeInTheDocument()
    expect(screen.getByText('file2.png')).toBeInTheDocument()
    expect(screen.getByText('file3.jpg')).toBeInTheDocument()
  })

  it('enforces maximum file limit', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} maxFiles={2} />)

    const fileInput = screen.getByTestId('file-input')
    const files = [
      createMockFile('file1.pdf'),
      createMockFile('file2.pdf'), 
      createMockFile('file3.pdf') // This should be rejected
    ]

    await user.upload(fileInput, files)

    expect(screen.getByText('file1.pdf')).toBeInTheDocument()
    expect(screen.getByText('file2.pdf')).toBeInTheDocument()
    expect(screen.queryByText('file3.pdf')).not.toBeInTheDocument()
    
    // Should show error message
    expect(screen.getByText(/maximum 2 files allowed/i)).toBeInTheDocument()
  })

  it('validates file types', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const invalidFile = createMockFile('test.txt', 'text/plain')

    await user.upload(fileInput, invalidFile)

    expect(screen.getByText(/file type not supported/i)).toBeInTheDocument()
    expect(screen.queryByText('test.txt')).not.toBeInTheDocument()
  })

  it('validates file size', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const largeFile = createMockFile('large.pdf', 'application/pdf', 60 * 1024 * 1024) // 60MB

    await user.upload(fileInput, largeFile)

    expect(screen.getByText(/file size exceeds limit/i)).toBeInTheDocument()
    expect(screen.queryByText('large.pdf')).not.toBeInTheDocument()
  })

  it('handles drag and drop', async () => {
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const dropZone = screen.getByTestId('document-upload-zone')
    const file = createMockFile('dropped.pdf', 'application/pdf')

    // Simulate drag enter
    const dragEnterEvent = createMockDragEvent('dragenter', [file])
    fireEvent(dropZone, dragEnterEvent)

    expect(dropZone).toHaveClass('drag-over')

    // Simulate drop
    const dropEvent = createMockDragEvent('drop', [file])
    fireEvent(dropZone, dropEvent)

    await waitFor(() => {
      expect(screen.getByText('dropped.pdf')).toBeInTheDocument()
    })

    expect(dropZone).not.toHaveClass('drag-over')
  })

  it('prevents default drag behaviors', () => {
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const dropZone = screen.getByTestId('document-upload-zone')
    const file = createMockFile('test.pdf')

    const dragOverEvent = createMockDragEvent('dragover', [file])
    const preventDefaultSpy = vi.spyOn(dragOverEvent, 'preventDefault')

    fireEvent(dropZone, dragOverEvent)

    expect(preventDefaultSpy).toHaveBeenCalled()
  })

  it('removes files when remove button is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const file = createMockFile('test.pdf', 'application/pdf')

    await user.upload(fileInput, file)

    expect(screen.getByText('test.pdf')).toBeInTheDocument()

    const removeButton = screen.getByTestId('remove-file-test.pdf')
    await user.click(removeButton)

    expect(screen.queryByText('test.pdf')).not.toBeInTheDocument()
  })

  it('clears all files when clear all button is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const files = [
      createMockFile('file1.pdf'),
      createMockFile('file2.pdf')
    ]

    await user.upload(fileInput, files)

    expect(screen.getByText('file1.pdf')).toBeInTheDocument()
    expect(screen.getByText('file2.pdf')).toBeInTheDocument()

    const clearButton = screen.getByTestId('clear-all-files')
    await user.click(clearButton)

    expect(screen.queryByText('file1.pdf')).not.toBeInTheDocument()
    expect(screen.queryByText('file2.pdf')).not.toBeInTheDocument()
  })

  it('uploads files when upload button is clicked', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    // Add files
    const fileInput = screen.getByTestId('file-input')
    const file = createMockFile('test.pdf', 'application/pdf')
    await user.upload(fileInput, file)

    // Click upload button
    const uploadButton = screen.getByTestId('upload-files-btn')
    await user.click(uploadButton)

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith('/api/upload/', expect.objectContaining({
        method: 'POST',
        body: expect.any(FormData)
      }))
    })

    expect(mockOnUploadComplete).toHaveBeenCalledWith([file])
  })

  it('shows upload progress during upload', async () => {
    const user = userEvent.setup()
    
    // Mock fetch to simulate slow upload
    mockFetch.mockImplementation(() => 
      new Promise(resolve => 
        setTimeout(() => resolve({
          ok: true,
          json: () => Promise.resolve({
            document: { id: 'test-id', original_filename: 'test.pdf' },
            message: 'Upload successful'
          })
        }), 100)
      )
    )

    renderWithProviders(<DocumentUpload {...defaultProps} />)

    // Add file and start upload
    const fileInput = screen.getByTestId('file-input')
    const file = createMockFile('test.pdf')
    await user.upload(fileInput, file)

    const uploadButton = screen.getByTestId('upload-files-btn')
    await user.click(uploadButton)

    // Should show progress indicator
    expect(screen.getByTestId('upload-progress')).toBeInTheDocument()
    expect(screen.getByText(/uploading/i)).toBeInTheDocument()

    // Wait for upload to complete
    await waitFor(() => {
      expect(screen.queryByTestId('upload-progress')).not.toBeInTheDocument()
    }, { timeout: 200 })
  })

  it('handles upload errors', async () => {
    const user = userEvent.setup()
    
    // Mock failed upload
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: () => Promise.resolve({
        error: 'Upload failed',
        details: ['File too large']
      })
    })

    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const file = createMockFile('test.pdf')
    await user.upload(fileInput, file)

    const uploadButton = screen.getByTestId('upload-files-btn')
    await user.click(uploadButton)

    await waitFor(() => {
      expect(screen.getByText(/upload failed/i)).toBeInTheDocument()
    })

    expect(mockOnUploadError).toHaveBeenCalledWith(expect.objectContaining({
      message: expect.stringContaining('Upload failed')
    }))
  })

  it('disables upload button when no files selected', () => {
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const uploadButton = screen.getByTestId('upload-files-btn')
    expect(uploadButton).toBeDisabled()
  })

  it('enables upload button when files are selected', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const file = createMockFile('test.pdf')
    await user.upload(fileInput, file)

    const uploadButton = screen.getByTestId('upload-files-btn')
    expect(uploadButton).not.toBeDisabled()
  })

  it('shows file preview information', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const file = createMockFile('test.pdf', 'application/pdf', 2048576) // 2MB
    await user.upload(fileInput, file)

    const preview = screen.getByTestId('file-preview-test.pdf')
    expect(preview).toBeInTheDocument()
    expect(screen.getByText('test.pdf')).toBeInTheDocument()
    expect(screen.getByText(/2\.\d+ MB/)).toBeInTheDocument() // File size
    expect(screen.getByText('PDF')).toBeInTheDocument() // File type
  })

  it('handles paste events for file upload', async () => {
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const dropZone = screen.getByTestId('document-upload-zone')
    const file = createMockFile('pasted.png', 'image/png')

    // Create paste event
    const pasteEvent = new Event('paste', { bubbles: true })
    Object.defineProperty(pasteEvent, 'clipboardData', {
      value: {
        files: createMockFileList([file]),
        items: [{
          kind: 'file',
          type: 'image/png',
          getAsFile: () => file
        }]
      }
    })

    fireEvent(dropZone, pasteEvent)

    await waitFor(() => {
      expect(screen.getByText('pasted.png')).toBeInTheDocument()
    })
  })

  it('respects single file mode when not in batch mode', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} batchMode={false} />)

    const fileInput = screen.getByTestId('file-input')
    const files = [
      createMockFile('file1.pdf'),
      createMockFile('file2.pdf')
    ]

    await user.upload(fileInput, files)

    // Should only show the first file
    expect(screen.getByText('file1.pdf')).toBeInTheDocument()
    expect(screen.queryByText('file2.pdf')).not.toBeInTheDocument()
  })

  it('displays upload tips when no files are selected', () => {
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    expect(screen.getByText(/drag and drop files here/i)).toBeInTheDocument()
    expect(screen.getByText(/maximum file size: 50mb/i)).toBeInTheDocument()
    expect(screen.getByText(/supported formats/i)).toBeInTheDocument()
  })

  it('hides upload tips when files are selected', async () => {
    const user = userEvent.setup()
    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const file = createMockFile('test.pdf')
    await user.upload(fileInput, file)

    expect(screen.queryByText(/drag and drop files here/i)).toBeInTheDocument()
    // Tips should still be visible but files should be shown too
    expect(screen.getByText('test.pdf')).toBeInTheDocument()
  })

  it('handles network errors during upload', async () => {
    const user = userEvent.setup()
    
    // Mock network error
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    renderWithProviders(<DocumentUpload {...defaultProps} />)

    const fileInput = screen.getByTestId('file-input')
    const file = createMockFile('test.pdf')
    await user.upload(fileInput, file)

    const uploadButton = screen.getByTestId('upload-files-btn')
    await user.click(uploadButton)

    await waitFor(() => {
      expect(screen.getByText(/upload failed/i)).toBeInTheDocument()
    })

    expect(mockOnUploadError).toHaveBeenCalled()
  })
})