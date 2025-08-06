import React from 'react';
import { Container, Row, Col, Card, Button } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth/AuthContext';
import NavigationHeader from '../../components/organisms/NavigationHeader';
import { 
  User, Building, LogOut, Settings, 
  FileText, Workflow, BarChart3, MessageSquare 
} from 'lucide-react';

const DashboardPage = () => {
  const { user, logout, hasRole, canAccessFeature } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
  };

  const navigateToDocuments = () => {
    navigate('/documents/processing');
  };

  const navigateToWorkflows = () => {
    navigate('/workflows');
  };

  const navigateToAnalytics = () => {
    navigate('/analytics');
  };

  const getRoleDisplayName = () => {
    const roleMap = {
      'business_owner': 'Business Owner/Manager',
      'operations_staff': 'Operations Staff',
      'document_processor': 'Document Processing Staff',
      'it_admin': 'IT Administrator',
      'customer_service': 'Customer Service Staff',
    };
    return roleMap[user?.role] || user?.role;
  };

  const getDashboardContent = () => {
    if (hasRole('business_owner')) {
      return (
        <Row className="g-4">
          <Col md={6} lg={3}>
            <Card className="h-100 border-primary" data-testid="executive-analytics-card">
              <Card.Body className="text-center">
                <BarChart3 size={48} className="text-primary mb-3" />
                <Card.Title>Analytics Dashboard</Card.Title>
                <Card.Text>View ROI and performance metrics</Card.Text>
                <Button variant="primary" size="sm" onClick={navigateToAnalytics}>View Analytics</Button>
              </Card.Body>
            </Card>
          </Col>
          <Col md={6} lg={3}>
            <Card className="h-100 border-success" data-testid="financial-reports-card">
              <Card.Body className="text-center">
                <FileText size={48} className="text-success mb-3" />
                <Card.Title>Financial Reports</Card.Title>
                <Card.Text>Cost savings and efficiency reports</Card.Text>
                <Button variant="success" size="sm">View Reports</Button>
              </Card.Body>
            </Card>
          </Col>
          <Col md={6} lg={3}>
            <Card className="h-100 border-info" data-testid="user-management-card">
              <Card.Body className="text-center">
                <User size={48} className="text-info mb-3" />
                <Card.Title>User Management</Card.Title>
                <Card.Text>Manage team members and roles</Card.Text>
                <Button variant="info" size="sm">Manage Users</Button>
              </Card.Body>
            </Card>
          </Col>
          <Col md={6} lg={3}>
            <Card className="h-100 border-warning" data-testid="organization-settings-card">
              <Card.Body className="text-center">
                <Settings size={48} className="text-warning mb-3" />
                <Card.Title>Settings</Card.Title>
                <Card.Text>Organization and billing settings</Card.Text>
                <Button variant="warning" size="sm">Settings</Button>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      );
    }

    if (hasRole('operations_staff')) {
      return (
        <Row className="g-4">
          <Col md={6} lg={4}>
            <Card className="h-100 border-primary" data-testid="workflow-builder-card">
              <Card.Body className="text-center">
                <Workflow size={48} className="text-primary mb-3" />
                <Card.Title>Workflow Builder</Card.Title>
                <Card.Text>Create and manage automation workflows</Card.Text>
                <Button variant="primary" size="sm" onClick={navigateToWorkflows}>Build Workflows</Button>
              </Card.Body>
            </Card>
          </Col>
          <Col md={6} lg={4}>
            <Card className="h-100 border-success" data-testid="document-processing-card">
              <Card.Body className="text-center">
                <FileText size={48} className="text-success mb-3" />
                <Card.Title>Document Processing</Card.Title>
                <Card.Text>Monitor document automation</Card.Text>
                <Button variant="success" size="sm" onClick={navigateToDocuments}>View Documents</Button>
              </Card.Body>
            </Card>
          </Col>
          <Col md={6} lg={4}>
            <Card className="h-100 border-info" data-testid="integrations-card">
              <Card.Body className="text-center">
                <Settings size={48} className="text-info mb-3" />
                <Card.Title>Integrations</Card.Title>
                <Card.Text>Manage CRM and tool connections</Card.Text>
                <Button variant="info" size="sm">Manage Integrations</Button>
              </Card.Body>
            </Card>
          </Col>
        </Row>
      );
    }

    // Default dashboard for other roles
    return (
      <Row className="g-4">
        <Col md={6}>
          <Card className="h-100" data-testid="role-specific-card">
            <Card.Body className="text-center">
              <User size={48} className="text-primary mb-3" />
              <Card.Title>Welcome to SMB Automation</Card.Title>
              <Card.Text>
                Your role-specific dashboard is being prepared. 
                Contact your administrator for access to additional features.
              </Card.Text>
            </Card.Body>
          </Card>
        </Col>
        <Col md={6}>
          <Card className="h-100" data-testid="help-card">
            <Card.Body className="text-center">
              <MessageSquare size={48} className="text-info mb-3" />
              <Card.Title>Need Help?</Card.Title>
              <Card.Text>
                Check out our documentation or contact support for assistance.
              </Card.Text>
              <Button variant="info" size="sm">Get Help</Button>
            </Card.Body>
          </Card>
        </Col>
      </Row>
    );
  };

  return (
    <div className="min-vh-100 bg-light">
      {/* Navigation Header */}
      <NavigationHeader />

      {/* Main Content */}
      <Container className="py-4">
        {/* Welcome Banner */}
        <Row className="mb-4">
          <Col>
            <Card className="bg-primary text-white border-0" data-testid="welcome-banner">
              <Card.Body>
                <Row className="align-items-center">
                  <Col>
                    <h3 className="mb-1">
                      Welcome back, {user?.first_name || user?.username}! 👋
                    </h3>
                    <p className="mb-0 text-light">
                      Organization: <strong>{user?.organization?.name}</strong>
                    </p>
                    <p className="mb-0 text-light">
                      Role: <strong>{getRoleDisplayName()}</strong>
                    </p>
                  </Col>
                  <Col xs="auto" className="d-none d-lg-block">
                    <div className="text-center">
                      <User size={64} className="text-white opacity-75" />
                    </div>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Role-specific Dashboard Content */}
        {getDashboardContent()}

        {/* Quick Stats Row */}
        <Row className="mt-4">
          <Col>
            <Card data-testid="quick-stats-card">
              <Card.Header>
                <h5 className="mb-0">Quick Stats</h5>
              </Card.Header>
              <Card.Body>
                <Row className="text-center">
                  <Col md={3}>
                    <div className="border-end">
                      <h4 className="text-primary mb-1">0</h4>
                      <small className="text-muted">Active Workflows</small>
                    </div>
                  </Col>
                  <Col md={3}>
                    <div className="border-end">
                      <h4 className="text-success mb-1">0</h4>
                      <small className="text-muted">Documents Processed</small>
                    </div>
                  </Col>
                  <Col md={3}>
                    <div className="border-end">
                      <h4 className="text-info mb-1">0</h4>
                      <small className="text-muted">Integrations</small>
                    </div>
                  </Col>
                  <Col md={3}>
                    <div>
                      <h4 className="text-warning mb-1">0%</h4>
                      <small className="text-muted">Time Saved</small>
                    </div>
                  </Col>
                </Row>
              </Card.Body>
            </Card>
          </Col>
        </Row>

        {/* Footer */}
        <Row className="mt-5">
          <Col className="text-center">
            <small className="text-muted">
              SMB Automation Platform • Powered by AI • Secured by Enterprise-Grade Encryption
            </small>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default DashboardPage;