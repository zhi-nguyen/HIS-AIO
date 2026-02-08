/**
 * Role Configuration
 * Cấu hình phân quyền theo vai trò
 */

export type StaffRole =
    | 'ADMIN'
    | 'DOCTOR'
    | 'NURSE'
    | 'RECEPTIONIST'
    | 'LAB_TECHNICIAN'
    | 'PHARMACIST'
    | 'RADIOLOGIST'
    | 'CASHIER';

export interface RoleConfig {
    label: string;
    color: string;
    defaultRoute: string;
    allowedRoutes: string[];
}

/**
 * Cấu hình quyền truy cập theo vai trò
 */
export const roleConfig: Record<StaffRole, RoleConfig> = {
    ADMIN: {
        label: 'Quản trị viên',
        color: 'red',
        defaultRoute: '/dashboard',
        allowedRoutes: ['*'], // Access all
    },
    DOCTOR: {
        label: 'Bác sĩ',
        color: 'blue',
        defaultRoute: '/dashboard/clinical',
        allowedRoutes: [
            '/dashboard',
            '/dashboard/clinical',
            '/dashboard/clinical/*',
            '/dashboard/patients',
            '/dashboard/lis',
            '/dashboard/ris',
        ],
    },
    NURSE: {
        label: 'Điều dưỡng',
        color: 'green',
        defaultRoute: '/dashboard/clinical',
        allowedRoutes: [
            '/dashboard',
            '/dashboard/clinical',
            '/dashboard/clinical/*',
            '/dashboard/patients',
            '/dashboard/qms',
        ],
    },
    RECEPTIONIST: {
        label: 'Tiếp nhận',
        color: 'orange',
        defaultRoute: '/dashboard/reception',
        allowedRoutes: [
            '/dashboard',
            '/dashboard/reception',
            '/dashboard/patients',
            '/dashboard/qms',
        ],
    },
    LAB_TECHNICIAN: {
        label: 'Kỹ thuật viên XN',
        color: 'purple',
        defaultRoute: '/dashboard/lis',
        allowedRoutes: [
            '/dashboard',
            '/dashboard/lis',
            '/dashboard/qms',
        ],
    },
    PHARMACIST: {
        label: 'Dược sĩ',
        color: 'cyan',
        defaultRoute: '/dashboard/pharmacy',
        allowedRoutes: [
            '/dashboard',
            '/dashboard/pharmacy',
            '/dashboard/qms',
        ],
    },
    RADIOLOGIST: {
        label: 'Bác sĩ CĐHA',
        color: 'geekblue',
        defaultRoute: '/dashboard/ris',
        allowedRoutes: [
            '/dashboard',
            '/dashboard/ris',
            '/dashboard/clinical',
        ],
    },
    CASHIER: {
        label: 'Thu ngân',
        color: 'gold',
        defaultRoute: '/dashboard/billing',
        allowedRoutes: [
            '/dashboard',
            '/dashboard/billing',
            '/dashboard/patients',
        ],
    },
};

/**
 * Menu items theo vai trò
 */
export interface MenuItem {
    key: string;
    label: string;
    icon: string;
    path: string;
}

