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
    Form,
    Input,
} from 'antd';
import {
    ReloadOutlined,
    FileImageOutlined,
    EyeOutlined,
    CheckCircleOutlined,
    FormOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { risApi } from '@/lib/services';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { TextArea } = Input;

/**
 * RIS Page - Quản lý phiếu chẩn đoán hình ảnh
 * Radiology Information System
 */

interface ImagingProcedure {
    id: string;
    code: string;
    name: string;
    body_part: string;
    modality: { code: string; name: string };
}

interface ImagingResult {
    findings: string;
    conclusion: string;
    recommendation?: string;
    is_abnormal: boolean;
    is_critical: boolean;
    is_verified: boolean;
}

interface ImagingOrder {
    id: string;
    visit: { visit_code: string };
    patient: { patient_code: string; full_name?: string; first_name?: string; last_name?: string };
    procedure: ImagingProcedure;
    clinical_indication: string;
    status: string;
    priority: string;
    order_time: string;
    note?: string;
    result?: ImagingResult;
}

const statusConfig: Record<string, { color: string; label: string }> = {
    PENDING: { color: 'gold', label: 'Chờ thực hiện' },
    SCHEDULED: { color: 'cyan', label: 'Đã lên lịch' },
    IN_PROGRESS: { color: 'blue', label: 'Đang chụp' },
    COMPLETED: { color: 'purple', label: 'Đã chụp, chờ đọc' },
    REPORTED: { color: 'geekblue', label: 'Đã có kết quả' },
    VERIFIED: { color: 'green', label: 'Đã duyệt' },
    CANCELLED: { color: 'default', label: 'Đã hủy' },
};

const priorityConfig: Record<string, { color: string; label: string }> = {
    NORMAL: { color: 'default', label: 'Bình thường' },
    URGENT: { color: 'orange', label: 'Khẩn' },
    STAT: { color: 'red', label: 'Cấp cứu' },
};

export default function RISPage() {
    const [orders, setOrders] = useState<ImagingOrder[]>([]);
    const [loading, setLoading] = useState(false);
    const [statusFilter, setStatusFilter] = useState<string | undefined>();
    const [selectedOrder, setSelectedOrder] = useState<ImagingOrder | null>(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);
    const [reportModalOpen, setReportModalOpen] = useState(false);
    const [reportLoading, setReportLoading] = useState(false);
    const [form] = Form.useForm();

    // Fetch imaging orders
    const fetchOrders = useCallback(async () => {
        setLoading(true);
        try {
            const response = await risApi.getOrders({ status: statusFilter });
            setOrders(response.results || []);
        } catch (error) {
            console.error('Error fetching imaging orders:', error);
            message.error('Không thể tải danh sách phiếu CĐHA');
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        fetchOrders();
    }, [fetchOrders]);

    // View order details
    const handleViewDetail = async (order: ImagingOrder) => {
        try {
            const detail = await risApi.getOrderById(order.id);
            setSelectedOrder(detail);
            setDetailModalOpen(true);
        } catch (error) {
            console.error('Error fetching order detail:', error);
            message.error('Không thể tải chi tiết phiếu');
        }
    };

    // Open report modal
    const handleWriteReport = (order: ImagingOrder) => {
        setSelectedOrder(order);
        form.resetFields();
        setReportModalOpen(true);
    };

    // Submit report
    const handleSubmitReport = async (values: Record<string, string | boolean>) => {
        if (!selectedOrder) return;
        setReportLoading(true);
        try {
            await risApi.submitResult(selectedOrder.id, {
                findings: values.findings as string,
                conclusion: values.conclusion as string,
                recommendation: values.recommendation as string,
                is_abnormal: values.is_abnormal as boolean,
                is_critical: values.is_critical as boolean,
            });
            message.success('Đã lưu kết quả');
            setReportModalOpen(false);
            fetchOrders();
        } catch (error) {
            console.error('Error submitting report:', error);
            message.error('Không thể lưu kết quả');
        } finally {
            setReportLoading(false);
        }
    };

    // Update order status
    const handleUpdateStatus = async (id: string, status: string) => {
        try {
            await risApi.updateOrderStatus(id, status);
            message.success('Cập nhật trạng thái thành công');
            fetchOrders();
        } catch (error) {
            console.error('Error updating status:', error);
            message.error('Không thể cập nhật trạng thái');
        }
    };

    // Table columns
    const columns: ColumnsType<ImagingOrder> = [
        {
            title: 'Kỹ thuật',
            key: 'procedure',
            render: (_, record) => (
                <Space direction="vertical" size={0}>
                    <Text strong>{record.procedure?.name}</Text>
                    <Text type="secondary" className="text-xs">
                        {record.procedure?.modality?.code} - {record.procedure?.body_part}
                    </Text>
                </Space>
            ),
        },
        {
            title: 'Bệnh nhân',
            key: 'patient',
            render: (_, record) => (
                <Space direction="vertical" size={0}>
                    <Text>
                        {record.patient.full_name ||
                            `${record.patient.last_name || ''} ${record.patient.first_name || ''}`}
                    </Text>
                    <Text type="secondary" className="text-xs">{record.patient.patient_code}</Text>
                </Space>
            ),
        },
        {
            title: 'Thời gian',
            dataIndex: 'order_time',
            key: 'order_time',
            width: 100,
            render: (time: string) => dayjs(time).format('HH:mm DD/MM'),
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
            width: 140,
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
                            icon={<FileImageOutlined />}
                            onClick={() => handleUpdateStatus(record.id, 'IN_PROGRESS')}
                        >
                            Bắt đầu
                        </Button>
                    )}
                    {record.status === 'COMPLETED' && (
                        <Button
                            size="small"
                            type="primary"
                            icon={<FormOutlined />}
                            onClick={() => handleWriteReport(record)}
                        >
                            Viết KQ
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
                    <Title level={3} className="!mb-0">Chẩn đoán hình ảnh (RIS)</Title>
                    <Text type="secondary">Quản lý phiếu CĐHA và kết quả đọc phim</Text>
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
            <div className="grid grid-cols-4 gap-4">
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Chờ thực hiện</Text>
                        <div className="text-2xl font-bold text-orange-500">
                            {orders.filter(o => o.status === 'PENDING').length}
                        </div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Đang thực hiện</Text>
                        <div className="text-2xl font-bold text-blue-500">
                            {orders.filter(o => o.status === 'IN_PROGRESS').length}
                        </div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Chờ đọc</Text>
                        <div className="text-2xl font-bold text-purple-500">
                            {orders.filter(o => o.status === 'COMPLETED').length}
                        </div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Hoàn thành</Text>
                        <div className="text-2xl font-bold text-green-500">
                            {orders.filter(o => ['REPORTED', 'VERIFIED'].includes(o.status)).length}
                        </div>
                    </div>
                </Card>
            </div>

            {/* Main Table */}
            <Card>
                <Table
                    columns={columns}
                    dataSource={orders}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10, showTotal: (t) => `${t} phiếu` }}
                    scroll={{ x: 900 }}
                    rowClassName={(record) =>
                        record.priority === 'STAT' ? 'bg-red-50' :
                            record.priority === 'URGENT' ? 'bg-orange-50' : ''
                    }
                />
            </Card>

            {/* Detail Modal */}
            <Modal
                title="Chi tiết phiếu CĐHA"
                open={detailModalOpen}
                onCancel={() => setDetailModalOpen(false)}
                footer={null}
                width={700}
            >
                {selectedOrder && (
                    <div className="space-y-4">
                        <Descriptions size="small" column={2}>
                            <Descriptions.Item label="Kỹ thuật">
                                {selectedOrder.procedure?.name}
                            </Descriptions.Item>
                            <Descriptions.Item label="Loại máy">
                                {selectedOrder.procedure?.modality?.name}
                            </Descriptions.Item>
                            <Descriptions.Item label="Bệnh nhân">
                                {selectedOrder.patient.full_name ||
                                    `${selectedOrder.patient.last_name || ''} ${selectedOrder.patient.first_name || ''}`}
                            </Descriptions.Item>
                            <Descriptions.Item label="Thời gian">
                                {dayjs(selectedOrder.order_time).format('HH:mm DD/MM/YYYY')}
                            </Descriptions.Item>
                            <Descriptions.Item label="Chẩn đoán LS" span={2}>
                                {selectedOrder.clinical_indication}
                            </Descriptions.Item>
                        </Descriptions>

                        {selectedOrder.result && (
                            <Card size="small" title="Kết quả đọc phim">
                                <Space direction="vertical" className="w-full">
                                    <div>
                                        <Text strong>Mô tả hình ảnh:</Text>
                                        <div>{selectedOrder.result.findings}</div>
                                    </div>
                                    <div>
                                        <Text strong>Kết luận:</Text>
                                        <div>{selectedOrder.result.conclusion}</div>
                                    </div>
                                    {selectedOrder.result.recommendation && (
                                        <div>
                                            <Text strong>Đề xuất:</Text>
                                            <div>{selectedOrder.result.recommendation}</div>
                                        </div>
                                    )}
                                    <Space>
                                        {selectedOrder.result.is_abnormal && (
                                            <Tag color="orange">Bất thường</Tag>
                                        )}
                                        {selectedOrder.result.is_critical && (
                                            <Tag color="red">Nguy hiểm</Tag>
                                        )}
                                        {selectedOrder.result.is_verified && (
                                            <Tag color="green" icon={<CheckCircleOutlined />}>Đã duyệt</Tag>
                                        )}
                                    </Space>
                                </Space>
                            </Card>
                        )}
                    </div>
                )}
            </Modal>

            {/* Report Modal */}
            <Modal
                title="Viết kết quả CĐHA"
                open={reportModalOpen}
                onCancel={() => setReportModalOpen(false)}
                footer={null}
                width={600}
            >
                <Form form={form} layout="vertical" onFinish={handleSubmitReport}>
                    <Form.Item
                        name="findings"
                        label="Mô tả hình ảnh"
                        rules={[{ required: true, message: 'Vui lòng nhập mô tả' }]}
                    >
                        <TextArea rows={4} placeholder="Chi tiết những gì quan sát được trên phim..." />
                    </Form.Item>

                    <Form.Item
                        name="conclusion"
                        label="Kết luận"
                        rules={[{ required: true, message: 'Vui lòng nhập kết luận' }]}
                    >
                        <TextArea rows={2} placeholder="Kết luận chẩn đoán..." />
                    </Form.Item>

                    <Form.Item name="recommendation" label="Đề xuất/Khuyến nghị">
                        <TextArea rows={2} placeholder="Đề xuất chụp thêm, theo dõi..." />
                    </Form.Item>

                    <Space>
                        <Form.Item name="is_abnormal" valuePropName="checked">
                            <Tag.CheckableTag checked={false}>Bất thường</Tag.CheckableTag>
                        </Form.Item>
                        <Form.Item name="is_critical" valuePropName="checked">
                            <Tag.CheckableTag checked={false}>Nguy hiểm</Tag.CheckableTag>
                        </Form.Item>
                    </Space>

                    <Form.Item className="mb-0 text-right">
                        <Button type="primary" htmlType="submit" loading={reportLoading}>
                            Lưu kết quả
                        </Button>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
