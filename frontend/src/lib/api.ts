import axios, { AxiosError } from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor for authentication
api.interceptors.request.use((config) => {
    // Get fresh token on every request to ensure we have the latest state
    const token = sessionStorage.getItem('token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    } else {
        // If no token found, ensure any old Authorization header is removed
        delete config.headers.Authorization;
    }
    return config;
});

// Add a response interceptor to handle auth errors and token expiration
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        if (error.response?.status === 401 || error.response?.status === 403) {
            // Clear all auth-related data
            sessionStorage.clear(); // Clear all session data to ensure clean state
            
            // Force a clean reload to reset all app state if not already on login page
            if (window.location.pathname !== '/login') {
                window.location.href = '/login';
                return Promise.reject(new Error('Session expired. Please login again.'));
            }
        }
        return Promise.reject(error);
    }
);

export interface LoginResponse {
    access_token: string;
    user: {
        id: string;
        email: string;
    };
}

export const login = async (email: string, password: string): Promise<LoginResponse> => {
    try {
        // Clear any existing session data first
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user');
        
        const response = await api.post<LoginResponse>('/auth/login', { email, password });
        if (response.data.access_token) {
            sessionStorage.setItem('token', response.data.access_token);
            if (response.data.user) {
                sessionStorage.setItem('user', JSON.stringify(response.data.user));
            }
        }
        return response.data;
    } catch (error) {
        // Make sure no stale data remains on failed login
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user');
        throw error;
    }
};

export const logout = async () => {
    try {
        // Clear session storage first in case the request fails
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user');
        
        // Attempt to notify the backend
        await api.post('/auth/logout');
    } catch (error) {
        // Even if the backend call fails, we want to ensure the client is logged out
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user');
        throw error;
    } finally {
        // Force reload all instances to reset client state
        window.location.href = '/login';
    }
};

export interface SignUpResponse {
    message: string;
    user: {
        id: string;
        email: string;
    };
}

export const signup = async (email: string, password: string): Promise<SignUpResponse> => {
    try {
        const response = await api.post<SignUpResponse>('/auth/register', { email, password });
        return response.data;
    } catch (error) {
        throw error;
    }
};
