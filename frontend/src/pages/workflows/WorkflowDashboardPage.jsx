import React, { useState, useEffect } from 'react';
import { 
  Container, 
  Row, 
  Col, 
  Card, 
  Table, 
  Badge, 
  Alert,
  Spinner,
  Button,
  ProgressBar
} from 'react-bootstrap';
import { 
  Activity, 
  CheckCircle, 
  XCircle, 
  Clock, 
  Play,
  Pause,
  RefreshCw,
  TrendingUp,
  AlertTriangle
} from 'lucide-react';

import NavigationHeader from '../../components/organisms/NavigationHeader';
import { workflowAPI } from '../../services/api/workflowAPI';

const WorkflowDashboardPage = () => {
  const [dashboardStats, setDashboardStats] = useState(null);
  const [recentExecutions, setRecentExecutions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  useEffect(() => {
    loadDashboardData();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      const [statsResponse, executionsResponse] = await Promise.all([
        workflowAPI.getDashboardStats(),
        workflowAPI.getAllExecutions({ limit: 10 })
      ]);
      
      setDashboardStats(statsResponse);
      setRecentExecutions(executionsResponse.executions || []);
      setLastUpdated(new Date());
      setError('');
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
      setError('Failed to load dashboard data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      'completed': { bg: 'success', icon: CheckCircle, text: 'Completed' },
      'running': { bg: 'primary', icon: Play, text: 'Running' },
      'failed': { bg: 'danger', icon: XCircle, text: 'Failed' },
      'queued': { bg: 'warning', icon: Clock, text: 'Queued' },
      'cancelled': { bg: 'secondary', icon: Pause, text: 'Cancelled' }
    };
    
    const config = statusConfig[status] || statusConfig['queued'];
    const IconComponent = config.icon;
    
    return (
      <Badge bg={config.bg} className="d-flex align-items-center">
        <IconComponent size={12} className="me-1" />
        {config.text}
      </Badge>
    );
  };

  const formatDuration = (seconds) => {
    if (!seconds) return 'N/A';
    
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    } else if (seconds < 3600) {
      return `${(seconds / 60).toFixed(1)}m`;
    } else {
      return `${(seconds / 3600).toFixed(1)}h`;
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('en-US', {
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
              <span className="visually-hidden">Loading dashboard...</span>
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
                <h2 data-testid="workflow-dashboard-title">Workflow Monitoring</h2>
                <p className="text-muted mb-0">
                  Real-time overview of your workflow performance
                </p>
                {lastUpdated && (
                  <small className="text-muted">
                    Last updated: {formatDate(lastUpdated)}
                  </small>
                )}
              </div>
              <Button 
                variant="outline-primary"
                onClick={loadDashboardData}
                disabled={loading}
                data-testid="refresh-dashboard-btn"
              >
                <RefreshCw size={16} className={`me-1 ${loading ? 'spin' : ''}`} />
                Refresh
              </Button>
            </div>
          </Col>
        </Row>

        {/* Error Alert */}
        {error && (
          <Alert variant="danger" dismissible onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {/* Overview Cards */}
        {dashboardStats && (
          <Row className="mb-4">
            <Col md={3}>
              <Card className="h-100 border-0 shadow-sm">
                <Card.Body className="text-center">
                  <div className="mb-2">
                    <Activity size={32} className="text-primary" />
                  </div>
                  <h4 className="fw-bold mb-1" data-testid="total-workflows">
                    {dashboardStats.total_workflows}
                  </h4>
                  <p className="text-muted mb-0">Total Workflows</p>
                  <small className="text-success">
                    {dashboardStats.active_workflows} active
                  </small>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="h-100 border-0 shadow-sm">
                <Card.Body className="text-center">
                  <div className="mb-2">
                    <Play size={32} className="text-success" />
                  </div>
                  <h4 className="fw-bold mb-1" data-testid="total-executions">
                    {dashboardStats.total_executions}
                  </h4>
                  <p className="text-muted mb-0">Total Executions</p>
                  <small className="text-info">
                    {dashboardStats.recent_executions} in last 24h
                  </small>
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="h-100 border-0 shadow-sm">
                <Card.Body className="text-center">
                  <div className="mb-2">
                    <TrendingUp size={32} className="text-warning" />
                  </div>
                  <h4 className="fw-bold mb-1" data-testid="success-rate">
                    {dashboardStats.success_rate}%
                  </h4>
                  <p className="text-muted mb-0">Success Rate</p>
                  <ProgressBar 
                    now={dashboardStats.success_rate} 
                    variant={dashboardStats.success_rate >= 90 ? 'success' : dashboardStats.success_rate >= 70 ? 'warning' : 'danger'}
                    size="sm"
                  />
                </Card.Body>
              </Card>
            </Col>
            
            <Col md={3}>
              <Card className="h-100 border-0 shadow-sm">
                <Card.Body className="text-center">
                  <div className="mb-2">
                    <Clock size={32} className="text-info" />
                  </div>
                  <h4 className="fw-bold mb-1" data-testid="avg-duration">
                    {formatDuration(dashboardStats.average_duration)}
                  </h4>
                  <p className="text-muted mb-0">Avg. Duration</p>
                  {dashboardStats.running_executions > 0 && (
                    <small className="text-warning">
                      {dashboardStats.running_executions} running now
                    </small>
                  )}
                </Card.Body>
              </Card>
            </Col>
          </Row>
        )}

        {/* Recent Executions */}
        <Row>
          <Col>
            <Card>
              <Card.Header className="d-flex justify-content-between align-items-center">
                <h5 className="mb-0" data-testid="recent-executions-title">
                  Recent Executions
                </h5>
                <Badge bg="light" text="dark">
                  Last 10 executions
                </Badge>
              </Card.Header>
              <Card.Body className="p-0">
                {recentExecutions.length > 0 ? (
                  <Table responsive hover className="mb-0">
                    <thead className="bg-light">
                      <tr>
                        <th>Workflow</th>
                        <th>Status</th>
                        <th>Triggered By</th>
                        <th>Started</th>
                        <th>Duration</th>
                        <th>Current Step</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentExecutions.map(execution => (
                        <tr key={execution.id} data-testid={`execution-row-${execution.id}`}>
                          <td>
                            <div className="fw-semibold">{execution.workflow_name}</div>
                          </td>
                          <td>{getStatusBadge(execution.status)}</td>
                          <td>
                            <small className="text-muted">
                              {execution.triggered_by_name}
                            </small>
                          </td>
                          <td>
                            <small>{formatDate(execution.started_at)}</small>
                          </td>
                          <td>
                            <small>
                              {execution.duration_seconds 
                                ? formatDuration(execution.duration_seconds)
                                : execution.status === 'running' ? 'Running...' : 'N/A'
                              }
                            </small>
                          </td>
                          <td>
                            <small className="text-muted">
                              {execution.current_node_name || 'N/A'}
                            </small>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </Table>
                ) : (
                  <div className="text-center py-4">
                    <AlertTriangle size={32} className="text-muted mb-2" />
                    <p className="text-muted mb-0">No recent executions found</p>
                    <small className="text-muted">
                      Execute some workflows to see them here
                    </small>
                  </div>
                )}
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Quick Actions */}
        <Row className="mt-4">
          <Col>
            <Card className="bg-light border-0">
              <Card.Body className="text-center py-3">
                <div className="d-flex justify-content-center gap-3">
                  <Button 
                    variant="primary"
                    onClick={() => window.location.href = '/workflows'}
                    data-testid="manage-workflows-btn"
                  >
                    <Activity size={16} className="me-1" />
                    Manage Workflows
                  </Button>
                  <Button 
                    variant="outline-primary"
                    onClick={() => window.location.href = '/workflows/builder'}
                    data-testid="create-workflow-btn"
                  >
                    <Play size={16} className="me-1" />
                    Create New Workflow
                  </Button>
                </div>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      </Container>
      
      <style jsx>{`
        .spin {
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        
        .card {
          transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        .card:hover {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
        }
      `}</style>
    </>
  );
};

export default WorkflowDashboardPage;