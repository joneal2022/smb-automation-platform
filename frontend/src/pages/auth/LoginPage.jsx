import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert, Spinner } from 'react-bootstrap';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../services/auth/AuthContext';
import { Eye, EyeOff, Shield, Lock, Mail } from 'lucide-react';

const LoginPage = () => {
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);

  const { login, loginLoading, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const from = location.state?.from?.pathname || '/dashboard';

  useEffect(() => {
    if (isAuthenticated) {
      navigate(from, { replace: true });
    }
  }, [isAuthenticated, navigate, from]);

  useEffect(() => {
    // Clear any previous errors when component mounts
    clearError();
  }, []); // Remove clearError from dependency array to prevent infinite loop

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value,
    }));
    // Clear error when user starts typing
    if (error) {
      clearError();
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.username.trim() || !formData.password.trim()) {
      return;
    }

    // Let the AuthContext handle the login and state update
    // The useEffect with isAuthenticated will handle the redirect
    await login(formData);
  };

  const togglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  return (
    <div className="min-vh-100 d-flex align-items-center bg-light">
      <Container>
        <Row className="justify-content-center">
          <Col md={6} lg={5} xl={4}>
            <Card className="shadow-sm border-0">
              <Card.Header className="bg-primary text-white text-center py-4">
                <div className="d-flex align-items-center justify-content-center mb-2">
                  <Shield size={32} className="me-2" />
                  <h3 className="mb-0">SMB Automation</h3>
                </div>
                <p className="mb-0 text-light">Secure Business Platform</p>
              </Card.Header>
              
              <Card.Body className="p-4">
                <div className="text-center mb-4">
                  <h4 className="text-dark mb-2">Welcome Back</h4>
                  <p className="text-muted">Sign in to your account to continue</p>
                </div>

                {error && (
                  <Alert 
                    variant="danger" 
                    dismissible 
                    onClose={clearError}
                    data-testid="login-error-alert"
                  >
                    <small>{typeof error === 'string' ? error : 'Login failed. Please try again.'}</small>
                  </Alert>
                )}

                <Form onSubmit={handleSubmit} data-testid="login-form">
                  <Form.Group className="mb-3">
                    <Form.Label className="text-dark fw-medium">
                      <Mail size={16} className="me-2" />
                      Username or Email
                    </Form.Label>
                    <Form.Control
                      type="text"
                      name="username"
                      value={formData.username}
                      onChange={handleInputChange}
                      placeholder="Enter your username or email"
                      required
                      disabled={loginLoading}
                      data-testid="username-input"
                      className="py-2"
                    />
                  </Form.Group>

                  <Form.Group className="mb-3">
                    <Form.Label className="text-dark fw-medium">
                      <Lock size={16} className="me-2" />
                      Password
                    </Form.Label>
                    <div className="position-relative">
                      <Form.Control
                        type={showPassword ? 'text' : 'password'}
                        name="password"
                        value={formData.password}
                        onChange={handleInputChange}
                        placeholder="Enter your password"
                        required
                        disabled={loginLoading}
                        data-testid="password-input"
                        className="py-2 pe-5"
                      />
                      <Button
                        variant="link"
                        size="sm"
                        onClick={togglePasswordVisibility}
                        className="position-absolute top-50 end-0 translate-middle-y pe-3 text-muted"
                        style={{ border: 'none', background: 'none' }}
                        tabIndex={-1}
                        data-testid="toggle-password-visibility"
                      >
                        {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                      </Button>
                    </div>
                  </Form.Group>

                  <Row className="mb-3">
                    <Col>
                      <Form.Check
                        type="checkbox"
                        id="remember-me"
                        label="Remember me"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        disabled={loginLoading}
                        data-testid="remember-me-checkbox"
                      />
                    </Col>
                    <Col className="text-end">
                      <Link 
                        to="/forgot-password" 
                        className="text-primary text-decoration-none small"
                        data-testid="forgot-password-link"
                      >
                        Forgot password?
                      </Link>
                    </Col>
                  </Row>

                  <Button
                    type="submit"
                    variant="primary"
                    size="lg"
                    className="w-100 py-2 fw-medium"
                    disabled={loginLoading || !formData.username.trim() || !formData.password.trim()}
                    data-testid="login-submit-button"
                  >
                    {loginLoading ? (
                      <>
                        <Spinner
                          as="span"
                          animation="border"
                          size="sm"
                          role="status"
                          aria-hidden="true"
                          className="me-2"
                        />
                        Signing in...
                      </>
                    ) : (
                      'Sign In'
                    )}
                  </Button>
                </Form>

                <hr className="my-4" />

                <div className="text-center">
                  <p className="text-muted mb-0">
                    Don't have an account?{' '}
                    <Link 
                      to="/register" 
                      className="text-primary text-decoration-none fw-medium"
                      data-testid="create-account-link"
                    >
                      Create Account
                    </Link>
                  </p>
                </div>
              </Card.Body>

              <Card.Footer className="bg-light text-center py-3">
                <small className="text-muted">
                  <Shield size={14} className="me-1" />
                  Secured by enterprise-grade encryption
                </small>
              </Card.Footer>
            </Card>

            {/* Security Notice */}
            <div className="text-center mt-3">
              <small className="text-muted">
                By signing in, you agree to our{' '}
                <Link to="/privacy-policy" className="text-primary text-decoration-none">
                  Privacy Policy
                </Link>{' '}
                and{' '}
                <Link to="/terms-of-service" className="text-primary text-decoration-none">
                  Terms of Service
                </Link>
              </small>
            </div>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default LoginPage;