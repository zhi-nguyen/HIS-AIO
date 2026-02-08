'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';
import { canAccessRoute, getDefaultRoute, StaffRole } from '@/lib/roles';
import { Result, Button } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import Loading from '@/components/common/Loading';

/**
 * Route Guard Component
 * Kiểm tra quyền truy cập dựa trên vai trò
 */

interface RouteGuardProps {
    children: React.ReactNode;
    requiredRoles?: StaffRole[];
}

export default function RouteGuard({ children, requiredRoles }: RouteGuardProps) {
    const { user, loading } = useAuth();
    const router = useRouter();
    const pathname = usePathname();

    useEffect(() => {
        if (!loading && !user) {
            router.push('/login');
        }
    }, [user, loading, router]);

    if (loading) {
        return <Loading tip="Đang kiểm tra quyền..." />;
    }

    if (!user) {
        return null;
    }

    const userRole = user.staff_profile?.role as StaffRole;

    // Nếu có requiredRoles, kiểm tra xem user có trong danh sách không
    if (requiredRoles && requiredRoles.length > 0) {
        if (!requiredRoles.includes(userRole)) {
            return (
                <Result
                    status="403"
                    icon={<LockOutlined className="text-gray-400" />}
                    title="Không có quyền truy cập"
                    subTitle={`Trang này chỉ dành cho: ${requiredRoles.join(', ')}`}
                    extra={
                        <Button
                            type="primary"
                            onClick={() => router.push(getDefaultRoute(userRole))}
                        >
                            Về trang chính
                        </Button>
                    }
                />
            );
        }
    }

    // Kiểm tra theo route config
    if (!canAccessRoute(userRole, pathname)) {
        return (
            <Result
                status="403"
                icon={<LockOutlined className="text-gray-400" />}
                title="Không có quyền truy cập"
                subTitle="Bạn không có quyền truy cập trang này."
                extra={
                    <Button
                        type="primary"
                        onClick={() => router.push(getDefaultRoute(userRole))}
                    >
                        Về trang chính
                    </Button>
                }
            />
        );
    }

    return <>{children}</>;
}

/**
 * HOC để wrap page với quyền truy cập
 */
export function withRoleGuard<P extends object>(
    WrappedComponent: React.ComponentType<P>,
    requiredRoles?: StaffRole[]
) {
    return function WithRoleGuardComponent(props: P) {
        return (
            <RouteGuard requiredRoles={requiredRoles}>
                <WrappedComponent {...props} />
            </RouteGuard>
        );
    };
}
