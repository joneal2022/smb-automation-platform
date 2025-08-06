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

// Workflow test data factories
export const createMockNodeType = (overrides = {}) => ({
  id: '1',
  name: 'Start Process',
  type: 'start',
  icon: 'play',
  color: '#28a745',
  description: 'Start node for workflow',
  config_schema: {
    properties: {
      timeout: { type: 'number', default: 300 }
    }
  },
  requires_user_action: false,
  allows_multiple_outputs: false,
  created_at: '2025-08-01T10:00:00Z',
  updated_at: '2025-08-01T10:00:00Z',
  ...overrides
})

export const createMockWorkflowTemplate = (overrides = {}) => ({
  id: '1',
  name: 'Invoice Processing',
  description: 'Process invoices automatically',
  category: 'document_processing',
  definition: {
    nodes: [
      {
        node_id: 'start_1',
        name: 'Start Process',
        type: 'start',
        position: { x: 100, y: 100 },
        config: {}
      },
      {
        node_id: 'end_1',
        name: 'End Process',
        type: 'end',
        position: { x: 300, y: 100 },
        config: {}
      }
    ],
    edges: [
      {
        source: 'start_1',
        target: 'end_1',
        condition_type: 'always'
      }
    ]
  },
  setup_time_minutes: 30,
  complexity_level: 2,
  tags: ['invoice', 'automation'],
  usage_count: 15,
  is_active: true,
  created_by: 1,
  created_by_name: 'Admin User',
  created_at: '2025-08-01T09:00:00Z',
  updated_at: '2025-08-01T09:00:00Z',
  ...overrides
})

export const createMockWorkflow = (overrides = {}) => ({
  id: '1',
  name: 'Test Workflow',
  description: 'Test workflow description',
  created_by: 1,
  created_by_name: 'Test User',
  assigned_users: [1],
  assigned_users_details: [
    {
      id: 1,
      name: 'Test User',
      email: 'test@example.com'
    }
  ],
  status: 'draft',
  trigger_type: 'manual',
  definition: {
    nodes: [],
    edges: [],
    version: 1
  },
  template: null,
  template_name: null,
  schedule_config: {},
  total_executions: 5,
  successful_executions: 4,
  failed_executions: 1,
  average_duration_seconds: 125.5,
  success_rate: 80.0,
  nodes: [],
  edges: [],
  created_at: '2025-08-01T08:00:00Z',
  updated_at: '2025-08-01T08:30:00Z',
  last_executed_at: '2025-08-01T12:00:00Z',
  ...overrides
})

export const createMockWorkflowNode = (overrides = {}) => ({
  id: '1',
  workflow: '1',
  node_type: '1',
  node_type_details: createMockNodeType(),
  node_id: 'node_1',
  name: 'Test Node',
  description: 'Test node description',
  position_x: 200,
  position_y: 150,
  config: {
    timeout_seconds: 300,
    retry_count: 3,
    priority: 'normal'
  },
  is_required: true,
  timeout_seconds: 300,
  retry_count: 3,
  assigned_user: null,
  assigned_user_name: null,
  created_at: '2025-08-01T08:15:00Z',
  updated_at: '2025-08-01T08:15:00Z',
  ...overrides
})

export const createMockWorkflowExecution = (overrides = {}) => ({
  id: '1',
  workflow: '1',
  workflow_name: 'Test Workflow',
  status: 'completed',
  triggered_by: 1,
  triggered_by_name: 'Test User',
  trigger_data: {
    source: 'manual',
    user_action: true
  },
  current_node: null,
  current_node_name: null,
  context_data: {
    variables: {},
    metadata: {}
  },
  started_at: '2025-08-01T12:00:00Z',
  completed_at: '2025-08-01T12:02:30Z',
  duration_seconds: 150.0,
  error_message: '',
  error_details: {},
  node_executions: [],
  ...overrides
})

export const createMockWorkflowCanvas = (overrides = {}) => ({
  id: '1',
  name: 'Canvas Workflow',
  description: 'Workflow for canvas testing',
  status: 'draft',
  nodes: [
    {
      id: 'start_1',
      node_id: 'start_1',
      name: 'Start Process',
      type: 'start',
      icon: 'play',
      color: '#28a745',
      position: { x: 100, y: 100 },
      config: {},
      requires_user_action: false,
      allows_multiple_outputs: false
    },
    {
      id: 'end_1',
      node_id: 'end_1',
      name: 'End Process',
      type: 'end',
      icon: 'stop',
      color: '#dc3545',
      position: { x: 300, y: 100 },
      config: {},
      requires_user_action: false,
      allows_multiple_outputs: false
    }
  ],
  edges: [
    {
      id: 'edge_1',
      source: 'start_1',
      target: 'end_1',
      condition_type: 'always',
      label: '',
      condition_config: {}
    }
  ],
  definition: {
    nodes: [],
    edges: [],
    version: 1
  },
  ...overrides
})

