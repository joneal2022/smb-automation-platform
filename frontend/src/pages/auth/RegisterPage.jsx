import React, { useState, useEffect } from 'react';
import { Container, Row, Col, Card, Form, Button, Alert, Spinner, ProgressBar } from 'react-bootstrap';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../services/auth/AuthContext';
import { 
  Eye, EyeOff, Shield, Lock, Mail, User, Phone, 
  Building, Briefcase, CheckCircle 
} from 'lucide-react';

const RegisterPage = () => {
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState({
    // Step 1: Account Info
    username: '',
    email: '',
    password: '',
    password_confirm: '',
    
    // Step 2: Personal Info
    first_name: '',
    last_name: '',
    phone_number: '',
    
    // Step 3: Organization Info
    organization_name: '',
    job_title: '',
    department: '',
    role: 'operations_staff',
    
    // Step 4: Compliance
    gdpr_consent: false,
    data_processing_consent: false,
  });
  
  const [showPassword, setShowPassword] = useState(false);
  const [showPasswordConfirm, setShowPasswordConfirm] = useState(false);
  const [passwordStrength, setPasswordStrength] = useState(0);
  const [fieldErrors, setFieldErrors] = useState({});

  const { register, registerLoading, error, clearError, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    clearError();
  }, [clearError]);

  const calculatePasswordStrength = (password) => {
    let score = 0;
    if (password.length >= 8) score += 25;
    if (password.match(/[a-z]/)) score += 25;
    if (password.match(/[A-Z]/)) score += 25;
    if (password.match(/[0-9]/) || password.match(/[^A-Za-z0-9]/)) score += 25;
    return score;
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    const newValue = type === 'checkbox' ? checked : value;
    
    setFormData(prev => ({
      ...prev,
      [name]: newValue,
    }));

    // Calculate password strength
    if (name === 'password') {
      setPasswordStrength(calculatePasswordStrength(value));
    }

    // Clear field error when user starts typing
    if (fieldErrors[name]) {
      setFieldErrors(prev => ({ ...prev, [name]: null }));
    }

    // Clear general error
    if (error) {
      clearError();
    }
  };

  const validateStep = (step) => {
    const errors = {};
    
    switch (step) {
      case 1:
        if (!formData.username.trim()) errors.username = 'Username is required';
        if (!formData.email.trim()) errors.email = 'Email is required';
        if (!formData.password) errors.password = 'Password is required';
        if (formData.password !== formData.password_confirm) {
          errors.password_confirm = 'Passwords do not match';
        }
        if (passwordStrength < 50) {
          errors.password = 'Password is too weak';
        }
        break;
        
      case 2:
        if (!formData.first_name.trim()) errors.first_name = 'First name is required';
        if (!formData.last_name.trim()) errors.last_name = 'Last name is required';
        break;
        
      case 3:
        if (!formData.organization_name.trim()) errors.organization_name = 'Organization name is required';
        if (!formData.role) errors.role = 'Role is required';
        break;
        
      case 4:
        if (!formData.gdpr_consent) errors.gdpr_consent = 'GDPR consent is required';
        if (!formData.data_processing_consent) errors.data_processing_consent = 'Data processing consent is required';
        break;
    }
    
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrevious = () => {
    setCurrentStep(prev => prev - 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateStep(4)) return;

    const result = await register(formData);
    
    if (result.success) {
      navigate('/login', { 
        state: { 
          message: 'Registration successful! Please sign in to continue.' 
        }
      });
    }
  };

  const getPasswordStrengthColor = () => {
    if (passwordStrength < 25) return 'danger';
    if (passwordStrength < 50) return 'warning';
    if (passwordStrength < 75) return 'info';
    return 'success';
  };

  const getPasswordStrengthText = () => {
    if (passwordStrength < 25) return 'Weak';
    if (passwordStrength < 50) return 'Fair';
    if (passwordStrength < 75) return 'Good';
    return 'Strong';
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <div data-testid="registration-step-1">
            <div className="text-center mb-4">
              <h4 className="text-dark mb-2">Create Account</h4>
              <p className="text-muted">Set up your login credentials</p>
            </div>

            <Form.Group className="mb-3">
              <Form.Label className="text-dark fw-medium">
                <User size={16} className="me-2" />
                Username
              </Form.Label>
              <Form.Control
                type="text"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                placeholder="Choose a unique username"
                required
                isInvalid={!!fieldErrors.username}
                data-testid="username-input"
              />
              <Form.Control.Feedback type="invalid">
                {fieldErrors.username}
              </Form.Control.Feedback>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label className="text-dark fw-medium">
                <Mail size={16} className="me-2" />
                Email Address
              </Form.Label>
              <Form.Control
                type="email"
                name="email"
                value={formData.email}
                onChange={handleInputChange}
                placeholder="Enter your business email"
                required
                isInvalid={!!fieldErrors.email}
                data-testid="email-input"
              />
              <Form.Control.Feedback type="invalid">
                {fieldErrors.email}
              </Form.Control.Feedback>
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
                  placeholder="Create a strong password"
                  required
                  isInvalid={!!fieldErrors.password}
                  data-testid="password-input"
                  className="pe-5"
                />
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => setShowPassword(!showPassword)}
                  className="position-absolute top-50 end-0 translate-middle-y pe-3 text-muted"
                  style={{ border: 'none', background: 'none' }}
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </Button>
              </div>
              {formData.password && (
                <div className="mt-2">
                  <ProgressBar 
                    now={passwordStrength} 
                    variant={getPasswordStrengthColor()}
                    style={{ height: '4px' }}
                  />
                  <small className={`text-${getPasswordStrengthColor()}`}>
                    Password strength: {getPasswordStrengthText()}
                  </small>
                </div>
              )}
              <Form.Control.Feedback type="invalid">
                {fieldErrors.password}
              </Form.Control.Feedback>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label className="text-dark fw-medium">
                <Lock size={16} className="me-2" />
                Confirm Password
              </Form.Label>
              <div className="position-relative">
                <Form.Control
                  type={showPasswordConfirm ? 'text' : 'password'}
                  name="password_confirm"
                  value={formData.password_confirm}
                  onChange={handleInputChange}
                  placeholder="Confirm your password"
                  required
                  isInvalid={!!fieldErrors.password_confirm}
                  data-testid="password-confirm-input"
                  className="pe-5"
                />
                <Button
                  variant="link"
                  size="sm"
                  onClick={() => setShowPasswordConfirm(!showPasswordConfirm)}
                  className="position-absolute top-50 end-0 translate-middle-y pe-3 text-muted"
                  style={{ border: 'none', background: 'none' }}
                  tabIndex={-1}
                >
                  {showPasswordConfirm ? <EyeOff size={16} /> : <Eye size={16} />}
                </Button>
              </div>
              <Form.Control.Feedback type="invalid">
                {fieldErrors.password_confirm}
              </Form.Control.Feedback>
            </Form.Group>
          </div>
        );

      case 2:
        return (
          <div data-testid="registration-step-2">
            <div className="text-center mb-4">
              <h4 className="text-dark mb-2">Personal Information</h4>
              <p className="text-muted">Tell us about yourself</p>
            </div>

            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label className="text-dark fw-medium">First Name</Form.Label>
                  <Form.Control
                    type="text"
                    name="first_name"
                    value={formData.first_name}
                    onChange={handleInputChange}
                    placeholder="Enter your first name"
                    required
                    isInvalid={!!fieldErrors.first_name}
                    data-testid="first-name-input"
                  />
                  <Form.Control.Feedback type="invalid">
                    {fieldErrors.first_name}
                  </Form.Control.Feedback>
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label className="text-dark fw-medium">Last Name</Form.Label>
                  <Form.Control
                    type="text"
                    name="last_name"
                    value={formData.last_name}
                    onChange={handleInputChange}
                    placeholder="Enter your last name"
                    required
                    isInvalid={!!fieldErrors.last_name}
                    data-testid="last-name-input"
                  />
                  <Form.Control.Feedback type="invalid">
                    {fieldErrors.last_name}
                  </Form.Control.Feedback>
                </Form.Group>
              </Col>
            </Row>

            <Form.Group className="mb-3">
              <Form.Label className="text-dark fw-medium">
                <Phone size={16} className="me-2" />
                Phone Number (Optional)
              </Form.Label>
              <Form.Control
                type="tel"
                name="phone_number"
                value={formData.phone_number}
                onChange={handleInputChange}
                placeholder="Enter your phone number"
                data-testid="phone-input"
              />
            </Form.Group>
          </div>
        );

      case 3:
        return (
          <div data-testid="registration-step-3">
            <div className="text-center mb-4">
              <h4 className="text-dark mb-2">Organization Details</h4>
              <p className="text-muted">Information about your workplace</p>
            </div>

            <Form.Group className="mb-3">
              <Form.Label className="text-dark fw-medium">
                <Building size={16} className="me-2" />
                Organization Name
              </Form.Label>
              <Form.Control
                type="text"
                name="organization_name"
                value={formData.organization_name}
                onChange={handleInputChange}
                placeholder="Enter your company name"
                required
                isInvalid={!!fieldErrors.organization_name}
                data-testid="organization-name-input"
              />
              <Form.Control.Feedback type="invalid">
                {fieldErrors.organization_name}
              </Form.Control.Feedback>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label className="text-dark fw-medium">
                <Briefcase size={16} className="me-2" />
                Your Role
              </Form.Label>
              <Form.Select
                name="role"
                value={formData.role}
                onChange={handleInputChange}
                required
                isInvalid={!!fieldErrors.role}
                data-testid="role-select"
              >
                <option value="business_owner">Business Owner/Manager</option>
                <option value="operations_staff">Operations Staff</option>
                <option value="document_processor">Document Processing Staff</option>
                <option value="it_admin">IT Administrator</option>
                <option value="customer_service">Customer Service Staff</option>
              </Form.Select>
              <Form.Control.Feedback type="invalid">
                {fieldErrors.role}
              </Form.Control.Feedback>
            </Form.Group>

            <Row>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label className="text-dark fw-medium">Job Title (Optional)</Form.Label>
                  <Form.Control
                    type="text"
                    name="job_title"
                    value={formData.job_title}
                    onChange={handleInputChange}
                    placeholder="e.g., Operations Manager"
                    data-testid="job-title-input"
                  />
                </Form.Group>
              </Col>
              <Col md={6}>
                <Form.Group className="mb-3">
                  <Form.Label className="text-dark fw-medium">Department (Optional)</Form.Label>
                  <Form.Control
                    type="text"
                    name="department"
                    value={formData.department}
                    onChange={handleInputChange}
                    placeholder="e.g., Operations"
                    data-testid="department-input"
                  />
                </Form.Group>
              </Col>
            </Row>
          </div>
        );

      case 4:
        return (
          <div data-testid="registration-step-4">
            <div className="text-center mb-4">
              <h4 className="text-dark mb-2">Privacy & Compliance</h4>
              <p className="text-muted">Please review and accept our terms</p>
            </div>

            <Alert variant="info" className="mb-4">
              <Shield size={20} className="me-2" />
              <strong>Your Privacy Matters</strong>
              <p className="mb-0 mt-2">
                We are committed to protecting your data in compliance with GDPR and industry standards.
              </p>
            </Alert>

            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                id="gdpr-consent"
                name="gdpr_consent"
                checked={formData.gdpr_consent}
                onChange={handleInputChange}
                isInvalid={!!fieldErrors.gdpr_consent}
                required
                data-testid="gdpr-consent-checkbox"
                label={
                  <span>
                    I consent to the processing of my personal data in accordance with the{' '}
                    <Link to="/privacy-policy" target="_blank" className="text-primary">
                      Privacy Policy
                    </Link>
                  </span>
                }
              />
              <Form.Control.Feedback type="invalid">
                {fieldErrors.gdpr_consent}
              </Form.Control.Feedback>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Check
                type="checkbox"
                id="data-processing-consent"
                name="data_processing_consent"
                checked={formData.data_processing_consent}
                onChange={handleInputChange}
                isInvalid={!!fieldErrors.data_processing_consent}
                required
                data-testid="data-processing-consent-checkbox"
                label={
                  <span>
                    I agree to the processing of my data for service provision and improvement as outlined in our{' '}
                    <Link to="/terms-of-service" target="_blank" className="text-primary">
                      Terms of Service
                    </Link>
                  </span>
                }
              />
              <Form.Control.Feedback type="invalid">
                {fieldErrors.data_processing_consent}
              </Form.Control.Feedback>
            </Form.Group>

            <div className="bg-light p-3 rounded mb-3">
              <h6 className="text-dark mb-2">
                <CheckCircle size={16} className="me-2 text-success" />
                What this means:
              </h6>
              <ul className="small text-muted mb-0">
                <li>Your data will be encrypted and stored securely</li>
                <li>You can request data deletion at any time</li>
                <li>We'll only use your data to provide our services</li>
                <li>You can update your preferences in account settings</li>
              </ul>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="min-vh-100 d-flex align-items-center bg-light py-4">
      <Container>
        <Row className="justify-content-center">
          <Col md={8} lg={6} xl={5}>
            <Card className="shadow-sm border-0">
              <Card.Header className="bg-primary text-white text-center py-4">
                <div className="d-flex align-items-center justify-content-center mb-2">
                  <Shield size={32} className="me-2" />
                  <h3 className="mb-0">SMB Automation</h3>
                </div>
                <p className="mb-0 text-light">Join the Platform</p>
              </Card.Header>

              <Card.Body className="p-4">
                {/* Progress Indicator */}
                <div className="mb-4">
                  <div className="d-flex justify-content-between mb-2">
                    {[1, 2, 3, 4].map((step) => (
                      <div
                        key={step}
                        className={`d-flex align-items-center justify-content-center rounded-circle ${
                          step <= currentStep ? 'bg-primary text-white' : 'bg-light text-muted'
                        }`}
                        style={{ width: '30px', height: '30px', fontSize: '14px' }}
                      >
                        {step < currentStep ? <CheckCircle size={16} /> : step}
                      </div>
                    ))}
                  </div>
                  <ProgressBar 
                    now={(currentStep / 4) * 100} 
                    variant="primary" 
                    style={{ height: '4px' }} 
                  />
                </div>

                {error && (
                  <Alert 
                    variant="danger" 
                    dismissible 
                    onClose={clearError}
                    data-testid="register-error-alert"
                  >
                    <small>{typeof error === 'object' ? JSON.stringify(error) : error}</small>
                  </Alert>
                )}

                <Form onSubmit={handleSubmit} data-testid="registration-form">
                  {renderStepContent()}

                  <div className="d-flex justify-content-between mt-4">
                    <Button
                      variant="outline-secondary"
                      onClick={handlePrevious}
                      disabled={currentStep === 1}
                      data-testid="previous-step-button"
                    >
                      Previous
                    </Button>

                    {currentStep < 4 ? (
                      <Button
                        variant="primary"
                        onClick={handleNext}
                        data-testid="next-step-button"
                      >
                        Next
                      </Button>
                    ) : (
                      <Button
                        type="submit"
                        variant="success"
                        disabled={registerLoading}
                        data-testid="register-submit-button"
                      >
                        {registerLoading ? (
                          <>
                            <Spinner
                              as="span"
                              animation="border"
                              size="sm"
                              role="status"
                              aria-hidden="true"
                              className="me-2"
                            />
                            Creating Account...
                          </>
                        ) : (
                          'Create Account'
                        )}
                      </Button>
                    )}
                  </div>
                </Form>

                <hr className="my-4" />

                <div className="text-center">
                  <p className="text-muted mb-0">
                    Already have an account?{' '}
                    <Link 
                      to="/login" 
                      className="text-primary text-decoration-none fw-medium"
                      data-testid="sign-in-link"
                    >
                      Sign In
                    </Link>
                  </p>
                </div>
              </Card.Body>

              <Card.Footer className="bg-light text-center py-3">
                <small className="text-muted">
                  <Shield size={14} className="me-1" />
                  Your data is protected by enterprise-grade security
                </small>
              </Card.Footer>
            </Card>
          </Col>
        </Row>
      </Container>
    </div>
  );
};

export default RegisterPage;