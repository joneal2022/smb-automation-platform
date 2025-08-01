import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../services/auth/AuthContext';
import { Spinner, Container } from 'react-bootstrap';

const ProtectedRoute = ({ children, requiredRole = null, requiredFeature = null }) => {
  const { isAuthenticated, isLoading, hasRole, canAccessFeature } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <Container className="d-flex justify-content-center align-items-center min-vh-100">
        <div className="text-center">
          <Spinner animation="border" variant="primary" />
          <p className="mt-2 text-muted">Loading...</p>
        </div>
      </Container>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access
  if (requiredRole && !hasRole(requiredRole)) {
    return (
      <Container className="d-flex justify-content-center align-items-center min-vh-100">
        <div className="text-center">
          <h3 className="text-danger">Access Denied</h3>
          <p className="text-muted">You don't have permission to access this page.</p>
        </div>
      </Container>
    );
  }

  // Check feature-based access
  if (requiredFeature && !canAccessFeature(requiredFeature)) {
    return (
      <Container className="d-flex justify-content-center align-items-center min-vh-100">
        <div className="text-center">
          <h3 className="text-warning">Feature Not Available</h3>
          <p className="text-muted">This feature is not available for your role.</p>
        </div>
      </Container>
    );
  }

  return children;
};

export default ProtectedRoute;