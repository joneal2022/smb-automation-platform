import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './services/auth/AuthContext';
import ProtectedRoute from './components/atoms/ProtectedRoute';

// Pages
import LoginPage from './pages/auth/LoginPage';
import RegisterPage from './pages/auth/RegisterPage';
import DashboardPage from './pages/dashboard/DashboardPage';

// Import Bootstrap CSS is already handled in main.jsx
import './App.css';

function App() {
  return (
    <AuthProvider>
      <div className="App">
        <Routes>
          {/* Public Routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          
          {/* Protected Routes */}
          <Route 
            path="/dashboard" 
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            } 
          />
          
          {/* Role-specific Protected Routes (examples for future implementation) */}
          <Route 
            path="/workflows/*" 
            element={
              <ProtectedRoute requiredFeature="workflow_builder">
                <div className="p-4 text-center">
                  <h3>Workflow Builder</h3>
                  <p>Coming soon...</p>
                </div>
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/documents/*" 
            element={
              <ProtectedRoute requiredFeature="document_processing">
                <div className="p-4 text-center">
                  <h3>Document Processing</h3>
                  <p>Coming soon...</p>
                </div>
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/analytics/*" 
            element={
              <ProtectedRoute requiredFeature="analytics_full">
                <div className="p-4 text-center">
                  <h3>Analytics Dashboard</h3>
                  <p>Coming soon...</p>
                </div>
              </ProtectedRoute>
            } 
          />
          
          <Route 
            path="/admin/*" 
            element={
              <ProtectedRoute requiredRole="it_admin">
                <div className="p-4 text-center">
                  <h3>Admin Panel</h3>
                  <p>Coming soon...</p>
                </div>
              </ProtectedRoute>
            } 
          />
          
          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          
          {/* 404 catch-all */}
          <Route 
            path="*" 
            element={
              <div className="min-vh-100 d-flex align-items-center justify-content-center bg-light">
                <div className="text-center">
                  <h1 className="display-1 text-muted">404</h1>
                  <h3 className="text-dark mb-3">Page Not Found</h3>
                  <p className="text-muted mb-4">
                    The page you're looking for doesn't exist.
                  </p>
                  <a href="/dashboard" className="btn btn-primary">
                    Go to Dashboard
                  </a>
                </div>
              </div>
            } 
          />
        </Routes>
      </div>
    </AuthProvider>
  );
}

export default App;
