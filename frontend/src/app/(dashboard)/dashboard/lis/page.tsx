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
    Modal,
    Descriptions,
    Input,
    InputNumber,
    Spin,
} from 'antd';
import {
    ReloadOutlined,
    ExperimentOutlined,
    CheckCircleOutlined,
    ClockCircleOutlined,
    EyeOutlined,
    EditOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { lisApi } from '@/lib/services';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

/**
 * LIS Page - Quản lý phiếu xét nghiệm
 * Laboratory Information System
 */

interface LabTest {
    id: string;
    code: string;
    name: string;
    unit?: string;
    min_limit?: number;
    max_limit?: number;
}

interface LabOrderDetail {
    id: string;
    test: LabTest;
    result?: {
        value_string: string;
        value_numeric?: number;
        is_abnormal: boolean;
        is_critical: boolean;
        abnormal_flag?: string;
    };
}

interface LabOrder {
    id: string;
    visit: { visit_code: string };
    patient: { patient_code: string; full_name?: string; first_name?: string; last_name?: string };
    status: string;
    order_time: string;
    note?: string;
    details?: LabOrderDetail[];
}

const statusConfig: Record<string, { color: string; label: string }> = {
    PENDING: { color: 'gold', label: 'Chờ lấy mẫu' },
    SAMPLING: { color: 'cyan', label: 'Đã lấy mẫu' },
    PROCESSING: { color: 'blue', label: 'Đang thực hiện' },
    COMPLETED: { color: 'green', label: 'Đã có kết quả' },
    CANCELLED: { color: 'default', label: 'Đã hủy' },
};

export default function LISPage() {
    const [orders, setOrders] = useState<LabOrder[]>([]);
    const [loading, setLoading] = useState(false);
    const [statusFilter, setStatusFilter] = useState<string | undefined>();
    const [selectedOrder, setSelectedOrder] = useState<LabOrder | null>(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);
    const [resultModalOpen, setResultModalOpen] = useState(false);

    // Fetch lab orders
    const fetchOrders = useCallback(async () => {
        setLoading(true);
        try {
            const response = await lisApi.getOrders({ status: statusFilter });
            setOrders(response.results || []);
        } catch (error) {
            console.error('Error fetching lab orders:', error);
            message.error('Không thể tải danh sách phiếu xét nghiệm');
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        fetchOrders();
    }, [fetchOrders]);

    // View order details
    const handleViewDetail = async (order: LabOrder) => {
        try {
            const detail = await lisApi.getOrderById(order.id);
            setSelectedOrder(detail);
            setDetailModalOpen(true);
        } catch (error) {
            console.error('Error fetching order detail:', error);
            message.error('Không thể tải chi tiết phiếu');
        }
    };

    // Open result entry modal
    const handleEnterResult = (order: LabOrder) => {
        setSelectedOrder(order);
        setResultModalOpen(true);
    };

    // Update order status
    const handleUpdateStatus = async (id: string, status: string) => {
        try {
            await lisApi.updateOrderStatus(id, status);
            message.success('Cập nhật trạng thái thành công');
            fetchOrders();
        } catch (error) {
            console.error('Error updating status:', error);
            message.error('Không thể cập nhật trạng thái');
        }
    };

    // Table columns
    const columns: ColumnsType<LabOrder> = [
        {
            title: 'Mã phiếu',
            key: 'id',
            width: 100,
            render: (_, record) => (
                <Text strong className="text-blue-600">
                    {record.id.slice(0, 8).toUpperCase()}
                </Text>
            ),
        },
        {
            title: 'Bệnh nhân',
            key: 'patient',
            render: (_, record) => (
                <Space orientation="vertical" size={0}>
                    <Text strong>
                        {record.patient.full_name ||
                            `${record.patient.last_name || ''} ${record.patient.first_name || ''}`}
                    </Text>
                    <Text type="secondary" className="text-xs">{record.patient.patient_code}</Text>
                </Space>
            ),
        },
        {
            title: 'Mã khám',
            dataIndex: ['visit', 'visit_code'],
            key: 'visit',
            width: 130,
        },
        {
            title: 'Thời gian',
            dataIndex: 'order_time',
            key: 'order_time',
            width: 100,
            render: (time: string) => dayjs(time).format('HH:mm DD/MM'),
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            width: 130,
            render: (status: string) => {
                const config = statusConfig[status] || { color: 'default', label: status };
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
        {
            title: 'Thao tác',
            key: 'actions',
            width: 200,
            render: (_, record) => (
                <Space>
                    <Button
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => handleViewDetail(record)}
                    >
                        Chi tiết
                    </Button>
                    {record.status === 'PENDING' && (
                        <Button
                            size="small"
                            type="primary"
                            icon={<ExperimentOutlined />}
                            onClick={() => handleUpdateStatus(record.id, 'SAMPLING')}
                        >
                            Lấy mẫu
                        </Button>
                    )}
                    {record.status === 'SAMPLING' && (
                        <Button
                            size="small"
                            type="primary"
                            icon={<EditOutlined />}
                            onClick={() => handleEnterResult(record)}
                        >
                            Nhập KQ
                        </Button>
                    )}
                </Space>
            ),
        },
    ];

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex justify-between items-center">
                <div>
                    <Title level={3} className="!mb-0">Xét nghiệm (LIS)</Title>
                    <Text type="secondary">Quản lý phiếu xét nghiệm và kết quả</Text>
                </div>
                <Space>
                    <Select
                        placeholder="Trạng thái"
                        value={statusFilter}
                        onChange={setStatusFilter}
                        allowClear
                        style={{ width: 150 }}
                        options={Object.entries(statusConfig).map(([k, v]) => ({
                            value: k,
                            label: v.label,
                        }))}
                    />
                    <Button icon={<ReloadOutlined />} onClick={fetchOrders}>
                        Làm mới
                    </Button>
                </Space>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-5 gap-4">
                {Object.entries(statusConfig).map(([key, config]) => (
                    <Card size="small" key={key}>
                        <div className="text-center">
                            <Text type="secondary">{config.label}</Text>
                            <div className="text-2xl font-bold" style={{ color: config.color === 'default' ? '#666' : undefined }}>
                                <Badge color={config.color} />
                                {orders.filter(o => o.status === key).length}
                            </div>
                        </div>
                    </Card>
                ))}
            </div>

            {/* Main Table */}
            <Card>
                <Table
                    columns={columns}
                    dataSource={orders}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10, showTotal: (t) => `${t} phiếu` }}
                    scroll={{ x: 800 }}
                    rowClassName={(record) =>
                        record.status === 'COMPLETED' && record.details?.some(d => d.result?.is_critical)
                            ? 'bg-red-50'
                            : ''
                    }
                />
            </Card>

            {/* Detail Modal */}
            <Modal
                title="Chi tiết phiếu xét nghiệm"
                open={detailModalOpen}
                onCancel={() => setDetailModalOpen(false)}
                footer={null}
                width={700}
            >
                {selectedOrder && (
                    <div className="space-y-4">
                        <Descriptions size="small" column={2}>
                            <Descriptions.Item label="Mã phiếu">
                                {selectedOrder.id.slice(0, 8).toUpperCase()}
                            </Descriptions.Item>
                            <Descriptions.Item label="Trạng thái">
                                <Tag color={statusConfig[selectedOrder.status]?.color}>
                                    {statusConfig[selectedOrder.status]?.label}
                                </Tag>
                            </Descriptions.Item>
                            <Descriptions.Item label="Bệnh nhân">
                                {selectedOrder.patient.full_name ||
                                    `${selectedOrder.patient.last_name || ''} ${selectedOrder.patient.first_name || ''}`}
                            </Descriptions.Item>
                            <Descriptions.Item label="Thời gian">
                                {dayjs(selectedOrder.order_time).format('HH:mm DD/MM/YYYY')}
                            </Descriptions.Item>
                        </Descriptions>

                        <Table
                            dataSource={selectedOrder.details}
                            rowKey="id"
                            size="small"
                            pagination={false}
                            columns={[
                                {
                                    title: 'Xét nghiệm',
                                    key: 'test',
                                    render: (_, d: LabOrderDetail) => (
                                        <Space orientation="vertical" size={0}>
                                            <Text strong>{d.test.name}</Text>
                                            <Text type="secondary" className="text-xs">{d.test.code}</Text>
                                        </Space>
                                    ),
                                },
                                {
                                    title: 'Kết quả',
                                    key: 'result',
                                    render: (_, d: LabOrderDetail) => {
                                        if (!d.result) return <Text type="secondary">Chưa có</Text>;
                                        return (
                                            <Space>
                                                <Text strong>{d.result.value_string}</Text>
                                                <Text type="secondary">{d.test.unit}</Text>
                                                {d.result.abnormal_flag && (
                                                    <Tag color={d.result.is_critical ? 'red' : 'orange'}>
                                                        {d.result.abnormal_flag}
                                                    </Tag>
                                                )}
                                            </Space>
                                        );
                                    },
                                },
                                {
                                    title: 'Bình thường',
                                    key: 'range',
                                    render: (_, d: LabOrderDetail) => (
                                        <Text type="secondary">
                                            {d.test.min_limit} - {d.test.max_limit} {d.test.unit}
                                        </Text>
                                    ),
                                },
                            ]}
                        />
                    </div>
                )}
            </Modal>

            {/* Result Entry Modal */}
            <Modal
                title="Nhập kết quả xét nghiệm"
                open={resultModalOpen}
                onCancel={() => setResultModalOpen(false)}
                footer={null}
                width={600}
            >
                <div className="text-center py-8 text-gray-500">
                    <ExperimentOutlined className="text-4xl mb-2" />
                    <div>Chức năng nhập kết quả đang được phát triển</div>
                </div>
            </Modal>
        </div>
    );
}