export const menuItemsByRole: Record<StaffRole, MenuItem[]> = {
    ADMIN: [
        { key: 'dashboard', label: 'Tổng quan', icon: 'DashboardOutlined', path: '/dashboard' },
        { key: 'patients', label: 'Bệnh nhân', icon: 'UserOutlined', path: '/dashboard/patients' },
        { key: 'reception', label: 'Tiếp nhận', icon: 'SolutionOutlined', path: '/dashboard/reception' },
        { key: 'qms', label: 'Gọi số', icon: 'NotificationOutlined', path: '/dashboard/qms' },
        { key: 'clinical', label: 'Khám bệnh', icon: 'MedicineBoxOutlined', path: '/dashboard/clinical' },
        { key: 'lis', label: 'Xét nghiệm', icon: 'ExperimentOutlined', path: '/dashboard/lis' },
        { key: 'ris', label: 'CĐHA', icon: 'FileImageOutlined', path: '/dashboard/ris' },
        { key: 'pharmacy', label: 'Dược', icon: 'MedicineBoxOutlined', path: '/dashboard/pharmacy' },
        { key: 'billing', label: 'Thanh toán', icon: 'DollarOutlined', path: '/dashboard/billing' },
    ],
    DOCTOR: [
        { key: 'dashboard', label: 'Tổng quan', icon: 'DashboardOutlined', path: '/dashboard' },
        { key: 'clinical', label: 'Khám bệnh', icon: 'MedicineBoxOutlined', path: '/dashboard/clinical' },
        { key: 'patients', label: 'Bệnh nhân', icon: 'UserOutlined', path: '/dashboard/patients' },
        { key: 'lis', label: 'Kết quả XN', icon: 'ExperimentOutlined', path: '/dashboard/lis' },
        { key: 'ris', label: 'Kết quả CĐHA', icon: 'FileImageOutlined', path: '/dashboard/ris' },
    ],
    NURSE: [
        { key: 'dashboard', label: 'Tổng quan', icon: 'DashboardOutlined', path: '/dashboard' },
        { key: 'clinical', label: 'Hỗ trợ khám', icon: 'MedicineBoxOutlined', path: '/dashboard/clinical' },
        { key: 'patients', label: 'Bệnh nhân', icon: 'UserOutlined', path: '/dashboard/patients' },
        { key: 'qms', label: 'Gọi số', icon: 'NotificationOutlined', path: '/dashboard/qms' },
    ],
    RECEPTIONIST: [
        { key: 'dashboard', label: 'Tổng quan', icon: 'DashboardOutlined', path: '/dashboard' },
        { key: 'reception', label: 'Tiếp nhận', icon: 'SolutionOutlined', path: '/dashboard/reception' },
        { key: 'patients', label: 'Bệnh nhân', icon: 'UserOutlined', path: '/dashboard/patients' },
        { key: 'qms', label: 'Gọi số', icon: 'NotificationOutlined', path: '/dashboard/qms' },
    ],
    LAB_TECHNICIAN: [
        { key: 'dashboard', label: 'Tổng quan', icon: 'DashboardOutlined', path: '/dashboard' },
        { key: 'lis', label: 'Xét nghiệm', icon: 'ExperimentOutlined', path: '/dashboard/lis' },
        { key: 'qms', label: 'Gọi số', icon: 'NotificationOutlined', path: '/dashboard/qms' },
    ],
    PHARMACIST: [
        { key: 'dashboard', label: 'Tổng quan', icon: 'DashboardOutlined', path: '/dashboard' },
        { key: 'pharmacy', label: 'Phát thuốc', icon: 'MedicineBoxOutlined', path: '/dashboard/pharmacy' },
        { key: 'qms', label: 'Gọi số', icon: 'NotificationOutlined', path: '/dashboard/qms' },
    ],
    RADIOLOGIST: [
        { key: 'dashboard', label: 'Tổng quan', icon: 'DashboardOutlined', path: '/dashboard' },
        { key: 'ris', label: 'CĐHA', icon: 'FileImageOutlined', path: '/dashboard/ris' },
        { key: 'clinical', label: 'Ca khám', icon: 'MedicineBoxOutlined', path: '/dashboard/clinical' },
    ],
    CASHIER: [
        { key: 'dashboard', label: 'Tổng quan', icon: 'DashboardOutlined', path: '/dashboard' },
        { key: 'billing', label: 'Thanh toán', icon: 'DollarOutlined', path: '/dashboard/billing' },
        { key: 'patients', label: 'Bệnh nhân', icon: 'UserOutlined', path: '/dashboard/patients' },
    ],
};

/**
 * Kiểm tra quyền truy cập route
 */
export function canAccessRoute(role: StaffRole, path: string): boolean {
    const config = roleConfig[role];
    if (!config) return false;

    // Admin có quyền truy cập tất cả
    if (config.allowedRoutes.includes('*')) return true;

    // Kiểm tra exact match hoặc wildcard
    return config.allowedRoutes.some(route => {
        if (route.endsWith('/*')) {
            const baseRoute = route.slice(0, -2);
            return path.startsWith(baseRoute);
        }
        return path === route || path.startsWith(route + '/');
    });
}

/**
 * Lấy default route theo vai trò
 */
export function getDefaultRoute(role: StaffRole): string {
    return roleConfig[role]?.defaultRoute || '/dashboard';
}

/**
 * Lấy menu items theo vai trò
 */
export function getMenuItems(role: StaffRole): MenuItem[] {
    return menuItemsByRole[role] || [];
}
