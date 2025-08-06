import { http, HttpResponse } from 'msw'
import {
  createMockNodeType,
  createMockWorkflowTemplate,
  createMockWorkflow,
  createMockWorkflowExecution,
  createMockWorkflowCanvas,
  generateMockWorkflowTemplates,
  generateMockWorkflows,
  generateMockExecutions
} from '../utils.jsx'

const API_BASE_URL = 'http://localhost:8000/api'

// Mock data stores
let nodeTypes = [
  createMockNodeType({ id: '1', name: 'Start Process', type: 'start', icon: 'play' }),
  createMockNodeType({ id: '2', name: 'Process Document', type: 'process', icon: 'cog' }),
  createMockNodeType({ id: '3', name: 'Make Decision', type: 'decision', icon: 'git-branch' }),
  createMockNodeType({ id: '4', name: 'Require Approval', type: 'approval', icon: 'check-circle' }),
  createMockNodeType({ id: '5', name: 'End Process', type: 'end', icon: 'stop' })
]

let workflowTemplates = generateMockWorkflowTemplates(5)
let workflows = generateMockWorkflows(10)
let executions = generateMockExecutions(20)

export const workflowHandlers = [
  // Node Types
  http.get(`${API_BASE_URL}/node-types/`, () => {
    return HttpResponse.json(nodeTypes)
  }),

  http.get(`${API_BASE_URL}/node-types/by_type/`, () => {
    const grouped = nodeTypes.reduce((acc, nodeType) => {
      if (!acc[nodeType.type]) {
        acc[nodeType.type] = []
      }
      acc[nodeType.type].push(nodeType)
      return acc
    }, {})
    return HttpResponse.json(grouped)
  }),

  http.get(`${API_BASE_URL}/node-types/:id/`, ({ params }) => {
    const nodeType = nodeTypes.find(nt => nt.id === params.id)
    if (!nodeType) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(nodeType)
  }),

  // Workflow Templates
  http.get(`${API_BASE_URL}/templates/`, ({ request }) => {
    const url = new URL(request.url)
    const category = url.searchParams.get('category')
    const search = url.searchParams.get('search')
    
    let filteredTemplates = [...workflowTemplates]
    
    if (category) {
      filteredTemplates = filteredTemplates.filter(t => t.category === category)
    }
    
    if (search) {
      filteredTemplates = filteredTemplates.filter(t => 
        t.name.toLowerCase().includes(search.toLowerCase()) ||
        t.description.toLowerCase().includes(search.toLowerCase())
      )
    }
    
    return HttpResponse.json(filteredTemplates)
  }),

  http.get(`${API_BASE_URL}/templates/:id/`, ({ params }) => {
    const template = workflowTemplates.find(t => t.id === params.id)
    if (!template) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(template)
  }),

  http.post(`${API_BASE_URL}/templates/`, async ({ request }) => {
    const newTemplate = await request.json()
    const template = createMockWorkflowTemplate({
      ...newTemplate,
      id: String(workflowTemplates.length + 1),
      usage_count: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
    workflowTemplates.push(template)
    return HttpResponse.json(template, { status: 201 })
  }),

  http.post(`${API_BASE_URL}/templates/:id/use_template/`, ({ params }) => {
    const template = workflowTemplates.find(t => t.id === params.id)
    if (!template) {
      return new HttpResponse(null, { status: 404 })
    }
    
    // Increment usage count
    template.usage_count += 1
    
    // Create new workflow from template
    const newWorkflow = createMockWorkflowCanvas({
      id: String(workflows.length + 1),
      name: `${template.name} - User Copy`,
      description: `Created from template: ${template.description}`,
      template: template.id,
      definition: template.definition
    })
    
    workflows.push(newWorkflow)
    return HttpResponse.json(newWorkflow, { status: 201 })
  }),

  // Workflows
  http.get(`${API_BASE_URL}/workflows/`, ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')
    const search = url.searchParams.get('search')
    
    let filteredWorkflows = [...workflows]
    
    if (status) {
      filteredWorkflows = filteredWorkflows.filter(w => w.status === status)
    }
    
    if (search) {
      filteredWorkflows = filteredWorkflows.filter(w => 
        w.name.toLowerCase().includes(search.toLowerCase()) ||
        w.description.toLowerCase().includes(search.toLowerCase())
      )
    }
    
    return HttpResponse.json(filteredWorkflows)
  }),

  http.get(`${API_BASE_URL}/workflows/:id/`, ({ params }) => {
    const workflow = workflows.find(w => w.id === params.id)
    if (!workflow) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(workflow)
  }),

  http.post(`${API_BASE_URL}/workflows/`, async ({ request }) => {
    const workflowData = await request.json()
    const newWorkflow = createMockWorkflow({
      ...workflowData,
      id: String(workflows.length + 1),
      total_executions: 0,
      successful_executions: 0,
      failed_executions: 0,
      success_rate: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    })
    workflows.push(newWorkflow)
    return HttpResponse.json(newWorkflow, { status: 201 })
  }),

  http.put(`${API_BASE_URL}/workflows/:id/`, async ({ params, request }) => {
    const workflowData = await request.json()
    const workflowIndex = workflows.findIndex(w => w.id === params.id)
    
    if (workflowIndex === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    
    workflows[workflowIndex] = {
      ...workflows[workflowIndex],
      ...workflowData,
      updated_at: new Date().toISOString()
    }
    
    return HttpResponse.json(workflows[workflowIndex])
  }),

  http.patch(`${API_BASE_URL}/workflows/:id/`, async ({ params, request }) => {
    const workflowData = await request.json()
    const workflowIndex = workflows.findIndex(w => w.id === params.id)
    
    if (workflowIndex === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    
    workflows[workflowIndex] = {
      ...workflows[workflowIndex],
      ...workflowData,
      updated_at: new Date().toISOString()
    }
    
    return HttpResponse.json(workflows[workflowIndex])
  }),

  http.delete(`${API_BASE_URL}/workflows/:id/`, ({ params }) => {
    const workflowIndex = workflows.findIndex(w => w.id === params.id)
    
    if (workflowIndex === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    
    workflows.splice(workflowIndex, 1)
    return new HttpResponse(null, { status: 204 })
  }),

  // Workflow Canvas
  http.get(`${API_BASE_URL}/workflows/:id/canvas/`, ({ params }) => {
    const workflow = workflows.find(w => w.id === params.id)
    if (!workflow) {
      return new HttpResponse(null, { status: 404 })
    }
    
    const canvasData = createMockWorkflowCanvas({
      id: workflow.id,
      name: workflow.name,
      description: workflow.description,
      status: workflow.status
    })
    
    return HttpResponse.json(canvasData)
  }),

  http.post(`${API_BASE_URL}/workflows/:id/save_canvas/`, async ({ params, request }) => {
    const canvasData = await request.json()
    const workflowIndex = workflows.findIndex(w => w.id === params.id)
    
    if (workflowIndex === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    
    // Update workflow with canvas data
    workflows[workflowIndex] = {
      ...workflows[workflowIndex],
      definition: {
        nodes: canvasData.nodes,
        edges: canvasData.edges,
        version: (workflows[workflowIndex].definition?.version || 0) + 1
      },
      updated_at: new Date().toISOString()
    }
    
    const updatedCanvas = createMockWorkflowCanvas({
      id: workflows[workflowIndex].id,
      name: workflows[workflowIndex].name,
      description: workflows[workflowIndex].description,
      status: workflows[workflowIndex].status,
      nodes: canvasData.nodes || [],
      edges: canvasData.edges || []
    })
    
    return HttpResponse.json(updatedCanvas)
  }),

  // Workflow Actions
  http.post(`${API_BASE_URL}/workflows/:id/activate/`, ({ params }) => {
    const workflowIndex = workflows.findIndex(w => w.id === params.id)
    
    if (workflowIndex === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    
    const workflow = workflows[workflowIndex]
    
    // Validate workflow has start and end nodes
    const hasStartNode = workflow.nodes?.some(n => n.type === 'start') || workflow.definition?.nodes?.some(n => n.type === 'start')
    const hasEndNode = workflow.nodes?.some(n => n.type === 'end') || workflow.definition?.nodes?.some(n => n.type === 'end')
    
    if (!hasStartNode) {
      return HttpResponse.json(
        { error: 'Workflow must have at least one start node' },
        { status: 400 }
      )
    }
    
    if (!hasEndNode) {
      return HttpResponse.json(
        { error: 'Workflow must have at least one end node' },
        { status: 400 }
      )
    }
    
    workflows[workflowIndex].status = 'active'
    workflows[workflowIndex].updated_at = new Date().toISOString()
    
    return HttpResponse.json({ status: 'activated' })
  }),

  http.post(`${API_BASE_URL}/workflows/:id/deactivate/`, ({ params }) => {
    const workflowIndex = workflows.findIndex(w => w.id === params.id)
    
    if (workflowIndex === -1) {
      return new HttpResponse(null, { status: 404 })
    }
    
    workflows[workflowIndex].status = 'inactive'
    workflows[workflowIndex].updated_at = new Date().toISOString()
    
    return HttpResponse.json({ status: 'deactivated' })
  }),

  http.post(`${API_BASE_URL}/workflows/:id/execute/`, async ({ params, request }) => {
    const workflow = workflows.find(w => w.id === params.id)
    
    if (!workflow) {
      return new HttpResponse(null, { status: 404 })
    }
    
    if (workflow.status !== 'active') {
      return HttpResponse.json(
        { error: 'Workflow must be active to execute' },
        { status: 400 }
      )
    }
    
    const requestData = await request.json()
    
    const newExecution = createMockWorkflowExecution({
      id: String(executions.length + 1),
      workflow: workflow.id,
      workflow_name: workflow.name,
      status: 'queued',
      trigger_data: requestData.trigger_data || {},
      started_at: new Date().toISOString(),
      completed_at: null,
      duration_seconds: null
    })
    
    executions.push(newExecution)
    
    // Update workflow execution counts
    const workflowIndex = workflows.findIndex(w => w.id === params.id)
    workflows[workflowIndex].total_executions += 1
    workflows[workflowIndex].last_executed_at = new Date().toISOString()
    
    return HttpResponse.json(newExecution, { status: 201 })
  }),

  // Workflow Executions
  http.get(`${API_BASE_URL}/workflows/:id/executions/`, ({ params }) => {
    const workflowExecutions = executions.filter(e => e.workflow === params.id)
    return HttpResponse.json(workflowExecutions)
  }),

  http.get(`${API_BASE_URL}/executions/`, ({ request }) => {
    const url = new URL(request.url)
    const status = url.searchParams.get('status')
    
    let filteredExecutions = [...executions]
    
    if (status) {
      filteredExecutions = filteredExecutions.filter(e => e.status === status)
    }
    
    return HttpResponse.json(filteredExecutions)
  }),

  http.get(`${API_BASE_URL}/executions/:id/`, ({ params }) => {
    const execution = executions.find(e => e.id === params.id)
    if (!execution) {
      return new HttpResponse(null, { status: 404 })
    }
    return HttpResponse.json(execution)
  }),

  // Audit Logs
  http.get(`${API_BASE_URL}/audit-logs/`, ({ request }) => {
    const url = new URL(request.url)
    const workflow = url.searchParams.get('workflow')
    const action = url.searchParams.get('action')
    
    // Mock audit logs
    let mockLogs = [
      {
        id: '1',
        workflow: '1',
        workflow_name: 'Test Workflow',
        user: 1,
        user_name: 'Test User',
        action: 'workflow_created',
        description: 'Workflow created',
        timestamp: new Date(Date.now() - 60000).toISOString()
      },
      {
        id: '2',
        workflow: '1',
        workflow_name: 'Test Workflow',
        user: 1,
        user_name: 'Test User',
        action: 'execution_started',
        description: 'Workflow execution started',
        timestamp: new Date().toISOString()
      }
    ]
    
    if (workflow) {
      mockLogs = mockLogs.filter(log => log.workflow === workflow)
    }
    
    if (action) {
      mockLogs = mockLogs.filter(log => log.action === action)
    }
    
    return HttpResponse.json(mockLogs)
  }),

  // Dashboard Stats
  http.get(`${API_BASE_URL}/audit-logs/dashboard_stats/`, () => {
    const stats = {
      total_workflows: workflows.length,
      active_workflows: workflows.filter(w => w.status === 'active').length,
      total_executions: executions.length,
      recent_executions: executions.filter(e => {
        const executionDate = new Date(e.started_at)
        const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000)
        return executionDate > dayAgo
      }).length,
      running_executions: executions.filter(e => e.status === 'running').length,
      success_rate: executions.length > 0 ? 
        (executions.filter(e => e.status === 'completed').length / executions.length) * 100 : 0,
      average_duration: executions.filter(e => e.duration_seconds).reduce(
        (sum, e) => sum + e.duration_seconds, 0
      ) / executions.filter(e => e.duration_seconds).length || 0,
      last_updated: new Date().toISOString()
    }
    
    return HttpResponse.json(stats)
  }),

  // Error simulation handlers
  http.get(`${API_BASE_URL}/workflows/error-test/`, () => {
    return new HttpResponse(null, { status: 500 })
  }),

  http.post(`${API_BASE_URL}/workflows/timeout-test/`, () => {
    // Simulate timeout by never resolving
    return new Promise(() => {})
  })
]

// Helper functions to manipulate mock data in tests
export const workflowMockHelpers = {
  // Reset mock data
  resetData: () => {
    nodeTypes = [
      createMockNodeType({ id: '1', name: 'Start Process', type: 'start', icon: 'play' }),
      createMockNodeType({ id: '2', name: 'Process Document', type: 'process', icon: 'cog' }),
      createMockNodeType({ id: '3', name: 'Make Decision', type: 'decision', icon: 'git-branch' }),
      createMockNodeType({ id: '4', name: 'Require Approval', type: 'approval', icon: 'check-circle' }),
      createMockNodeType({ id: '5', name: 'End Process', type: 'end', icon: 'stop' })
    ]
    workflowTemplates = generateMockWorkflowTemplates(5)
    workflows = generateMockWorkflows(10)
    executions = generateMockExecutions(20)
  },

  // Add specific test data
  addWorkflow: (workflow) => {
    workflows.push(workflow)
  },

  addExecution: (execution) => {
    executions.push(execution)
  },

  addTemplate: (template) => {
    workflowTemplates.push(template)
  },

  // Get current data
  getWorkflows: () => workflows,
  getExecutions: () => executions,
  getTemplates: () => workflowTemplates,
  getNodeTypes: () => nodeTypes,

  // Update specific items
  updateWorkflow: (id, updates) => {
    const index = workflows.findIndex(w => w.id === id)
    if (index !== -1) {
      workflows[index] = { ...workflows[index], ...updates }
    }
  },

  updateExecution: (id, updates) => {
    const index = executions.findIndex(e => e.id === id)
    if (index !== -1) {
      executions[index] = { ...executions[index], ...updates }
    }
  }
}