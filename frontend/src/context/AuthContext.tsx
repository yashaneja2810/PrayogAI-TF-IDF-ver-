import React, { createContext, useContext, useState } from 'react';
import { login as apiLogin } from '../lib/api';

interface User {
  id: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(() => {
    // Synchronously restore auth state from sessionStorage on initial render
    // to prevent ProtectedRoute from redirecting before useEffect runs
    const token = sessionStorage.getItem('token');
    const storedUser = sessionStorage.getItem('user');

    if (!token || !storedUser) {
      sessionStorage.clear();
      return null;
    }

    try {
      const parsedUser = JSON.parse(storedUser);
      if (!parsedUser.id || !parsedUser.email) {
        throw new Error('Invalid user data');
      }
      return parsedUser;
    } catch {
      sessionStorage.clear();
      return null;
    }
  });

  const login = async (email: string, password: string) => {
    try {
      // Clear any existing session data first
      sessionStorage.clear();
      setUser(null);

      const response = await apiLogin(email, password);

      // Only set new session data if we have valid response data
      if (response.access_token && response.user) {
        sessionStorage.setItem('token', response.access_token);
        sessionStorage.setItem('user', JSON.stringify(response.user));
        setUser(response.user);
      } else {
        throw new Error('Invalid login response');
      }
    } catch (error) {
      sessionStorage.clear();
      setUser(null);
      throw error;
    }
  };

  const logout = async () => {
    try {
      // Clear frontend state first
      sessionStorage.clear();
      setUser(null);

      // Force reload to clear any in-memory state
      window.location.href = '/login';
    } catch (error) {
      // Ensure we clear state even if API call fails
      sessionStorage.clear();
      setUser(null);
      window.location.href = '/login';
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};
