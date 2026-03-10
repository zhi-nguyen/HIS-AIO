'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Card,
    Table,
    Typography,
    Badge,
    Row,
    Col,
    Space,
    Divider,
    message,
} from 'antd';
import { lisApi } from '@/lib/services';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface LabTest {
    id: string;
    code: string;
    name: string;
    unit: string;
    min_limit: number | null;
    max_limit: number | null;
    panic_low: number | null;
    panic_high: number | null;
}

interface LabResult {
    id: string;
    value_string: string;
    value_numeric: number | null;
    is_abnormal: boolean;
    is_critical: boolean;
    abnormal_flag: string | null;
    machine_name: string | null;
    result_time: string;
}

interface LabOrderDetail {
    id: string;
    test_name: string;
    test: LabTest;
    result: LabResult | null;
}

interface LabOrder {
    id: string;
    visit: string;
    visit_code: string;
    patient_code: string;
    patient_name: string | null;
    details: LabOrderDetail[];
    status: string;
    priority: string;
    created_at: string;
    order_time: string;
    doctor?: string;
}

export default function LISVerifiedPage() {
    const [orders, setOrders] = useState<LabOrder[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedOrder, setSelectedOrder] = useState<LabOrder | null>(null);

    const fetchOrders = useCallback(async () => {
        setLoading(true);
        try {
            const response = await lisApi.getOrders();
            const allOrders: LabOrder[] = response.results || response;
            // Chỉ lấy các order ĐÃ DUYỆT
            setOrders(allOrders.filter(o => o.status === 'VERIFIED'));
        } catch (error) {
            console.error('Error fetching lab orders:', error);
            message.error('Không thể tải dữ liệu LIS');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchOrders();
    }, [fetchOrders]);

    const handleSelectOrder = (order: LabOrder) => {
        setSelectedOrder(order);
    };

    const columns: ColumnsType<LabOrderDetail> = [
        {
            title: 'THÔNG SỐ (PARAMETER)',
            key: 'name',
            render: (_, record) => (
                <Space direction="vertical" size={2}>
                    <Text strong>{record.test?.name}</Text>
                    <Text type="secondary" className="text-xs">{record.test?.code}</Text>
                </Space>
            )
        },
        {
            title: 'KẾT QUẢ',
            key: 'result',
            width: 150,
            render: (_, record) => {
                const valStr = record.result?.value_string || '';
                const val = parseFloat(valStr);
                let isAbnormal = false;
                if (!isNaN(val) && record.test) {
                    if (record.test.min_limit !== null && val < record.test.min_limit) isAbnormal = true;
                    if (record.test.max_limit !== null && val > record.test.max_limit) isAbnormal = true;
                }

                return (
                    <Text style={{ color: isAbnormal ? 'var(--ant-color-error)' : 'inherit', fontWeight: isAbnormal ? 'bold' : 'normal' }}>
                        {valStr || '-'}
                    </Text>
                );
            }
        },
        {
            title: 'CỜ (FLAG)',
            key: 'flag',
            width: 100,
            render: (_, record) => {
                if (!record.test || !record.result) return '-';
                const val = parseFloat(record.result.value_string || '');
                if (isNaN(val)) return '-';
                if (record.test.min_limit !== null && val < record.test.min_limit) {
                    return <Text type="danger">↓ Thấp</Text>;
                }
                if (record.test.max_limit !== null && val > record.test.max_limit) {
                    return <Text type="danger">↑ Cao</Text>;
                }
                return '-';
            }
        },
        {
            title: 'ĐƠN VỊ',
            key: 'unit',
            dataIndex: ['test', 'unit'],
            width: 100,
        },
        {
            title: 'KHOẢNG THAM CHIẾU',
            key: 'reference',
            width: 150,
            render: (_, record) => {
                if (record.test && record.test.min_limit !== null && record.test.max_limit !== null) {
                    return `${record.test.min_limit} - ${record.test.max_limit}`;
                }
                return '-';
            }
        }
    ];

    return (
        <Row gutter={16} className="h-full">
            {/* Cột trái: Worklist */}
            <Col xs={24} md={8} lg={6} className="h-[calc(100vh-100px)] overflow-y-auto" style={{ borderRight: '1px solid #f0f0f0' }}>
                <Card bodyStyle={{ padding: '8px' }} bordered={false}>
                    <div className="flex justify-between items-center mb-2 px-1">
                        <Text strong>Danh sách đã duyệt</Text>
                        <Badge count={orders.length} style={{ backgroundColor: '#52c41a' }} />
                    </div>

                    <div className="flex flex-col gap-2 mt-4">
                        {orders.length === 0 && !loading && (
                            <Text type="secondary" className="text-center italic mt-4">Không có phiếu nào đã duyệt.</Text>
                        )}
                        {orders.map(order => (
                            <div
                                key={order.id}
                                className={`p-3 border rounded-md cursor-pointer transition-colors ${selectedOrder?.id === order.id ? 'bg-green-50 border-green-300' : 'hover:bg-gray-50'}`}
                                onClick={() => handleSelectOrder(order)}
                            >
                                <div className="flex justify-between items-start mb-1">
                                    <Text type="secondary" className="font-mono text-xs">
                                        SID-{order.id.slice(0, 6).toUpperCase()}
                                    </Text>
                                    <Text type="secondary" className="text-xs">
                                        {dayjs(order.order_time).format('HH:mm')}
                                    </Text>
                                </div>
                                <div className="flex items-center gap-2 mb-1">
                                    <Text strong className="text-sm">{order.patient_name || 'Bệnh nhân'}</Text>
                                </div>
                                <div className="flex justify-between items-center mt-2">
                                    <Text type="secondary" className="text-xs">
                                        {order.patient_code || ''}
                                    </Text>
                                    <Badge status="success" text={<span className="text-xs font-medium text-green-600">✓ Đã duyệt</span>} />
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>
            </Col>

            {/* Cột phải: Content */}
            <Col xs={24} md={16} lg={18}>
                <Card bodyStyle={{ padding: '24px' }} className="h-full" bordered={false}>
                    {selectedOrder ? (
                        <div className="flex flex-col space-y-6">
                            {/* Header Bệnh nhân */}
                            <div className="flex justify-between items-start">
                                <div>
                                    <Title level={4} className="!mb-2">{selectedOrder.patient_name || '—'}</Title>
                                    <Space split={<Divider type="vertical" />} className="text-gray-500">
                                        <Text>SID: <span className="font-mono font-medium">SID-{selectedOrder.id.slice(0, 6).toUpperCase()}</span></Text>
                                        <Text>Mã BN: {selectedOrder.patient_code}</Text>
                                        <Text>Chỉ định: {dayjs(selectedOrder.order_time).format('HH:mm DD/MM')}</Text>
                                    </Space>
                                </div>
                                <div className="text-right">
                                    <Badge status="success" text={<span className="font-medium text-lg text-green-600">Đã duyệt</span>} />
                                </div>
                            </div>

                            {/* Bảng thông số */}
                            <Table
                                dataSource={selectedOrder.details || []}
                                columns={columns}
                                rowKey="id"
                                pagination={false}
                                bordered
                                size="middle"
                            />
                        </div>
                    ) : (
                        <div className="flex items-center justify-center h-full text-gray-400 pb-20">
                            <span>Vui lòng chọn phiếu ở danh sách bên trái để xem kết quả.</span>
                        </div>
                    )}
                </Card>
            </Col>
        </Row>
    );
}
