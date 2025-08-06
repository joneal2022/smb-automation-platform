import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refreshToken');
        if (refreshToken) {
          const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
            refresh: refreshToken,
          });

          const { access } = response.data;
          localStorage.setItem('accessToken', access);

          // Retry the original request with new token
          originalRequest.headers.Authorization = `Bearer ${access}`;
          return apiClient(originalRequest);
        }
      } catch (refreshError) {
        // Refresh failed, redirect to login
        authService.logout();
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

class AuthService {
  async login(credentials) {
    try {
      const response = await apiClient.post('/auth/login/', credentials);
      const { access, refresh, user } = response.data;
      
      // Store tokens
      localStorage.setItem('accessToken', access);
      localStorage.setItem('refreshToken', refresh);
      localStorage.setItem('user', JSON.stringify(user));
      
      return { success: true, user };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Login failed',
      };
    }
  }

  async register(userData) {
    try {
      const response = await apiClient.post('/auth/register/', userData);
      return { success: true, data: response.data };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Registration failed',
      };
    }
  }

  async logout() {
    try {
      const refreshToken = localStorage.getItem('refreshToken');
      if (refreshToken) {
        await apiClient.post('/auth/logout/', { refresh: refreshToken });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Clear local storage regardless of API call success
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      localStorage.removeItem('user');
    }
  }

  async getCurrentUser() {
    try {
      const response = await apiClient.get('/auth/me/');
      const user = response.data;
      localStorage.setItem('user', JSON.stringify(user));
      return { success: true, user };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Failed to get user info',
      };
    }
  }

  async updateProfile(profileData) {
    try {
      const response = await apiClient.patch('/auth/me/', profileData);
      const user = response.data;
      localStorage.setItem('user', JSON.stringify(user));
      return { success: true, user };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Profile update failed',
      };
    }
  }

  async changePassword(passwordData) {
    try {
      await apiClient.post('/auth/change-password/', passwordData);
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Password change failed',
      };
    }
  }

  async requestPasswordReset(email) {
    try {
      await apiClient.post('/auth/password-reset/', { email });
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.detail || 'Password reset request failed',
      };
    }
  }

  async resetPassword(token, newPassword) {
    try {
      await apiClient.post('/auth/password-reset-confirm/', {
        token,
        password: newPassword,
      });
      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data || 'Password reset failed',
      };
    }
  }

  isAuthenticated() {
    const token = localStorage.getItem('accessToken');
    const user = localStorage.getItem('user');
    return !!(token && user);
  }

  getUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  }

  hasRole(role) {
    const user = this.getUser();
    return user?.role === role;
  }

  canAccessFeature(feature) {
    const user = this.getUser();
    if (!user) return false;

    const featurePermissions = {
      'business_owner': [
        'dashboard_executive', 'analytics_full', 'reports_financial', 
        'user_management', 'organization_settings', 'billing',
        'document_processing', 'workflow_builder', 'workflow_management'
      ],
      'operations_staff': [
        'dashboard_operations', 'workflow_builder', 'workflow_management',
        'integration_management', 'document_processing', 'analytics_operational'
      ],
      'document_processor': [
        'dashboard_documents', 'document_upload', 'document_review',
        'data_extraction', 'batch_processing', 'quality_control'
      ],
      'it_admin': [
        'dashboard_admin', 'user_management', 'system_monitoring',
        'security_logs', 'integration_config', 'backup_management'
      ],
      'customer_service': [
        'dashboard_service', 'chatbot_management', 'customer_history',
        'escalation_management', 'response_templates'
      ],
    };

    const userPermissions = featurePermissions[user.role] || [];
    return userPermissions.includes(feature);
  }

  getAuthHeader() {
    const token = localStorage.getItem('accessToken');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
}

const authService = new AuthService();
export default authService;