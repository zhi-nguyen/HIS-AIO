'use client';

import { Card, Row, Col, Statistic, Typography, Space, Table, Tag, Progress } from 'antd';
import {
    UserOutlined,
    TeamOutlined,
    MedicineBoxOutlined,
    ClockCircleOutlined,
    CheckCircleOutlined,
    ExperimentOutlined,
    RiseOutlined,
} from '@ant-design/icons';

const { Title, Text } = Typography;

/**
 * Dashboard Page
 * Trang tổng quan hiển thị các số liệu thống kê
 */

// Mock data - Thay bằng API call thực tế
const stats = {
    totalPatients: 1234,
    todayVisits: 87,
    waitingQueue: 12,
    completedToday: 65,
    pendingLabs: 23,
    pendingImaging: 8,
};

const recentVisits = [
    {
        key: '1',
        patientName: 'Nguyễn Văn A',
        visitCode: 'VIS-2024-0087',
        department: 'Nội khoa',
        status: 'IN_PROGRESS',
        time: '08:30',
    },
    {
        key: '2',
        patientName: 'Trần Thị B',
        visitCode: 'VIS-2024-0088',
        department: 'Nhi khoa',
        status: 'WAITING',
        time: '08:45',
    },
    {
        key: '3',
        patientName: 'Lê Văn C',
        visitCode: 'VIS-2024-0089',
        department: 'Ngoại khoa',
        status: 'COMPLETED',
        time: '07:15',
    },
    {
        key: '4',
        patientName: 'Phạm Thị D',
        visitCode: 'VIS-2024-0090',
        department: 'Tim mạch',
        status: 'WAITING',
        time: '09:00',
    },
];

const statusColors: Record<string, string> = {
    WAITING: 'orange',
    IN_PROGRESS: 'blue',
    COMPLETED: 'green',
    CANCELLED: 'red',
};

const statusLabels: Record<string, string> = {
    WAITING: 'Chờ khám',
    IN_PROGRESS: 'Đang khám',
    COMPLETED: 'Hoàn thành',
    CANCELLED: 'Đã hủy',
};

const columns = [
    {
        title: 'Mã phiếu',
        dataIndex: 'visitCode',
        key: 'visitCode',
        render: (text: string) => <Text strong>{text}</Text>,
    },
    {
        title: 'Bệnh nhân',
        dataIndex: 'patientName',
        key: 'patientName',
    },
    {
        title: 'Khoa',
        dataIndex: 'department',
        key: 'department',
    },
    {
        title: 'Giờ',
        dataIndex: 'time',
        key: 'time',
    },
    {
        title: 'Trạng thái',
        dataIndex: 'status',
        key: 'status',
        render: (status: string) => (
            <Tag color={statusColors[status]}>{statusLabels[status]}</Tag>
        ),
    },
];

export default function DashboardPage() {
    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div>
                <Title level={3} className="!mb-1">Tổng quan</Title>
                <Text type="secondary">Chào mừng bạn đến với hệ thống HIS</Text>
            </div>

            {/* Statistics Cards */}
            <Row gutter={[16, 16]}>
                <Col xs={24} sm={12} lg={6}>
                    <Card className="card-hover">
                        <Statistic
                            title="Tổng bệnh nhân"
                            value={stats.totalPatients}
                            prefix={<UserOutlined className="text-blue-500" />}
                            styles={{ content: { color: '#1E88E5' } }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card className="card-hover">
                        <Statistic
                            title="Lượt khám hôm nay"
                            value={stats.todayVisits}
                            prefix={<TeamOutlined className="text-green-500" />}
                            styles={{ content: { color: '#4CAF50' } }}
                            suffix={<RiseOutlined />}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card className="card-hover">
                        <Statistic
                            title="Đang chờ khám"
                            value={stats.waitingQueue}
                            prefix={<ClockCircleOutlined className="text-orange-500" />}
                            styles={{ content: { color: '#FF9800' } }}
                        />
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={6}>
                    <Card className="card-hover">
                        <Statistic
                            title="Hoàn thành"
                            value={stats.completedToday}
                            prefix={<CheckCircleOutlined className="text-green-500" />}
                            styles={{ content: { color: '#4CAF50' } }}
                        />
                    </Card>
                </Col>
            </Row>

            {/* Second Row - Paraclinical Stats */}
            <Row gutter={[16, 16]}>
                <Col xs={24} sm={12} lg={8}>
                    <Card className="card-hover">
                        <Space orientation="vertical" className="w-full">
                            <div className="flex justify-between items-center">
                                <Space>
                                    <ExperimentOutlined className="text-purple-500 text-xl" />
                                    <Text strong>Xét nghiệm chờ</Text>
                                </Space>
                                <Text className="text-2xl font-bold text-purple-600">{stats.pendingLabs}</Text>
                            </div>
                            <Progress percent={75} strokeColor="#9c27b0" showInfo={false} />
                        </Space>
                    </Card>
                </Col>
                <Col xs={24} sm={12} lg={8}>
                    <Card className="card-hover">
                        <Space orientation="vertical" className="w-full">
                            <div className="flex justify-between items-center">
                                <Space>
                                    <MedicineBoxOutlined className="text-cyan-500 text-xl" />
                                    <Text strong>CĐHA chờ</Text>
                                </Space>
                                <Text className="text-2xl font-bold text-cyan-600">{stats.pendingImaging}</Text>
                            </div>
                            <Progress percent={40} strokeColor="#00bcd4" showInfo={false} />
                        </Space>
                    </Card>
                </Col>
                <Col xs={24} lg={8}>
                    <Card className="card-hover">
                        <Space orientation="vertical" className="w-full">
                            <div className="flex justify-between items-center">
                                <Space>
                                    <CheckCircleOutlined className="text-green-500 text-xl" />
                                    <Text strong>Tỷ lệ hoàn thành</Text>
                                </Space>
                                <Text className="text-2xl font-bold text-green-600">75%</Text>
                            </div>
                            <Progress percent={75} strokeColor="#4CAF50" showInfo={false} />
                        </Space>
                    </Card>
                </Col>
            </Row>

            {/* Recent Visits Table */}
            <Card title="Lượt khám gần đây" className="card-shadow">
                <Table
                    columns={columns}
                    dataSource={recentVisits}
                    pagination={false}
                    size="middle"
                />
            </Card>
        </div>
    );
}
