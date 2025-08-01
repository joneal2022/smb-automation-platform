import React, { createContext, useContext, useReducer, useEffect } from 'react';
import authService from './authService';

// Auth Context
const AuthContext = createContext();

// Auth Actions
const AUTH_ACTIONS = {
  LOGIN_START: 'LOGIN_START',
  LOGIN_SUCCESS: 'LOGIN_SUCCESS',
  LOGIN_FAILURE: 'LOGIN_FAILURE',
  LOGOUT: 'LOGOUT',
  REGISTER_START: 'REGISTER_START',
  REGISTER_SUCCESS: 'REGISTER_SUCCESS',
  REGISTER_FAILURE: 'REGISTER_FAILURE',
  UPDATE_USER: 'UPDATE_USER',
  SET_LOADING: 'SET_LOADING',
  CLEAR_ERROR: 'CLEAR_ERROR',
};

// Initial State
const initialState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  error: null,
  loginLoading: false,
  registerLoading: false,
};

// Auth Reducer
function authReducer(state, action) {
  switch (action.type) {
    case AUTH_ACTIONS.LOGIN_START:
      return {
        ...state,
        loginLoading: true,
        error: null,
      };

    case AUTH_ACTIONS.LOGIN_SUCCESS:
      return {
        ...state,
        user: action.payload.user,
        isAuthenticated: true,
        loginLoading: false,
        error: null,
      };

    case AUTH_ACTIONS.LOGIN_FAILURE:
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        loginLoading: false,
        error: action.payload.error,
      };

    case AUTH_ACTIONS.REGISTER_START:
      return {
        ...state,
        registerLoading: true,
        error: null,
      };

    case AUTH_ACTIONS.REGISTER_SUCCESS:
      return {
        ...state,
        registerLoading: false,
        error: null,
      };

    case AUTH_ACTIONS.REGISTER_FAILURE:
      return {
        ...state,
        registerLoading: false,
        error: action.payload.error,
      };

    case AUTH_ACTIONS.LOGOUT:
      return {
        ...state,
        user: null,
        isAuthenticated: false,
        error: null,
      };

    case AUTH_ACTIONS.UPDATE_USER:
      return {
        ...state,
        user: action.payload.user,
      };

    case AUTH_ACTIONS.SET_LOADING:
      return {
        ...state,
        isLoading: action.payload.isLoading,
      };

    case AUTH_ACTIONS.CLEAR_ERROR:
      return {
        ...state,
        error: null,
      };

    default:
      return state;
  }
}

// Auth Provider Component
export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize authentication state
  useEffect(() => {
    const initializeAuth = async () => {
      dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: { isLoading: true } });

      if (authService.isAuthenticated()) {
        // Verify token is still valid
        const result = await authService.getCurrentUser();
        if (result.success) {
          dispatch({
            type: AUTH_ACTIONS.LOGIN_SUCCESS,
            payload: { user: result.user },
          });
        } else {
          // Token invalid, clear local storage
          authService.logout();
          dispatch({ type: AUTH_ACTIONS.LOGOUT });
        }
      }

      dispatch({ type: AUTH_ACTIONS.SET_LOADING, payload: { isLoading: false } });
    };

    initializeAuth();
  }, []);

  // Login function
  const login = async (credentials) => {
    dispatch({ type: AUTH_ACTIONS.LOGIN_START });

    const result = await authService.login(credentials);

    if (result.success) {
      dispatch({
        type: AUTH_ACTIONS.LOGIN_SUCCESS,
        payload: { user: result.user },
      });
      return { success: true };
    } else {
      dispatch({
        type: AUTH_ACTIONS.LOGIN_FAILURE,
        payload: { error: result.error },
      });
      return { success: false, error: result.error };
    }
  };

  // Register function
  const register = async (userData) => {
    dispatch({ type: AUTH_ACTIONS.REGISTER_START });

    const result = await authService.register(userData);

    if (result.success) {
      dispatch({ type: AUTH_ACTIONS.REGISTER_SUCCESS });
      return { success: true, data: result.data };
    } else {
      dispatch({
        type: AUTH_ACTIONS.REGISTER_FAILURE,
        payload: { error: result.error },
      });
      return { success: false, error: result.error };
    }
  };

  // Logout function
  const logout = async () => {
    await authService.logout();
    dispatch({ type: AUTH_ACTIONS.LOGOUT });
  };

  // Update user profile
  const updateUser = async (profileData) => {
    const result = await authService.updateProfile(profileData);

    if (result.success) {
      dispatch({
        type: AUTH_ACTIONS.UPDATE_USER,
        payload: { user: result.user },
      });
      return { success: true };
    } else {
      return { success: false, error: result.error };
    }
  };

  // Change password
  const changePassword = async (passwordData) => {
    return await authService.changePassword(passwordData);
  };

  // Request password reset
  const requestPasswordReset = async (email) => {
    return await authService.requestPasswordReset(email);
  };

  // Reset password
  const resetPassword = async (token, newPassword) => {
    return await authService.resetPassword(token, newPassword);
  };

  // Clear error
  const clearError = () => {
    dispatch({ type: AUTH_ACTIONS.CLEAR_ERROR });
  };

  // Check if user has specific role
  const hasRole = (role) => {
    return authService.hasRole(role);
  };

  // Check if user can access feature
  const canAccessFeature = (feature) => {
    return authService.canAccessFeature(feature);
  };

  const value = {
    // State
    user: state.user,
    isAuthenticated: state.isAuthenticated,
    isLoading: state.isLoading,
    error: state.error,
    loginLoading: state.loginLoading,
    registerLoading: state.registerLoading,

    // Actions
    login,
    register,
    logout,
    updateUser,
    changePassword,
    requestPasswordReset,
    resetPassword,
    clearError,
    hasRole,
    canAccessFeature,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// Custom hook to use auth context
export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;