// Workflow test data generators
export const generateMockWorkflowTemplates = (count = 3) => {
  const categories = ['document_processing', 'approval', 'customer_service', 'integration', 'compliance']
  const names = ['Invoice Processing', 'Customer Onboarding', 'Contract Review', 'Expense Processing', 'Support Ticket']
  
  return Array.from({ length: count }, (_, index) =>
    createMockWorkflowTemplate({
      id: String(index + 1),
      name: names[index % names.length],
      category: categories[index % categories.length],
      usage_count: Math.floor(Math.random() * 50),
      complexity_level: Math.floor(Math.random() * 5) + 1
    })
  )
}

export const generateMockWorkflows = (count = 5) => {
  const statuses = ['draft', 'active', 'paused', 'inactive', 'archived']
  const triggerTypes = ['manual', 'schedule', 'event', 'webhook', 'document_upload']
  
  return Array.from({ length: count }, (_, index) =>
    createMockWorkflow({
      id: String(index + 1),
      name: `Workflow ${index + 1}`,
      status: statuses[index % statuses.length],
      trigger_type: triggerTypes[index % triggerTypes.length],
      total_executions: Math.floor(Math.random() * 100),
      success_rate: Math.random() * 100
    })
  )
}

export const generateMockExecutions = (count = 10) => {
  const statuses = ['queued', 'running', 'paused', 'completed', 'failed', 'cancelled']
  
  return Array.from({ length: count }, (_, index) => {
    const status = statuses[index % statuses.length]
    const isCompleted = ['completed', 'failed', 'cancelled'].includes(status)
    
    return createMockWorkflowExecution({
      id: String(index + 1),
      status,
      started_at: new Date(Date.now() - (index * 60 * 60 * 1000)).toISOString(), // Hours ago
      completed_at: isCompleted ? new Date(Date.now() - (index * 60 * 60 * 1000) + (Math.random() * 300000)).toISOString() : null,
      duration_seconds: isCompleted ? Math.random() * 300 : null,
      error_message: status === 'failed' ? `Error in execution ${index + 1}` : ''
    })
  })
}

// ReactFlow test utilities
export const createMockReactFlowNode = (overrides = {}) => ({
  id: 'node_1',
  type: 'workflowNode',
  position: { x: 100, y: 100 },
  data: {
    nodeId: 'node_1',
    name: 'Test Node',
    nodeType: 'start',
    icon: 'play',
    color: '#28a745',
    config: {},
    requires_user_action: false,
    allows_multiple_outputs: false
  },
  ...overrides
})

export const createMockReactFlowEdge = (overrides = {}) => ({
  id: 'edge_1',
  source: 'node_1',
  target: 'node_2',
  type: 'smoothstep',
  label: 'Always',
  data: {
    condition_type: 'always',
    condition_config: {}
  },
  ...overrides
})

// Workflow builder test helpers
export const mockDragAndDrop = {
  dragStart: (element, nodeType) => {
    const dragEvent = new DragEvent('dragstart', { bubbles: true })
    Object.defineProperty(dragEvent, 'dataTransfer', {
      value: {
        setData: vi.fn(),
        getData: vi.fn(() => JSON.stringify({ type: nodeType })),
        effectAllowed: 'copy'
      }
    })
    element.dispatchEvent(dragEvent)
  },
  
  drop: (element, position = { x: 200, y: 150 }) => {
    const dropEvent = new DragEvent('drop', { bubbles: true })
    Object.defineProperty(dropEvent, 'dataTransfer', {
      value: {
        getData: vi.fn(() => JSON.stringify({ type: 'start' }))
      }
    })
    Object.defineProperty(dropEvent, 'clientX', { value: position.x })
    Object.defineProperty(dropEvent, 'clientY', { value: position.y })
    element.dispatchEvent(dropEvent)
  }
}

// Mock workflow API responses
export const createMockAPIResponse = (data, status = 200) => ({
  data,
  status,
  statusText: 'OK',
  headers: {},
  config: {}
})

export const createMockAPIError = (message = 'API Error', status = 500) => {
  const error = new Error(message)
  error.response = {
    data: { error: message },
    status,
    statusText: status === 404 ? 'Not Found' : 'Internal Server Error'
  }
  return error
}