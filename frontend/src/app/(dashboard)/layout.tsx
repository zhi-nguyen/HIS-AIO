'use client';

import { useState, useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Layout, Menu, Avatar, Dropdown, Space, Typography, Spin, Button } from 'antd';
import {
    DashboardOutlined,
    UserOutlined,
    TeamOutlined,
    MedicineBoxOutlined,
    ExperimentOutlined,
    PictureOutlined,
    DollarOutlined,
    MenuFoldOutlined,
    MenuUnfoldOutlined,
    LogoutOutlined,
    SettingOutlined,
    BellOutlined,
    OrderedListOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useAuth } from '@/contexts/AuthContext';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

/**
 * Dashboard Layout
 * Layout chính với Sidebar navigation cho các trang dashboard
 */

// Menu items theo module
const menuItems: MenuProps['items'] = [
    {
        key: '/dashboard',
        icon: <DashboardOutlined />,
        label: 'Tổng quan',
    },
    {
        type: 'divider',
    },
    {
        key: 'reception',
        icon: <TeamOutlined />,
        label: 'Tiếp nhận',
        children: [
            { key: '/dashboard/patients', label: 'Bệnh nhân' },
            { key: '/dashboard/reception', label: 'Tiếp nhận khám' },
            { key: '/dashboard/qms', label: 'Hàng đợi (QMS)' },
        ],
    },
    {
        key: 'clinical',
        icon: <MedicineBoxOutlined />,
        label: 'Khám bệnh',
        children: [
            { key: '/dashboard/clinical', label: 'Phòng khám' },
            { key: '/dashboard/clinical/queue', label: 'Danh sách chờ' },
        ],
    },
    {
        key: 'paraclinical',
        icon: <ExperimentOutlined />,
        label: 'Cận lâm sàng',
        children: [
            { key: '/dashboard/lis', label: 'Xét nghiệm (LIS)' },
            { key: '/dashboard/ris', label: 'Chẩn đoán HA (RIS)' },
        ],
    },
    {
        key: '/dashboard/pharmacy',
        icon: <OrderedListOutlined />,
        label: 'Dược phẩm',
    },
    {
        key: '/dashboard/billing',
        icon: <DollarOutlined />,
        label: 'Thanh toán',
    },
];

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();
    const pathname = usePathname();
    const { user, logout, isAuthenticated, isLoading } = useAuth();
    const [collapsed, setCollapsed] = useState(false);

    // Redirect nếu chưa đăng nhập
    useEffect(() => {
        if (!isLoading && !isAuthenticated) {
            router.push('/login');
        }
    }, [isAuthenticated, isLoading, router]);

    // Menu click handler
    const handleMenuClick: MenuProps['onClick'] = (e) => {
        router.push(e.key);
    };

    // User dropdown menu
    const userMenuItems: MenuProps['items'] = [
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
                <Spin size="large" fullscreen tip="Đang tải..." />
            </div>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    // Tìm selected keys và open keys từ pathname
    const getSelectedKeys = () => [pathname];
    const getOpenKeys = () => {
        if (pathname.includes('/patients') || pathname.includes('/reception') || pathname.includes('/qms')) {
            return ['reception'];
        }
        if (pathname.includes('/clinical')) {
            return ['clinical'];
        }
        if (pathname.includes('/lis') || pathname.includes('/ris')) {
            return ['paraclinical'];
        }
        return [];
    };

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

                {/* Navigation Menu */}
                <Menu
                    theme="dark"
                    mode="inline"
                    selectedKeys={getSelectedKeys()}
                    defaultOpenKeys={getOpenKeys()}
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
