import React from 'react';
import { Navbar, Nav, Container, Button, Dropdown } from 'react-bootstrap';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../services/auth/AuthContext';
import { 
  Building, LogOut, User, FileText, Workflow, BarChart3, Settings 
} from 'lucide-react';

const NavigationHeader = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const isActive = (path) => {
    return location.pathname.startsWith(path);
  };

  return (
    <Navbar bg="white" expand="lg" className="shadow-sm" data-testid="navigation-header">
      <Container>
        <Navbar.Brand 
          onClick={() => navigate('/dashboard')} 
          style={{ cursor: 'pointer' }}
          data-testid="brand-logo"
        >
          <Building size={24} className="text-primary me-2" />
          <span className="fw-bold text-dark">SMB Automation</span>
        </Navbar.Brand>

        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link 
              onClick={() => navigate('/dashboard')}
              className={isActive('/dashboard') ? 'fw-bold text-primary' : ''}
              data-testid="nav-dashboard"
            >
              <BarChart3 size={16} className="me-1" />
              Dashboard
            </Nav.Link>
            
            <Nav.Link 
              onClick={() => navigate('/documents/processing')}
              className={isActive('/documents') ? 'fw-bold text-primary' : ''}
              data-testid="nav-documents"
            >
              <FileText size={16} className="me-1" />
              Documents
            </Nav.Link>
            
            <Nav.Link 
              onClick={() => navigate('/workflows')}
              className={isActive('/workflows') ? 'fw-bold text-primary' : ''}
              data-testid="nav-workflows"
            >
              <Workflow size={16} className="me-1" />
              Workflows
            </Nav.Link>
          </Nav>

          <Nav>
            <Dropdown align="end">
              <Dropdown.Toggle 
                variant="outline-primary" 
                id="user-dropdown"
                size="sm"
                data-testid="user-dropdown"
              >
                <User size={16} className="me-1" />
                {user?.full_name || user?.username}
              </Dropdown.Toggle>

              <Dropdown.Menu>
                <Dropdown.Item 
                  onClick={() => navigate('/profile')}
                  data-testid="dropdown-profile"
                >
                  <User size={14} className="me-2" />
                  Profile
                </Dropdown.Item>
                <Dropdown.Item 
                  onClick={() => navigate('/settings')}
                  data-testid="dropdown-settings"
                >
                  <Settings size={14} className="me-2" />
                  Settings
                </Dropdown.Item>
                <Dropdown.Divider />
                <Dropdown.Item 
                  onClick={handleLogout}
                  className="text-danger"
                  data-testid="dropdown-logout"
                >
                  <LogOut size={14} className="me-2" />
                  Logout
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};

export default NavigationHeader;