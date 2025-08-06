import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Row, 
  Col, 
  Card, 
  Button, 
  Table, 
  Badge, 
  Dropdown,
  Modal,
  Form,
  Alert,
  Spinner
} from 'react-bootstrap';
import { 
  Plus, 
  Play, 
  Pause, 
  Edit, 
  Trash2, 
  Copy, 
  MoreVertical,
  Calendar,
  Clock,
  Activity
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';

import NavigationHeader from '../../components/organisms/NavigationHeader';
import { workflowAPI } from '../../services/api/workflowAPI';

const WorkflowListPage = () => {
  const navigate = useNavigate();
  const [workflows, setWorkflows] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showTemplateModal, setShowTemplateModal] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [createFromTemplate, setCreateFromTemplate] = useState(null);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('success');
  const [filterStatus, setFilterStatus] = useState('all');
  
  // Form state for creating new workflow
  const [newWorkflow, setNewWorkflow] = useState({
    name: '',
    description: '',
    trigger_type: 'manual'
  });

  useEffect(() => {
    loadWorkflows();
    loadTemplates();
  }, [filterStatus]);

  const loadWorkflows = async () => {
    try {
      const params = filterStatus !== 'all' ? { status: filterStatus } : {};
      const response = await workflowAPI.getWorkflows(params);
      setWorkflows(response.data.results || response.data);
    } catch (error) {
      console.error('Failed to load workflows:', error);
      showMessage('Failed to load workflows', 'danger');
    } finally {
      setLoading(false);
    }
  };

  const loadTemplates = async () => {
    try {
      const response = await workflowAPI.getWorkflowTemplates();
      setTemplates(response.data.results || response.data);
    } catch (error) {
      console.error('Failed to load templates:', error);
    }
  };

  const showMessage = (text, type = 'success') => {
    setMessage(text);
    setMessageType(type);
    setTimeout(() => setMessage(''), 5000);
  };

  const handleCreateWorkflow = async () => {
    try {
      const response = await workflowAPI.createWorkflow(newWorkflow);
      setWorkflows([response.data, ...workflows]);
      setShowCreateModal(false);
      setNewWorkflow({ name: '', description: '', trigger_type: 'manual' });
      showMessage('Workflow created successfully!');
      
      // Navigate to workflow builder
      navigate(`/workflows/builder?id=${response.data.id}`);
    } catch (error) {
      console.error('Failed to create workflow:', error);
      showMessage('Failed to create workflow', 'danger');
    }
  };

  const handleCreateFromTemplate = async (template) => {
    try {
      const response = await workflowAPI.createWorkflowFromTemplate(template.id);
      setWorkflows([response.data, ...workflows]);
      setShowTemplateModal(false);
      showMessage(`Workflow created from template: ${template.name}`);
      
      // Navigate to workflow builder
      navigate(`/workflows/builder?id=${response.data.id}`);
    } catch (error) {
      console.error('Failed to create workflow from template:', error);
      showMessage('Failed to create workflow from template', 'danger');
    }
  };

  const handleActivateWorkflow = async (workflowId, currentStatus) => {
    try {
      if (currentStatus === 'active') {
        await workflowAPI.deactivateWorkflow(workflowId);
        showMessage('Workflow deactivated successfully!');
      } else {
        await workflowAPI.activateWorkflow(workflowId);
        showMessage('Workflow activated successfully!');
      }
      loadWorkflows();
    } catch (error) {
      console.error('Failed to toggle workflow status:', error);
      showMessage('Failed to update workflow status', 'danger');
    }
  };

  const handleDeleteWorkflow = async (workflowId) => {
    if (!window.confirm('Are you sure you want to delete this workflow?')) return;
    
    try {
      await workflowAPI.deleteWorkflow(workflowId);
      setWorkflows(workflows.filter(w => w.id !== workflowId));
      showMessage('Workflow deleted successfully!');
    } catch (error) {
      console.error('Failed to delete workflow:', error);
      showMessage('Failed to delete workflow', 'danger');
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      'draft': { bg: 'secondary', text: 'Draft' },
      'active': { bg: 'success', text: 'Active' },
      'inactive': { bg: 'warning', text: 'Inactive' },
      'paused': { bg: 'info', text: 'Paused' },
      'archived': { bg: 'dark', text: 'Archived' }
    };
    
    const config = statusConfig[status] || statusConfig['draft'];
    return <Badge bg={config.bg}>{config.text}</Badge>;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <>
        <NavigationHeader />
        <Container className="py-4">
          <div className="d-flex justify-content-center align-items-center" style={{ height: '400px' }}>
            <Spinner animation="border" role="status">
              <span className="visually-hidden">Loading workflows...</span>
            </Spinner>
          </div>
        </Container>
      </>
    );
  }

  return (
    <>
      <NavigationHeader />
      <Container className="py-4">
        {/* Header */}
        <Row className="mb-4">
          <Col>
            <div className="d-flex justify-content-between align-items-center">
              <div>
                <h2 data-testid="workflows-page-title">Workflow Management</h2>
                <p className="text-muted mb-0">
                  Create, manage, and monitor your automated workflows
                </p>
              </div>
              <div className="d-flex gap-2">
                <Button 
                  variant="outline-primary"
                  onClick={() => setShowTemplateModal(true)}
                  data-testid="create-from-template-btn"
                >
                  <Copy size={16} className="me-1" />
                  From Template
                </Button>
                <Button 
                  variant="primary"
                  onClick={() => setShowCreateModal(true)}
                  data-testid="create-workflow-btn"
                >
                  <Plus size={16} className="me-1" />
                  New Workflow
                </Button>
              </div>
            </div>
          </Col>
        </Row>

        {/* Alert Messages */}
        {message && (
          <Alert variant={messageType} dismissible onClose={() => setMessage('')}>
            {message}
          </Alert>
        )}

        {/* Filter Controls */}
        <Row className="mb-3">
          <Col md={4}>
            <Form.Select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              data-testid="status-filter"
            >
              <option value="all">All Workflows</option>
              <option value="active">Active</option>
              <option value="draft">Draft</option>
              <option value="inactive">Inactive</option>
              <option value="paused">Paused</option>
            </Form.Select>
          </Col>
        </Row>

        {/* Workflows Table */}
        <Card>
          <Card.Body className="p-0">
            {workflows.length > 0 ? (
              <Table responsive hover className="mb-0">
                <thead className="bg-light">
                  <tr>
                    <th>Workflow Name</th>
                    <th>Status</th>
                    <th>Trigger</th>
                    <th>Executions</th>
                    <th>Success Rate</th>
                    <th>Last Run</th>
                    <th>Created</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {workflows.map(workflow => (
                    <tr key={workflow.id} data-testid={`workflow-row-${workflow.id}`}>
                      <td>
                        <div>
                          <div className="fw-semibold">{workflow.name}</div>
                          {workflow.description && (
                            <small className="text-muted">{workflow.description}</small>
                          )}
                          {workflow.template_name && (
                            <div>
                              <Badge bg="light" text="dark" className="me-1">
                                Template: {workflow.template_name}
                              </Badge>
                            </div>
                          )}
                        </div>
                      </td>
                      <td>{getStatusBadge(workflow.status)}</td>
                      <td>
                        <Badge bg="info" className="text-capitalize">
                          {workflow.trigger_type.replace('_', ' ')}
                        </Badge>
                      </td>
                      <td>
                        <div className="d-flex align-items-center">
                          <Activity size={14} className="me-1 text-muted" />
                          {workflow.total_executions || 0}
                        </div>
                      </td>
                      <td>
                        <div className="d-flex align-items-center">
                          {workflow.total_executions > 0 ? (
                            <span className={`fw-semibold ${
                              workflow.success_rate >= 90 ? 'text-success' :
                              workflow.success_rate >= 70 ? 'text-warning' :
                              'text-danger'
                            }`}>
                              {workflow.success_rate?.toFixed(1)}%
                            </span>
                          ) : (
                            <span className="text-muted">-</span>
                          )}
                        </div>
                      </td>
                      <td>
                        <div className="d-flex align-items-center">
                          <Clock size={14} className="me-1 text-muted" />
                          <small>{formatDate(workflow.last_executed_at)}</small>
                        </div>
                      </td>
                      <td>
                        <div className="d-flex align-items-center">
                          <Calendar size={14} className="me-1 text-muted" />
                          <small>{formatDate(workflow.created_at)}</small>
                        </div>
                      </td>
                      <td>
                        <Dropdown>
                          <Dropdown.Toggle 
                            variant="link" 
                            size="sm" 
                            className="text-muted border-0 shadow-none"
                            data-testid={`workflow-actions-${workflow.id}`}
                          >
                            <MoreVertical size={16} />
                          </Dropdown.Toggle>
                          <Dropdown.Menu align="end">
                            <Dropdown.Item
                              onClick={() => navigate(`/workflows/builder?id=${workflow.id}`)}
                            >
                              <Edit size={14} className="me-2" />
                              Edit Workflow
                            </Dropdown.Item>
                            <Dropdown.Item
                              onClick={() => handleActivateWorkflow(workflow.id, workflow.status)}
                            >
                              {workflow.status === 'active' ? (
                                <>
                                  <Pause size={14} className="me-2" />
                                  Deactivate
                                </>
                              ) : (
                                <>
                                  <Play size={14} className="me-2" />
                                  Activate
                                </>
                              )}
                            </Dropdown.Item>
                            <Dropdown.Divider />
                            <Dropdown.Item
                              className="text-danger"
                              onClick={() => handleDeleteWorkflow(workflow.id)}
                            >
                              <Trash2 size={14} className="me-2" />
                              Delete
                            </Dropdown.Item>
                          </Dropdown.Menu>
                        </Dropdown>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            ) : (
              <div className="text-center py-5">
                <Activity size={48} className="text-muted mb-3" />
                <h5>No Workflows Found</h5>
                <p className="text-muted mb-4">
                  {filterStatus !== 'all' 
                    ? `No workflows found with status: ${filterStatus}`
                    : 'Get started by creating your first workflow'
                  }
                </p>
                <div className="d-flex gap-2 justify-content-center">
                  <Button 
                    variant="outline-primary"
                    onClick={() => setShowTemplateModal(true)}
                  >
                    Browse Templates
                  </Button>
                  <Button 
                    variant="primary"
                    onClick={() => setShowCreateModal(true)}
                  >
                    Create New Workflow
                  </Button>
                </div>
              </div>
            )}
          </Card.Body>
        </Card>

        {/* Create New Workflow Modal */}
        <Modal show={showCreateModal} onHide={() => setShowCreateModal(false)}>
          <Modal.Header closeButton>
            <Modal.Title>Create New Workflow</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <Form>
              <Form.Group className="mb-3">
                <Form.Label>Workflow Name</Form.Label>
                <Form.Control
                  type="text"
                  value={newWorkflow.name}
                  onChange={(e) => setNewWorkflow({...newWorkflow, name: e.target.value})}
                  placeholder="Enter workflow name"
                  data-testid="new-workflow-name"
                />
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label>Description</Form.Label>
                <Form.Control
                  as="textarea"
                  rows={3}
                  value={newWorkflow.description}
                  onChange={(e) => setNewWorkflow({...newWorkflow, description: e.target.value})}
                  placeholder="Describe what this workflow does"
                  data-testid="new-workflow-description"
                />
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label>Trigger Type</Form.Label>
                <Form.Select
                  value={newWorkflow.trigger_type}
                  onChange={(e) => setNewWorkflow({...newWorkflow, trigger_type: e.target.value})}
                  data-testid="new-workflow-trigger"
                >
                  <option value="manual">Manual Start</option>
                  <option value="schedule">Scheduled</option>
                  <option value="webhook">Webhook</option>
                  <option value="document_upload">Document Upload</option>
                </Form.Select>
              </Form.Group>
            </Form>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowCreateModal(false)}>
              Cancel
            </Button>
            <Button 
              variant="primary" 
              onClick={handleCreateWorkflow}
              disabled={!newWorkflow.name.trim()}
              data-testid="create-workflow-submit"
            >
              Create & Edit
            </Button>
          </Modal.Footer>
        </Modal>

        {/* Template Selection Modal */}
        <Modal 
          show={showTemplateModal} 
          onHide={() => setShowTemplateModal(false)}
          size="lg"
        >
          <Modal.Header closeButton>
            <Modal.Title>Choose a Template</Modal.Title>
          </Modal.Header>
          <Modal.Body>
            <Row>
              {templates.map(template => (
                <Col md={6} key={template.id} className="mb-3">
                  <Card className="h-100 workflow-template-card" style={{ cursor: 'pointer' }}>
                    <Card.Body onClick={() => handleCreateFromTemplate(template)}>
                      <div className="d-flex justify-content-between align-items-start mb-2">
                        <h6 className="card-title">{template.name}</h6>
                        <Badge bg="primary">
                          Level {template.complexity_level}
                        </Badge>
                      </div>
                      <p className="card-text small text-muted mb-2">
                        {template.description}
                      </p>
                      <div className="d-flex justify-content-between align-items-center">
                        <small className="text-muted">
                          ~{template.setup_time_minutes} min setup
                        </small>
                        <small className="text-muted">
                          Used {template.usage_count} times
                        </small>
                      </div>
                      {template.tags && template.tags.length > 0 && (
                        <div className="mt-2">
                          {template.tags.slice(0, 3).map(tag => (
                            <Badge key={tag} bg="light" text="dark" className="me-1">
                              {tag}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </Card.Body>
                  </Card>
                </Col>
              ))}
            </Row>
            {templates.length === 0 && (
              <div className="text-center py-4">
                <p className="text-muted">No templates available</p>
              </div>
            )}
          </Modal.Body>
        </Modal>
      </Container>

      <style jsx>{`
        .workflow-template-card {
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .workflow-template-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
      `}</style>
    </>
  );
};

export default WorkflowListPage;