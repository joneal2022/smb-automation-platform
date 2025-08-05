import React from 'react'
import { render } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from '../services/auth/AuthContext'

// Mock auth context value
const mockAuthContextValue = {
  user: {
    id: 1,
    email: 'test@example.com',
    first_name: 'Test',
    last_name: 'User',
    organization: {
      id: 1,
      name: 'Test Organization'
    }
  },
  isAuthenticated: true,
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  canAccessFeature: vi.fn(() => true)
}

// Custom render function that includes providers
export function renderWithProviders(ui, {
  authValue = mockAuthContextValue,
  route = '/',
  ...renderOptions
} = {}) {
  // Mock the AuthContext
  const MockAuthProvider = ({ children }) => (
    <AuthProvider value={authValue}>
      {children}
    </AuthProvider>
  )

  const Wrapper = ({ children }) => (
    <BrowserRouter>
      <MockAuthProvider>
        {children}
      </MockAuthProvider>
    </BrowserRouter>
  )

  // Set initial route if provided
  if (route !== '/') {
    window.history.pushState({}, 'Test page', route)
  }

  return render(ui, { wrapper: Wrapper, ...renderOptions })
}

// Factory functions for creating test data
export const createMockDocument = (overrides = {}) => ({
  id: '1',
  original_filename: 'test_document.pdf',
  document_type_name: 'Invoice',
  status: 'uploaded',
  created_at: '2025-08-01T10:30:00Z',
  file_size_mb: 2.4,
  extractions_count: 0,
  unverified_extractions_count: 0,
  uploaded_by_name: 'Test User',
  ocr_confidence: null,
  ...overrides
})

export const createMockExtraction = (overrides = {}) => ({
  id: '1',
  field_name: 'amount',
  field_value: '$100.00',
  field_type: 'currency',
  confidence: 0.95,
  is_verified: false,
  original_value: '$100.00',
  document_filename: 'test_document.pdf',
  ...overrides
})

export const createMockBatch = (overrides = {}) => ({
  id: '1',
  name: 'Test Batch',
  status: 'created',
  total_documents: 5,
  processed_documents: 0,
  successful_documents: 0,
  failed_documents: 0,
  completion_percentage: 0,
  success_rate: 0,
  created_at: '2025-08-01T08:00:00Z',
  ...overrides
})

// Mock file creation utilities
export const createMockFile = (name = 'test.pdf', type = 'application/pdf', size = 1024) => {
  const file = new File(['mock file content'], name, { type })
  
  // Add size property (not automatically set in jsdom)
  Object.defineProperty(file, 'size', {
    value: size,
    writable: false
  })
  
  return file
}

export const createMockFileList = (files) => {
  const fileList = {
    length: files.length,
    item: (index) => files[index],
    [Symbol.iterator]: function* () {
      for (let i = 0; i < files.length; i++) {
        yield files[i]
      }
    }
  }
  
  // Add files as indexed properties
  files.forEach((file, index) => {
    fileList[index] = file
  })
  
  return fileList
}

// Authentication test helpers
export const createUnauthenticatedAuthValue = () => ({
  user: null,
  isAuthenticated: false,
  loading: false,
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  canAccessFeature: vi.fn(() => false)
})

export const createLoadingAuthValue = () => ({
  user: null,
  isAuthenticated: false,
  loading: true,
  login: vi.fn(),
  logout: vi.fn(),
  register: vi.fn(),
  canAccessFeature: vi.fn(() => false)
})

// Error testing helpers
export const createErrorResponse = (message = 'Test error', status = 500) => ({
  response: {
    status,
    data: { error: message }
  }
})

// Wait for async operations in tests
export const waitForLoadingToFinish = () =>
  new Promise(resolve => setTimeout(resolve, 0))

// Mock drag and drop events
export const createMockDragEvent = (type, files = []) => {
  const event = new Event(type, { bubbles: true })
  
  if (files.length > 0) {
    const dataTransfer = {
      files: createMockFileList(files),
      items: files.map(file => ({
        kind: 'file',
        type: file.type,
        getAsFile: () => file
      })),
      setData: vi.fn(),
      getData: vi.fn()
    }
    
    Object.defineProperty(event, 'dataTransfer', {
      value: dataTransfer,
      writable: false
    })
  }
  
  return event
}

// Mock clipboard events
export const createMockClipboardEvent = (files = []) => {
  const event = new Event('paste', { bubbles: true })
  
  const clipboardData = {
    files: createMockFileList(files),
    items: files.map(file => ({
      kind: 'file',
      type: file.type,
      getAsFile: () => file
    }))
  }
  
  Object.defineProperty(event, 'clipboardData', {
    value: clipboardData,
    writable: false
  })
  
  return event
}

// Test data generators
export const generateMockDocuments = (count = 5) => {
  return Array.from({ length: count }, (_, index) => 
    createMockDocument({
      id: String(index + 1),
      original_filename: `document_${index + 1}.pdf`,
      status: ['uploaded', 'processing', 'approved', 'review_required', 'error'][index % 5]
    })
  )
}

export const generateMockExtractions = (count = 3) => {
  const fieldNames = ['amount', 'date', 'vendor_name', 'invoice_number', 'description']
  return Array.from({ length: count }, (_, index) =>
    createMockExtraction({
      id: String(index + 1),
      field_name: fieldNames[index % fieldNames.length],
      field_value: `Value ${index + 1}`,
      confidence: 0.8 + (index * 0.05) // Varying confidence levels
    })
  )
}

// Console suppression for noisy tests
export const suppressConsoleError = () => {
  const originalError = console.error
  beforeEach(() => {
    console.error = vi.fn()
  })
  afterEach(() => {
    console.error = originalError
  })
}

export const suppressConsoleWarn = () => {
  const originalWarn = console.warn
  beforeEach(() => {
    console.warn = vi.fn()
  })
  afterEach(() => {
    console.warn = originalWarn
  })
}