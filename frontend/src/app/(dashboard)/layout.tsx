'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Layout, Menu, Avatar, Dropdown, Space, Typography, Spin, Button, Tag, Tooltip, Drawer, Grid } from 'antd';
import { Toaster } from 'sonner';
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
    MenuOutlined,
    CloseOutlined,
} from '@ant-design/icons';
import type { MenuProps } from 'antd';
import { useAuth } from '@/contexts/AuthContext';
import { getMenuItems, roleConfig, StaffRole, canAccessRoute, getDefaultRoute } from '@/lib/roles';
import { useRemoteScanner } from '@/hooks/useRemoteScanner';
import ScannerStatus from '@/components/common/ScannerStatus';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;
const { useBreakpoint } = Grid;

/**
 * Dashboard Layout với Role-based Navigation — Responsive (Desktop/Tablet/Mobile)
 */

// Icon mapping — outline icons, consistent color
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

// Bottom nav items limit (mobile)
const MOBILE_NAV_MAX = 5;

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const router = useRouter();
    const pathname = usePathname();
    const { user, logout, isAuthenticated, isLoading } = useAuth();
    const screens = useBreakpoint();

    // Desktop: sidebar collapsed state; Mobile: drawer open state
    const [collapsed, setCollapsed] = useState(false);
    const [drawerOpen, setDrawerOpen] = useState(false);

    const isMobile = !screens.md; // < 768px
    const isTablet = screens.md && !screens.lg; // 768–1023px

    // Remote Scanner hook
    const { isConnected: scannerConnected, stationId: scannerStation, lastScan, setStationId: setScannerStation, disconnect: disconnectScanner } = useRemoteScanner();

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

    // Mobile bottom nav — top 5 items
    const mobileNavItems = useMemo(() => {
        const items = getMenuItems(userRole);
        return items.slice(0, MOBILE_NAV_MAX);
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

    // Auto collapse on tablet
    useEffect(() => {
        if (isTablet) setCollapsed(true);
        if (!isMobile && !isTablet) setCollapsed(false);
    }, [isMobile, isTablet]);

    // Menu click handler
    const handleMenuClick: MenuProps['onClick'] = (e) => {
        router.push(e.key);
        if (isMobile) setDrawerOpen(false);
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
                <Spin size="large" />
                <div className="mt-2">Đang tải...</div>
            </div>
        );
    }

    if (!isAuthenticated) {
        return null;
    }

    // ── Sidebar content (shared between Sider + Drawer) ──────────
    const SidebarContent = (
        <>
            {/* Logo */}
            <div style={{ height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center', borderBottom: '1px solid rgba(255,255,255,0.1)', padding: '0 16px' }}>
                <Space>
                    <MedicineBoxOutlined style={{ fontSize: 22, color: '#64B5F6' }} />
                    {(!collapsed || isMobile) && (
                        <Text strong style={{ color: '#fff', fontSize: 16 }}>HIS System</Text>
                    )}
                </Space>
            </div>

            {/* Role Badge */}
            {(!collapsed || isMobile) && (
                <div style={{ padding: '8px 16px', textAlign: 'center' }}>
                    <Tag color={roleInfo?.color} style={{ fontSize: 11 }}>
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
                inlineCollapsed={!isMobile && collapsed}
                style={{ border: 'none', fontSize: 14 }}
            />
        </>
    );

    // ────────────────────────────────────────────────────────────
    // MOBILE LAYOUT
    // ────────────────────────────────────────────────────────────
    if (isMobile) {
        return (
            <Layout style={{ minHeight: '100vh' }}>
                {/* Mobile Drawer Sidebar */}
                <Drawer
                    placement="left"
                    open={drawerOpen}
                    onClose={() => setDrawerOpen(false)}
                    width={240}
                    styles={{
                        header: { display: 'none' },
                        body: { background: '#001529', padding: 0 },
                    }}
                    maskClosable
                >
                    {/* Close button */}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', padding: '12px 12px 0' }}>
                        <Button
                            type="text"
                            icon={<CloseOutlined />}
                            onClick={() => setDrawerOpen(false)}
                            style={{ color: 'rgba(255,255,255,0.65)' }}
                        />
                    </div>
                    {SidebarContent}
                </Drawer>

                {/* Main layout */}
                <Layout>
                    {/* Mobile Header */}
                    <Header style={{
                        background: '#fff',
                        padding: '0 12px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        boxShadow: '0 1px 4px rgba(0,0,0,0.1)',
                        position: 'sticky',
                        top: 0,
                        zIndex: 40,
                        height: 56,
                    }}>
                        <Space>
                            <Button
                                type="text"
                                icon={<MenuOutlined />}
                                onClick={() => setDrawerOpen(true)}
                                style={{ fontSize: 18, color: '#374151' }}
                            />
                            <Space align="center">
                                <MedicineBoxOutlined style={{ color: '#1E88E5', fontSize: 18 }} />
                                <Text strong style={{ fontSize: 14 }}>HIS</Text>
                            </Space>
                        </Space>

                        <Space size="small">
                            <ScannerStatus
                                isConnected={scannerConnected}
                                stationId={scannerStation}
                                lastScan={lastScan}
                                onSetStationId={setScannerStation}
                                onDisconnect={disconnectScanner}
                            />
                            <Tooltip title="Thông báo">
                                <Button type="text" icon={<BellOutlined />} style={{ color: '#374151' }} />
                            </Tooltip>
                            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
                                <Avatar
                                    icon={<UserOutlined />}
                                    size="small"
                                    style={{ background: '#1E88E5', cursor: 'pointer' }}
                                />
                            </Dropdown>
                        </Space>
                    </Header>

                    {/* Content — add bottom padding for nav bar */}
                    <Content style={{ padding: 12, background: '#f5f7fa', minHeight: 'calc(100vh - 56px - 56px)', paddingBottom: 72 }}>
                        {children}
                    </Content>
                </Layout>

                {/* Mobile Bottom Navigation */}
                <nav className="mobile-bottom-nav">
                    {mobileNavItems.map(item => {
                        const icon = iconMap[item.icon] || <DashboardOutlined />;
                        const isActive = pathname === item.path;
                        return (
                            <div
                                key={item.path}
                                className={`mobile-bottom-nav-item ${isActive ? 'active' : ''}`}
                                onClick={() => router.push(item.path)}
                            >
                                <span style={{ fontSize: 20 }}>{icon}</span>
                                <span style={{ fontSize: 10, marginTop: 2 }}>{item.label.split(' ')[0]}</span>
                            </div>
                        );
                    })}
                </nav>

                <Toaster position="top-right" richColors closeButton duration={3000} />
            </Layout>
        );
    }

    // ────────────────────────────────────────────────────────────
    // DESKTOP + TABLET LAYOUT
    // ────────────────────────────────────────────────────────────
    return (
        <Layout style={{ minHeight: '100vh' }}>
            {/* Sidebar */}
            <Sider
                trigger={null}
                collapsible
                collapsed={collapsed}
                width={240}
                collapsedWidth={64}
                style={{
                    overflow: 'auto',
                    height: '100vh',
                    position: 'fixed',
                    left: 0,
                    top: 0,
                    bottom: 0,
                    zIndex: 50,
                    transition: 'width 0.2s',
                }}
            >
                {SidebarContent}
            </Sider>

            {/* Main Content Area */}
            <Layout style={{ marginLeft: collapsed ? 64 : 240, transition: 'margin-left 0.2s' }}>
                {/* Header */}
                <Header style={{
                    background: '#fff',
                    padding: '0 20px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
                    position: 'sticky',
                    top: 0,
                    zIndex: 40,
                    height: 56,
                }}>
                    <Space>
                        <Tooltip title={collapsed ? 'Mở rộng menu' : 'Thu gọn menu'}>
                            <Button
                                type="text"
                                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                                onClick={() => setCollapsed(!collapsed)}
                                style={{ fontSize: 16, color: '#374151' }}
                            />
                        </Tooltip>
                    </Space>

                    <Space size="middle">
                        {/* Scanner Status */}
                        <ScannerStatus
                            isConnected={scannerConnected}
                            stationId={scannerStation}
                            lastScan={lastScan}
                            onSetStationId={setScannerStation}
                            onDisconnect={disconnectScanner}
                        />

                        {/* Notifications */}
                        <Tooltip title="Thông báo">
                            <Button type="text" icon={<BellOutlined />} style={{ color: '#374151' }} />
                        </Tooltip>

                        {/* User Menu */}
                        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight" arrow>
                            <div className="cursor-pointer hover:bg-gray-50 px-2 py-1 rounded flex items-center gap-2">
                                <Avatar icon={<UserOutlined />} style={{ background: '#1E88E5' }} />
                                <Text className="hidden md:block m-0" style={{ maxWidth: 140, lineHeight: '1.2' }} ellipsis>
                                    {user?.email || 'Người dùng'}
                                </Text>
                            </div>
                        </Dropdown>
                    </Space>
                </Header>

                {/* Page Content */}
                <Content className="dashboard-content" style={{ padding: 24, background: '#f5f7fa', minHeight: 'calc(100vh - 56px)' }}>
                    {children}
                </Content>
            </Layout>

            <Toaster position="bottom-right" richColors closeButton duration={3000} />
        </Layout>
    );
}
