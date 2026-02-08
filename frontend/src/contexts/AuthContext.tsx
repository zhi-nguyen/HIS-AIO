'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { authApi, tokenUtils } from '@/lib/api';
import { message } from 'antd';

/**
 * Auth Context
 * Quản lý trạng thái đăng nhập của người dùng
 * Backend sử dụng email làm USERNAME_FIELD
 */

interface StaffProfile {
    id: string;
    role: string;
    department?: string;
}

interface User {
    user_id: string;
    email?: string;
    exp: number;
    iat: number;
    staff_profile?: StaffProfile;
}

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    loading: boolean; // alias for isLoading
    isAuthenticated: boolean;
    login: (email: string, password: string) => Promise<boolean>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Kiểm tra token khi khởi động
    useEffect(() => {
        const initAuth = async () => {
            try {
                const userData = await authApi.getMe();
                if (userData) {
                    setUser(userData as User);
                }
            } catch (error) {
                console.error('Auth init error:', error);
                tokenUtils.clearTokens();
            } finally {
                setIsLoading(false);
            }
        };

        initAuth();
    }, []);

    /**
     * Login với email và password
     */
    const login = useCallback(async (email: string, password: string): Promise<boolean> => {
        try {
            setIsLoading(true);
            await authApi.login(email, password);
            const userData = await authApi.getMe();
            setUser(userData as User);
            message.success('Đăng nhập thành công!');
            return true;
        } catch (error: unknown) {
            console.error('Login error:', error);

            // Hiển thị message lỗi chi tiết hơn
            if (error && typeof error === 'object' && 'response' in error) {
                const axiosError = error as { response?: { data?: { detail?: string } } };
                const detail = axiosError.response?.data?.detail;
                if (detail) {
                    message.error(detail);
                } else {
                    message.error('Email hoặc mật khẩu không đúng!');
                }
            } else {
                message.error('Không thể kết nối đến server!');
            }
            return false;
        } finally {
            setIsLoading(false);
        }
    }, []);

    const logout = useCallback(() => {
        authApi.logout();
        setUser(null);
        message.success('Đã đăng xuất!');
    }, []);

    const value: AuthContextType = {
        user,
        isLoading,
        loading: isLoading,
        isAuthenticated: !!user,
        login,
        logout,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
