'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Card,
    Table,
    Button,
    Space,
    Tag,
    Typography,
    Badge,
    Select,
    message,
} from 'antd';
import {
    ReloadOutlined,
    MedicineBoxOutlined,
    UserOutlined,
    ClockCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { visitApi } from '@/lib/services';
import type { Visit, Patient } from '@/types';
import { useRouter } from 'next/navigation';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

/**
 * Clinical Waiting List Page
 * Danh sách bệnh nhân chờ khám của bác sĩ
 */

const statusConfig: Record<string, { color: string; label: string }> = {
    WAITING: { color: 'gold', label: 'Chờ khám' },
    IN_PROGRESS: { color: 'processing', label: 'Đang khám' },
    PENDING_RESULTS: { color: 'purple', label: 'Chờ CLS' },
    COMPLETED: { color: 'success', label: 'Hoàn thành' },
};

const priorityConfig: Record<string, { color: string; label: string }> = {
    NORMAL: { color: 'default', label: 'Bình thường' },
    PRIORITY: { color: 'orange', label: 'Ưu tiên' },
    EMERGENCY: { color: 'error', label: 'Cấp cứu' },
};

export default function ClinicalWaitingPage() {
    const [visits, setVisits] = useState<Visit[]>([]);
    const [loading, setLoading] = useState(false);
    const [statusFilter, setStatusFilter] = useState<string | undefined>('WAITING');
    const router = useRouter();

    // Fetch visits for clinical
    const fetchVisits = useCallback(async () => {
        setLoading(true);
        try {
            const response = await visitApi.getAll({ status: statusFilter });
            // Filter only clinical-relevant statuses
            const clinicalVisits = (response.results || []).filter((v: Visit) =>
                ['WAITING', 'IN_PROGRESS', 'PENDING_RESULTS'].includes(v.status)
            );
            setVisits(statusFilter ? response.results || [] : clinicalVisits);
        } catch (error) {
            console.error('Error fetching visits:', error);
            message.error('Không thể tải danh sách bệnh nhân');
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        fetchVisits();
        // Auto refresh every 30 seconds
        const interval = setInterval(fetchVisits, 30000);
        return () => clearInterval(interval);
    }, [fetchVisits]);

    // Start examination
    const handleStartExam = async (visit: Visit) => {
        try {
            // Update status to IN_PROGRESS
            await visitApi.update(visit.id, { status: 'IN_PROGRESS' });
            // Navigate to examination page
            router.push(`/dashboard/clinical/${visit.id}`);
        } catch (error) {
            console.error('Error starting exam:', error);
            message.error('Không thể bắt đầu khám');
        }
    };

    // Table columns
    const columns: ColumnsType<Visit> = [
        {
            title: 'STT',
            dataIndex: 'queue_number',
            key: 'queue_number',
            width: 70,
            render: (num: number) => (
                <Badge
                    count={num}
                    style={{ backgroundColor: '#1E88E5', fontSize: 14 }}
                    overflowCount={999}
                />
            ),
        },
        {
            title: 'Bệnh nhân',
            dataIndex: 'patient',
            key: 'patient',
            render: (patient: Patient | string) => {
                if (typeof patient === 'object' && patient) {
                    return (
                        <Space>
                            <UserOutlined className="text-gray-400" />
                            <div>
                                <Text strong>{patient.full_name || `${patient.last_name} ${patient.first_name}`}</Text>
                                <div className="text-xs text-gray-500">{patient.patient_code}</div>
                            </div>
                        </Space>
                    );
                }
                return patient || '-';
            },
        },
        {
            title: 'Check-in',
            dataIndex: 'check_in_time',
            key: 'check_in_time',
            width: 90,
            render: (time: string) => time ? dayjs(time).format('HH:mm') : '-',
        },
        {
            title: 'Thời gian chờ',
            key: 'wait_time',
            width: 110,
            render: (_: unknown, record: Visit) => {
                if (!record.check_in_time) return '-';
                const minutes = dayjs().diff(dayjs(record.check_in_time), 'minute');
                const color = minutes > 30 ? 'red' : minutes > 15 ? 'orange' : 'green';
                return (
                    <Tag color={color} icon={<ClockCircleOutlined />}>
                        {minutes} phút
                    </Tag>
                );
            },
        },
        {
            title: 'Ưu tiên',
            dataIndex: 'priority',
            key: 'priority',
            width: 100,
            render: (priority: string) => {
                const config = priorityConfig[priority] || { color: 'default', label: priority };
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            width: 110,
            render: (status: string) => {
                const config = statusConfig[status] || { color: 'default', label: status };
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
        {
            title: 'Thao tác',
            key: 'actions',
            width: 140,
            render: (_: unknown, record: Visit) => (
                <Button
                    type="primary"
                    size="small"
                    icon={<MedicineBoxOutlined />}
                    onClick={() => handleStartExam(record)}
                    disabled={record.status === 'COMPLETED'}
                >
                    {record.status === 'IN_PROGRESS' ? 'Tiếp tục' : 'Khám'}
                </Button>
            ),
        },
    ];

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex justify-between items-center">
                <div>
                    <Title level={3} className="!mb-0">Danh sách chờ khám</Title>
                    <Text type="secondary">Bệnh nhân đang chờ khám bệnh</Text>
                </div>
                <Space>
                    <Select
                        placeholder="Trạng thái"
                        value={statusFilter}
                        onChange={setStatusFilter}
                        allowClear
                        style={{ width: 140 }}
                        options={Object.entries(statusConfig).map(([k, v]) => ({
                            value: k,
                            label: v.label,
                        }))}
                    />
                    <Button icon={<ReloadOutlined />} onClick={fetchVisits}>
                        Làm mới
                    </Button>
                </Space>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4">
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Chờ khám</Text>
                        <div className="text-2xl font-bold text-orange-500">
                            {visits.filter(v => v.status === 'WAITING').length}
                        </div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Đang khám</Text>
                        <div className="text-2xl font-bold text-blue-500">
                            {visits.filter(v => v.status === 'IN_PROGRESS').length}
                        </div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Chờ CLS</Text>
                        <div className="text-2xl font-bold text-purple-500">
                            {visits.filter(v => v.status === 'PENDING_RESULTS').length}
                        </div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Hoàn thành</Text>
                        <div className="text-2xl font-bold text-green-500">
                            {visits.filter(v => v.status === 'COMPLETED').length}
                        </div>
                    </div>
                </Card>
            </div>

            {/* Main Table */}
            <Card>
                <Table
                    columns={columns}
                    dataSource={visits}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 15, showTotal: (t) => `${t} bệnh nhân` }}
                    scroll={{ x: 800 }}
                    rowClassName={(record) =>
                        record.priority === 'EMERGENCY' ? 'bg-red-50' :
                            record.priority === 'PRIORITY' ? 'bg-orange-50' : ''
                    }
                />
            </Card>
        </div>
    );
}
