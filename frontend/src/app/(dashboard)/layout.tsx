'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Layout, Menu, Avatar, Dropdown, Space, Typography, Spin, Button, Tag } from 'antd';
import {
    DashboardOutlined,
    UserOutlined,
    TeamOutlined,
    MedicineBoxOutlined,
    ExperimentOutlined,
    FileImageOutlined,
    DollarOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    LogoutOutlined,
    SettingOutlined,
    BellOutlined,
    SolutionOutlined,
    NotificationOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useAuth } from '@/contexts/AuthContext';
import { getMenuItems, roleConfig, StaffRole, canAccessRoute, getDefaultRoute } from '@/lib/roles';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

/**
 * Dashboard Layout với Role-based Navigation
 */

// Icon mapping
const iconMap: Record<string, React.ReactNode> = {
    DashboardOutlined: <DashboardOutlined />,
    UserOutlined: <UserOutlined />,
    TeamOutlined: <TeamOutlined />,
    MedicineBoxOutlined: <MedicineBoxOutlined />,
    ExperimentOutlined: <ExperimentOutlined />,
    FileImageOutlined: <FileImageOutlined />,
    DollarOutlined: <DollarOutlined />,
    SolutionOutlined: <SolutionOutlined />,
    NotificationOutlined: <NotificationOutlined />,
};

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();
    const pathname = usePathname();
    const { user, logout, isAuthenticated, isLoading } = useAuth();
    const [collapsed, setCollapsed] = useState(false);

    const userRole = (user?.staff_profile?.role as StaffRole) || 'RECEPTIONIST';
    const roleInfo = roleConfig[userRole];

    // Tạo menu items dựa trên role
    const menuItems: MenuProps['items'] = useMemo(() => {
        const items = getMenuItems(userRole);
        return items.map(item => ({
            key: item.path,
            icon: iconMap[item.icon] || <DashboardOutlined />,
            label: item.label,
        }));
    }, [userRole]);

    // Redirect nếu chưa đăng nhập
    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, isLoading, router]);

    // Redirect nếu không có quyền truy cập route hiện tại
    useEffect(() => {
        if (!isLoading && isAuthenticated && pathname) {
            if (!canAccessRoute(userRole, pathname)) {
                router.push(getDefaultRoute(userRole));
            }
        }
    }, [isLoading, isAuthenticated, pathname, userRole, router]);

    // Menu click handler
    const handleMenuClick: MenuProps['onClick'] = (e) => {
        router.push(e.key);
    };

    // User dropdown menu
    const userMenuItems: MenuProps['items'] = [
        {
            key: 'role',
            label: (
                <Space>
                    <Text type="secondary">Vai trò:</Text>
                    <Tag color={roleInfo?.color}>{roleInfo?.label}</Tag>
                </Space>
            ),
            disabled: true,
        },
        { type: 'divider' },
        {
            key: 'profile',
            icon: <UserOutlined />,
            label: 'Thông tin cá nhân',
        },
        {
            key: 'settings',
            icon: <SettingOutlined />,
            label: 'Cài đặt',
        },
        { type: 'divider' },
        {
            key: 'logout',
            icon: <LogoutOutlined />,
            label: 'Đăng xuất',
            danger: true,
            onClick: () => {
                logout();
                router.push('/login');
            },
        },
    ];

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Spin size="large" tip="Đang tải..." />
            </div>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    return (
        <Layout className="min-h-screen">
            {/* Sidebar */}
            <Sider
                trigger={null}
                collapsible
                collapsed={collapsed}
                width={240}
                className="fixed left-0 top-0 bottom-0 z-50 overflow-auto"
            >
                {/* Logo */}
                <div className="h-16 flex items-center justify-center border-b border-white/10">
                    <Space>
                        <MedicineBoxOutlined className="text-2xl text-white" />
                        {!collapsed && (
                            <Text strong className="text-white text-lg">HIS System</Text>
                        )}
                    </Space>
                </div>

                {/* Role Badge */}
                {!collapsed && (
                    <div className="px-4 py-2 text-center">
                        <Tag color={roleInfo?.color} className="text-xs">
                            {roleInfo?.label}
                        </Tag>
                    </div>
                )}

                {/* Navigation Menu */}
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={[pathname]}
                    items={menuItems}
                    onClick={handleMenuClick}
                    className="border-none"
                />
            </Sider>

            {/* Main Content Area */}
            <Layout className={`transition-all duration-200 ${collapsed ? 'ml-20' : 'ml-60'}`}>
                {/* Header */}
                <Header className="bg-white px-4 flex items-center justify-between shadow-sm sticky top-0 z-40">
                    <Space>
                        <Button
                            type="text"
                            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                            onClick={() => setCollapsed(!collapsed)}
                            className="text-lg"
                        />
                    </Space>

                    <Space size="middle">
                        {/* Notifications */}
                        <Button type="text" icon={<BellOutlined />} className="text-lg" />

                        {/* User Menu */}
                        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
                            <Space className="cursor-pointer hover:bg-gray-50 px-2 py-1 rounded">
                                <Avatar icon={<UserOutlined />} className="bg-blue-500" />
                                <Text className="hidden md:inline">
                                    {user?.email || 'Người dùng'}
                                </Text>
                            </Space>
                        </Dropdown>
                    </Space>
                </Header>

                {/* Page Content */}
                <Content className="p-6 bg-gray-50 min-h-[calc(100vh-64px)]">
                    {children}
                </Content>
            </Layout>
        </Layout>
    );
}
