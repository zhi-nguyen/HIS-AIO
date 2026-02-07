import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

/**
 * API Configuration
 * Cấu hình Axios client với JWT authentication
 * Backend sử dụng email làm USERNAME_FIELD
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

// Tạo Axios instance
export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 30000, // 30 seconds
});

// Token storage keys
const ACCESS_TOKEN_KEY = 'his_access_token';
const REFRESH_TOKEN_KEY = 'his_refresh_token';

// Token utilities
export const tokenUtils = {
    getAccessToken: (): string | null => {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem(ACCESS_TOKEN_KEY);
    },

    getRefreshToken: (): string | null => {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem(REFRESH_TOKEN_KEY);
    },

    setTokens: (access: string, refresh: string): void => {
        localStorage.setItem(ACCESS_TOKEN_KEY, access);
        localStorage.setItem(REFRESH_TOKEN_KEY, refresh);
    },

    clearTokens: (): void => {
        localStorage.removeItem(ACCESS_TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
    },
};

// Request interceptor - Thêm JWT token vào mỗi request
api.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
        const token = tokenUtils.getAccessToken();
        if (token && config.headers) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Response interceptor - Xử lý token refresh
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        // Nếu 401 và chưa thử refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
            originalRequest._retry = true;

            try {
                const refreshToken = tokenUtils.getRefreshToken();
                if (!refreshToken) {
                    throw new Error('No refresh token');
                }

                // Gọi API refresh token
                const response = await axios.post(`${API_BASE_URL}/token/refresh/`, {
                    refresh: refreshToken,
                });

                const { access } = response.data;
                tokenUtils.setTokens(access, refreshToken);

                // Retry request gốc với token mới
                if (originalRequest.headers) {
                    originalRequest.headers.Authorization = `Bearer ${access}`;
                }
                return api(originalRequest);
            } catch (refreshError) {
                // Refresh thất bại -> Logout
                tokenUtils.clearTokens();
                if (typeof window !== 'undefined') {
                    window.location.href = '/login';
                }
                return Promise.reject(refreshError);
            }
        }

        return Promise.reject(error);
    }
);

/**
 * Decode JWT payload
 * JWT format: header.payload.signature
 */
interface JWTPayload {
    user_id: string;
    email?: string;
    exp: number;
    iat: number;
    jti?: string;
    token_type?: string;
}

function decodeJWT(token: string): JWTPayload | null {
    try {
        const base64Url = token.split('.')[1];
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            atob(base64)
                .split('')
                .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(jsonPayload);
    } catch {
        return null;
    }
}

// API functions
export const authApi = {
    /**
     * Login với email và password
     * Backend sử dụng rest_framework_simplejwt
     * Request: { email: string, password: string }
     * Response: { access: string, refresh: string }
     */
    login: async (email: string, password: string) => {
        const response = await api.post('/token/', { email, password });
        const { access, refresh } = response.data;
        tokenUtils.setTokens(access, refresh);
        return response.data;
    },

    logout: () => {
        tokenUtils.clearTokens();
    },

    /**
     * Lấy thông tin user từ JWT token
     * Không cần gọi API vì đã có trong token
     */
    getMe: async (): Promise<JWTPayload | null> => {
        const token = tokenUtils.getAccessToken();
        if (!token) return null;

        const payload = decodeJWT(token);
        if (!payload) return null;

        // Kiểm tra token hết hạn
        const now = Date.now() / 1000;
        if (payload.exp && payload.exp < now) {
            tokenUtils.clearTokens();
            return null;
        }

        return payload;
    },
};

export default api;
