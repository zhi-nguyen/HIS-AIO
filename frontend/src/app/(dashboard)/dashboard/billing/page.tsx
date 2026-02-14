'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Card,
    Table,
    Button,
    Space,
    Tag,
    Typography,
    Select,
    message,
    Modal,
    Descriptions,
    List,
    InputNumber,
    Form,
    Radio,
} from 'antd';
import {
    ReloadOutlined,
    DollarOutlined,
    EyeOutlined,
    PrinterOutlined,
    CheckCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { billingApi } from '@/lib/services';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

/**
 * Billing Page - Quản lý hóa đơn và thanh toán
 * Invoice & Payment Management
 */

interface InvoiceItem {
    id: string;
    item_name: string;
    quantity: number;
    unit_price: number;
    total_price: number;
    is_paid: boolean;
}

interface Invoice {
    id: string;
    invoice_number: string;
    visit: { visit_code: string };
    patient: { patient_code: string; full_name?: string; first_name?: string; last_name?: string };
    status: string;
    total_amount: number;
    discount_amount: number;
    insurance_coverage: number;
    patient_payable: number;
    paid_amount: number;
    created_time: string;
    items?: InvoiceItem[];
}

const statusConfig: Record<string, { color: string; label: string }> = {
    PENDING: { color: 'gold', label: 'Chờ thanh toán' },
    PARTIAL: { color: 'cyan', label: 'Thanh toán một phần' },
    PAID: { color: 'green', label: 'Đã thanh toán' },
    CANCELLED: { color: 'default', label: 'Đã hủy' },
    REFUNDED: { color: 'red', label: 'Đã hoàn tiền' },
};

const paymentMethods = [
    { value: 'CASH', label: 'Tiền mặt' },
    { value: 'CARD', label: 'Thẻ ngân hàng' },
    { value: 'TRANSFER', label: 'Chuyển khoản' },
    { value: 'MOMO', label: 'Ví MoMo' },
    { value: 'VNPAY', label: 'VNPay' },
];

export default function BillingPage() {
    const [invoices, setInvoices] = useState<Invoice[]>([]);
    const [loading, setLoading] = useState(false);
    const [statusFilter, setStatusFilter] = useState<string | undefined>('PENDING');
    const [selectedInvoice, setSelectedInvoice] = useState<Invoice | null>(null);
    const [detailModalOpen, setDetailModalOpen] = useState(false);
    const [paymentModalOpen, setPaymentModalOpen] = useState(false);
    const [paying, setPaying] = useState(false);
    const [form] = Form.useForm();

    // Fetch invoices
    const fetchInvoices = useCallback(async () => {
        setLoading(true);
        try {
            const response = await billingApi.getInvoices({ status: statusFilter });
            setInvoices(response.results || []);
        } catch (error) {
            console.error('Error fetching invoices:', error);
            message.error('Không thể tải danh sách hóa đơn');
        } finally {
            setLoading(false);
        }
    }, [statusFilter]);

    useEffect(() => {
        fetchInvoices();
    }, [fetchInvoices]);

    // View invoice details
    const handleViewDetail = async (invoice: Invoice) => {
        try {
            const detail = await billingApi.getInvoiceById(invoice.id);
            setSelectedInvoice(detail);
            setDetailModalOpen(true);
        } catch (error) {
            console.error('Error fetching invoice detail:', error);
            message.error('Không thể tải chi tiết hóa đơn');
        }
    };

    // Open payment modal
    const handleOpenPayment = (invoice: Invoice) => {
        setSelectedInvoice(invoice);
        form.setFieldsValue({
            amount: invoice.patient_payable - invoice.paid_amount,
            payment_method: 'CASH',
        });
        setPaymentModalOpen(true);
    };

    // Process payment
    const handlePayment = async (values: Record<string, unknown>) => {
        if (!selectedInvoice) return;

        setPaying(true);
        try {
            await billingApi.createPayment({
                invoice: selectedInvoice.id,
                amount: values.amount as number,
                payment_method: values.payment_method as string,
                note: values.note as string,
            });
            message.success('Thanh toán thành công');
            setPaymentModalOpen(false);
            fetchInvoices();
        } catch (error) {
            console.error('Error processing payment:', error);
            message.error('Không thể xử lý thanh toán');
        } finally {
            setPaying(false);
        }
    };

    // Table columns
    const columns: ColumnsType<Invoice> = [
        {
            title: 'Số HĐ',
            dataIndex: 'invoice_number',
            key: 'number',
            width: 130,
            render: (num: string) => <Text strong className="text-blue-600">{num}</Text>,
        },
        {
            title: 'Bệnh nhân',
            key: 'patient',
            render: (_, record) => {
                const patient = record.patient;
                if (!patient) return <Text type="secondary">-</Text>;
                return (
                    <Space orientation="vertical" size={0}>
                        <Text>
                            {patient.full_name ||
                                `${patient.last_name || ''} ${patient.first_name || ''}`}
                        </Text>
                        <Text type="secondary" className="text-xs">{patient.patient_code}</Text>
                    </Space>
                );
            },
        },
        {
            title: 'Tổng tiền',
            dataIndex: 'total_amount',
            key: 'total',
            width: 120,
            render: (amount: number) => (
                <Text>{amount?.toLocaleString('vi-VN')} ₫</Text>
            ),
        },
        {
            title: 'Phải trả',
            dataIndex: 'patient_payable',
            key: 'payable',
            width: 120,
            render: (amount: number) => (
                <Text strong className="text-red-600">{amount?.toLocaleString('vi-VN')} ₫</Text>
            ),
        },
        {
            title: 'Đã trả',
            dataIndex: 'paid_amount',
            key: 'paid',
            width: 120,
            render: (amount: number) => (
                <Text type="success">{amount?.toLocaleString('vi-VN')} ₫</Text>
            ),
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
            width: 180,
            render: (_, record) => (
                <Space>
                    <Button
                        size="small"
                        icon={<EyeOutlined />}
                        onClick={() => handleViewDetail(record)}
                    >
                        Chi tiết
                    </Button>
                    {record.status !== 'PAID' && record.status !== 'CANCELLED' && (
                        <Button
                            size="small"
                            type="primary"
                            icon={<DollarOutlined />}
                            onClick={() => handleOpenPayment(record)}
                        >
                            Thu
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
                    <Title level={3} className="!mb-0">Thanh toán</Title>
                    <Text type="secondary">Quản lý hóa đơn và thu tiền</Text>
                </div>
                <Space>
                    <Select
                        placeholder="Trạng thái"
                        value={statusFilter}
                        onChange={setStatusFilter}
                        allowClear
                        style={{ width: 160 }}
                        options={Object.entries(statusConfig).map(([k, v]) => ({
                            value: k,
                            label: v.label,
                        }))}
                    />
                    <Button icon={<ReloadOutlined />} onClick={fetchInvoices}>
                        Làm mới
                    </Button>
                </Space>
            </div>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-4">
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Chờ thanh toán</Text>
                        <div className="text-2xl font-bold text-orange-500">
                            {invoices.filter(i => i.status === 'PENDING').length}
                        </div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Tổng phải thu</Text>
                        <div className="text-xl font-bold text-red-500">
                            {invoices
                                .filter(i => i.status === 'PENDING' || i.status === 'PARTIAL')
                                .reduce((sum, i) => sum + (i.patient_payable - i.paid_amount), 0)
                                .toLocaleString('vi-VN')} ₫
                        </div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Đã thu hôm nay</Text>
                        <div className="text-2xl font-bold text-green-500">
                            {invoices.filter(i => i.status === 'PAID').length}
                        </div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Tổng đã thu</Text>
                        <div className="text-xl font-bold text-green-600">
                            {invoices
                                .reduce((sum, i) => sum + i.paid_amount, 0)
                                .toLocaleString('vi-VN')} ₫
                        </div>
                    </div>
                </Card>
            </div>

            {/* Main Table */}
            <Card>
                <Table
                    columns={columns}
                    dataSource={invoices}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10, showTotal: (t) => `${t} hóa đơn` }}
                    scroll={{ x: 1000 }}
                />
            </Card>

            {/* Detail Modal */}
            <Modal
                title={`Hóa đơn ${selectedInvoice?.invoice_number}`}
                open={detailModalOpen}
                onCancel={() => setDetailModalOpen(false)}
                footer={
                    <Button icon={<PrinterOutlined />}>In hóa đơn</Button>
                }
                width={700}
            >
                {selectedInvoice && (
                    <div className="space-y-4">
                        <Descriptions size="small" column={2}>
                            <Descriptions.Item label="Ngày tạo">
                                {dayjs(selectedInvoice.created_time).format('HH:mm DD/MM/YYYY')}
                            </Descriptions.Item>
                            <Descriptions.Item label="Trạng thái">
                                <Tag color={statusConfig[selectedInvoice.status]?.color}>
                                    {statusConfig[selectedInvoice.status]?.label}
                                </Tag>
                            </Descriptions.Item>
                            <Descriptions.Item label="Tổng tiền">
                                {selectedInvoice.total_amount?.toLocaleString('vi-VN')} ₫
                            </Descriptions.Item>
                            <Descriptions.Item label="BHYT chi trả">
                                {selectedInvoice.insurance_coverage?.toLocaleString('vi-VN')} ₫
                            </Descriptions.Item>
                            <Descriptions.Item label="Phải trả">
                                <Text strong className="text-red-600">
                                    {selectedInvoice.patient_payable?.toLocaleString('vi-VN')} ₫
                                </Text>
                            </Descriptions.Item>
                            <Descriptions.Item label="Đã thanh toán">
                                <Text type="success">
                                    {selectedInvoice.paid_amount?.toLocaleString('vi-VN')} ₫
                                </Text>
                            </Descriptions.Item>
                        </Descriptions>

                        <List
                            size="small"
                            header={<Text strong>Chi tiết dịch vụ</Text>}
                            dataSource={selectedInvoice.items}
                            renderItem={(item: InvoiceItem) => (
                                <List.Item>
                                    <List.Item.Meta
                                        title={item.item_name}
                                        description={`Đơn giá: ${item.unit_price?.toLocaleString('vi-VN')} ₫`}
                                    />
                                    <Space orientation="vertical" size={0} className="text-right">
                                        <Text>x{item.quantity}</Text>
                                        <Text strong>{item.total_price?.toLocaleString('vi-VN')} ₫</Text>
                                    </Space>
                                </List.Item>
                            )}
                        />
                    </div>
                )}
            </Modal>

            {/* Payment Modal */}
            <Modal
                title="Thanh toán"
                open={paymentModalOpen}
                onCancel={() => setPaymentModalOpen(false)}
                footer={null}
            >
                <Form form={form} layout="vertical" onFinish={handlePayment}>
                    <div className="mb-4 p-3 bg-gray-50 rounded">
                        <Text type="secondary">Số tiền còn phải trả:</Text>
                        <div className="text-xl font-bold text-red-600">
                            {((selectedInvoice?.patient_payable || 0) - (selectedInvoice?.paid_amount || 0)).toLocaleString('vi-VN')} ₫
                        </div>
                    </div>

                    <Form.Item
                        name="amount"
                        label="Số tiền thanh toán"
                        rules={[{ required: true, message: 'Vui lòng nhập số tiền' }]}
                    >
                        <InputNumber
                            className="w-full"
                            formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                            addonAfter="₫"
                        />
                    </Form.Item>

                    <Form.Item
                        name="payment_method"
                        label="Phương thức"
                        rules={[{ required: true }]}
                    >
                        <Radio.Group options={paymentMethods} optionType="button" buttonStyle="solid" />
                    </Form.Item>

                    <Form.Item className="mb-0 text-right">
                        <Button type="primary" htmlType="submit" icon={<CheckCircleOutlined />} loading={paying}>
                            Xác nhận thanh toán
                        </Button>
                    </Form.Item>
                </Form>
            </Modal>
        </div>
    );
}
