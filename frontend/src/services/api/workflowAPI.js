import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000/api';

// Create axios instance with authentication
const createAuthenticatedAxios = () => {
  const token = localStorage.getItem('access_token');
  return axios.create({
    baseURL: API_BASE_URL,
    headers: {
      'Authorization': token ? `Bearer ${token}` : '',
      'Content-Type': 'application/json',
    },
  });
};

export const workflowAPI = {
  // Node Types
  getNodeTypes: async () => {
    const api = createAuthenticatedAxios();
    return api.get('/node-types/');
  },

  getNodeTypesByCategory: async () => {
    const api = createAuthenticatedAxios();
    return api.get('/node-types/by_type/');
  },

  // Workflow Templates
  getWorkflowTemplates: async (params = {}) => {
    const api = createAuthenticatedAxios();
    return api.get('/templates/', { params });
  },

  getWorkflowTemplate: async (templateId) => {
    const api = createAuthenticatedAxios();
    return api.get(`/templates/${templateId}/`);
  },

  createWorkflowFromTemplate: async (templateId, workflowData = {}) => {
    const api = createAuthenticatedAxios();
    return api.post(`/templates/${templateId}/use_template/`, workflowData);
  },

  // Workflows
  getWorkflows: async (params = {}) => {
    const api = createAuthenticatedAxios();
    return api.get('/workflows/', { params });
  },

  getWorkflow: async (workflowId) => {
    const api = createAuthenticatedAxios();
    return api.get(`/workflows/${workflowId}/`);
  },

  getWorkflowCanvas: async (workflowId) => {
    const api = createAuthenticatedAxios();
    return api.get(`/workflows/${workflowId}/canvas/`);
  },

  createWorkflow: async (workflowData) => {
    const api = createAuthenticatedAxios();
    return api.post('/workflows/', workflowData);
  },

  updateWorkflow: async (workflowId, workflowData) => {
    const api = createAuthenticatedAxios();
    return api.put(`/workflows/${workflowId}/`, workflowData);
  },

  deleteWorkflow: async (workflowId) => {
    const api = createAuthenticatedAxios();
    return api.delete(`/workflows/${workflowId}/`);
  },

  saveWorkflowCanvas: async (workflowId, canvasData) => {
    const api = createAuthenticatedAxios();
    return api.post(`/workflows/${workflowId}/save_canvas/`, canvasData);
  },

  activateWorkflow: async (workflowId) => {
    const api = createAuthenticatedAxios();
    return api.post(`/workflows/${workflowId}/activate/`);
  },

  deactivateWorkflow: async (workflowId) => {
    const api = createAuthenticatedAxios();
    return api.post(`/workflows/${workflowId}/deactivate/`);
  },

  executeWorkflow: async (workflowId, triggerData = {}) => {
    const api = createAuthenticatedAxios();
    return api.post(`/workflows/${workflowId}/execute/`, { trigger_data: triggerData });
  },

  // Workflow Executions
  getWorkflowExecutions: async (workflowId, params = {}) => {
    const api = createAuthenticatedAxios();
    return api.get(`/workflows/${workflowId}/executions/`, { params });
  },

  getAllExecutions: async (params = {}) => {
    const api = createAuthenticatedAxios();
    return api.get('/executions/', { params });
  },

  getExecution: async (executionId) => {
    const api = createAuthenticatedAxios();
    return api.get(`/executions/${executionId}/`);
  },

  cancelExecution: async (executionId) => {
    const api = createAuthenticatedAxios();
    return api.post(`/executions/${executionId}/cancel/`);
  },

  // Audit Logs
  getAuditLogs: async (params = {}) => {
    const api = createAuthenticatedAxios();
    return api.get('/audit-logs/', { params });
  },

  // Statistics and Dashboard Data
  getWorkflowStats: async (workflowId) => {
    const api = createAuthenticatedAxios();
    try {
      const response = await api.get(`/workflows/${workflowId}/`);
      const workflow = response.data;
      
      return {
        total_executions: workflow.total_executions || 0,
        successful_executions: workflow.successful_executions || 0,
        failed_executions: workflow.failed_executions || 0,
        success_rate: workflow.success_rate || 0,
        average_duration: workflow.average_duration_seconds || 0,
        last_executed: workflow.last_executed_at,
        status: workflow.status
      };
    } catch (error) {
      console.error('Failed to get workflow stats:', error);
      return {
        total_executions: 0,
        successful_executions: 0,
        failed_executions: 0,
        success_rate: 0,
        average_duration: 0,
        last_executed: null,
        status: 'draft'
      };
    }
  },

  getDashboardStats: async () => {
    const api = createAuthenticatedAxios();
    try {
      const [workflowsResponse, executionsResponse] = await Promise.all([
        api.get('/workflows/'),
        api.get('/executions/')
      ]);

      const workflows = workflowsResponse.data.results || workflowsResponse.data;
      const executions = executionsResponse.data.results || executionsResponse.data;

      // Calculate summary statistics
      const totalWorkflows = workflows.length;
      const activeWorkflows = workflows.filter(w => w.status === 'active').length;
      const totalExecutions = executions.length;
      const recentExecutions = executions.filter(e => {
        const executionDate = new Date(e.started_at);
        const dayAgo = new Date(Date.now() - 24 * 60 * 60 * 1000);
        return executionDate > dayAgo;
      }).length;

      return {
        total_workflows: totalWorkflows,
        active_workflows: activeWorkflows,
        total_executions: totalExecutions,
        recent_executions: recentExecutions,
        workflows,
        executions: executions.slice(0, 10) // Recent 10 executions
      };
    } catch (error) {
      console.error('Failed to get dashboard stats:', error);
      return {
        total_workflows: 0,
        active_workflows: 0,
        total_executions: 0,
        recent_executions: 0,
        workflows: [],
        executions: []
      };
    }
  }
};

export default workflowAPI;