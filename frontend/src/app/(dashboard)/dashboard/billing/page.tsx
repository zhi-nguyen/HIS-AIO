'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    Button, Space, Tag, Typography, Select, Descriptions,
    InputNumber, Form, Radio, Divider, Badge, Avatar,
    Table, Empty, Spin, notification, Tooltip, Card,
} from 'antd';
import {
    ReloadOutlined, PrinterOutlined, CheckCircleOutlined,
    DollarOutlined, UserOutlined, ClockCircleOutlined,
    SafetyOutlined, FileTextOutlined, BellOutlined,
} from '@ant-design/icons';
import { billingApi, insuranceApi } from '@/lib/services';
import type { InsuranceLookupResult } from '@/lib/services';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

/**
 * Billing Page — Thu ngân
 * Layout: 3 cột dọc có thể cuộn độc lập
 * Col 1: Hàng chờ
 * Col 2: Chi tiết chỉ định / đơn thuốc
 * Col 3: Tính tiền + thanh toán
 */

/* ─── Types ─── */
interface InvoiceItem {
    id: string;
    item_name: string;
    quantity: number;
    unit_price: number;
    total_price: number;
    insurance_covered: number;
    related_order_type?: string;
    is_paid: boolean;
}

interface Invoice {
    id: string;
    invoice_number: string;
    visit: string; // UUID - plain FK field
    visit_detail?: {
        id?: string;
        visit_code: string;
        // Insurance snapshot được lưu tại lúc đăng ký Visit
        insurance_number?: string | null;
        insurance_benefit_rate?: number | null;  // 0-100, e.g. 80 = 80%
        insurance_card_expire?: string | null;
    };
    patient: {
        id?: string;
        patient_code: string;
        full_name?: string;
        first_name?: string;
        last_name?: string;
        insurance_number?: string;
    };
    status: string;
    total_amount: number;
    discount_amount: number;
    insurance_coverage: number;
    patient_payable: number;
    paid_amount: number;
    created_time: string;
    items?: InvoiceItem[];
}

/* ─── Config ─── */
const statusConfig: Record<string, { color: string; label: string }> = {
    PENDING:   { color: 'gold',    label: 'Chờ thanh toán' },
    PARTIAL:   { color: 'cyan',    label: 'TT một phần' },
    PAID:      { color: 'green',   label: 'Đã thanh toán' },
    CANCELLED: { color: 'default', label: 'Đã hủy' },
    REFUNDED:  { color: 'red',     label: 'Đã hoàn tiền' },
};

const paymentMethods = [
    { value: 'CASH',     label: 'Tiền mặt' },
    { value: 'CARD',     label: 'Thẻ NH' },
    { value: 'TRANSFER', label: 'CK' },
    { value: 'MOMO',     label: 'MoMo' },
    { value: 'VNPAY',    label: 'VNPay' },
];

const vnd = (n: number | undefined) =>
    n != null ? `${n.toLocaleString('vi-VN')} ₫` : '—';

/* ─── Component ─── */
export default function BillingPage() {
    const [invoices, setInvoices]           = useState<Invoice[]>([]);
    const [loading, setLoading]             = useState(false);
    const [statusFilter, setStatusFilter]   = useState<string>('PENDING');
    const [selected, setSelected]           = useState<Invoice | null>(null);
    const [paying, setPaying]               = useState(false);
    const [wsStatus, setWsStatus]           = useState<'connected' | 'disconnected'>('disconnected');
    const wsRef                             = useRef<WebSocket | null>(null);

    // Insurance state
    const [insurance, setInsurance]         = useState<InsuranceLookupResult | null>(null);
    const [insuranceLoading, setInsLoading] = useState(false);
    // Computed pricing
    const [computedCoverage, setComputed]   = useState<number>(0);   // amount covered by insurance
    const [benefitRate, setBenefitRate]     = useState<number>(0);   // 0‒1 fraction

    const [form] = Form.useForm();
    const [api, contextHolder] = notification.useNotification();

    /* ── Fetch list ── */
    const fetchInvoices = useCallback(async () => {
        setLoading(true);
        try {
            const res = await billingApi.getInvoices({ status: statusFilter || undefined });
            setInvoices(res.results || []);
        } catch {
            api.error({ message: 'Không thể tải danh sách hóa đơn' });
        } finally {
            setLoading(false);
        }
    }, [statusFilter, api]);

    useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

    /* ── WebSocket ── */
    useEffect(() => {
        const host = process.env.NEXT_PUBLIC_API_URL
            ? new URL(process.env.NEXT_PUBLIC_API_URL).host
            : 'localhost:8000';
        const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${proto}//${host}/ws/billing/`);
        wsRef.current = ws;

        ws.onopen  = () => setWsStatus('connected');
        ws.onclose = () => setWsStatus('disconnected');
        ws.onmessage = (ev) => {
            try {
                const d = JSON.parse(ev.data);
                // Consumer gửi {type: 'invoice_updated'} hoặc {type: 'payment_done'}
                // (cũng hỗ trợ format cũ {action: '...'})
                const msgType = d.type || d.action || '';
                if (msgType === 'invoice_updated' || msgType === 'updated' || msgType === 'new_order') {
                    fetchInvoices();
                    if (d.action === 'paid') {
                        api.success({ message: 'Thanh toán hoàn tất', description: `Hóa đơn đã được thanh toán.`, duration: 3 });
                    }
                } else if (msgType === 'payment_done') {
                    // Thanh toán xong → xóa khỏi hàng chờ PENDING
                    fetchInvoices();
                }
            } catch { /* noop */ }
        };
        return () => ws.close();
    }, [fetchInvoices]);

    /* ── Select invoice & lookup insurance ── */
    const handleSelect = async (inv: Invoice) => {
        try {
            const detail = await billingApi.getInvoiceById(inv.id) as Invoice;
            setSelected(detail);
            setInsurance(null);
            setComputed(0);
            setBenefitRate(0);

            // Reset form
            form.setFieldsValue({
                amount: detail.patient_payable - detail.paid_amount,
                payment_method: 'CASH',
            });

            // 1. Ưu tiên dùng dữ liệu BHYT đã snapshot vào Visit tại lúc đăng ký
            const snapshotRate = detail.visit_detail?.insurance_benefit_rate;
            const snapshotIns  = detail.visit_detail?.insurance_number;

            if (snapshotRate != null && snapshotIns) {
                // Có snapshot → dùng ngay, không cần tra lại cổng BH
                const rate = snapshotRate / 100;
                setBenefitRate(rate);
                const coverage = Math.round(detail.total_amount * rate);
                setComputed(coverage);
                form.setFieldsValue({ amount: Math.max(0, detail.total_amount - coverage - (detail.discount_amount || 0)) });

                // Tạo insurance object giả để hiển thị UI
                setInsurance({
                    status: 'success',
                    data: {
                        patient_name: detail.patient?.full_name || '',
                        insurance_code: snapshotIns,
                        dob: '',
                        gender: 'male',
                        address: '',
                        card_issue_date: '',
                        card_expire_date: detail.visit_detail?.insurance_card_expire || '',
                        benefit_rate: snapshotRate,
                        benefit_code: '',
                        registered_hospital_code: '',
                        registered_hospital_name: '',
                        is_5_years_consecutive: false,
                    },
                });
            } else {
                // 2. Fallback: tra cứu realtime nếu Visit cũ chưa có snapshot
                const insNum = detail.visit_detail?.insurance_number || detail.patient?.insurance_number;
                if (insNum) {
                    setInsLoading(true);
                    try {
                        const result = await insuranceApi.lookup(insNum);
                        setInsurance(result);
                        if (result.status === 'success' && result.data) {
                            const rate = result.data.benefit_rate / 100;
                            setBenefitRate(rate);
                            const coverage = Math.round(detail.total_amount * rate);
                            setComputed(coverage);
                            const patientPays = detail.total_amount - coverage - (detail.discount_amount || 0);
                            form.setFieldsValue({ amount: Math.max(0, patientPays) });
                        }
                    } catch {
                        // ignore — giữ nguyên giá gốc
                    } finally {
                        setInsLoading(false);
                    }
                }
            }
        } catch {
            api.error({ message: 'Không thể tải chi tiết hóa đơn' });
        }
    };

    /* ── Payment ── */
    const handlePayment = async (values: Record<string, unknown>) => {
        if (!selected) return;
        setPaying(true);
        try {
            await billingApi.createPayment(selected.id, {
                amount:             values.amount as number,
                payment_method:     values.payment_method as string,
                // Gửi coverage để backend cập nhật patient_payable trước khi xác định PAID/PARTIAL
                insurance_coverage: computedCoverage > 0 ? computedCoverage : undefined,
                note:               values.note as string,
            });
            api.success({ message: 'Thanh toán thành công!' });
            fetchInvoices();
            const updated = await billingApi.getInvoiceById(selected.id) as Invoice;
            setSelected(updated);
            form.setFieldsValue({ amount: Math.max(0, updated.patient_payable - updated.paid_amount) });
        } catch {
            api.error({ message: 'Không thể xử lý thanh toán' });
        } finally {
            setPaying(false);
        }
    };

    /* ── Computed values ── */
    const totalAmount  = selected?.total_amount  ?? 0;
    const discount     = selected?.discount_amount ?? 0;
    const coverage     = benefitRate > 0 ? computedCoverage : (selected?.insurance_coverage ?? 0);
    const patientDue   = Math.max(0, totalAmount - coverage - discount);
    const alreadyPaid  = selected?.paid_amount ?? 0;
    const stillOwed    = Math.max(0, patientDue - alreadyPaid);

    /* ─── RENDER ─── */
    const HEADER_H = 56; // header height from layout
    const colH = `calc(100vh - ${HEADER_H}px - 48px)`;  // full minus layout header & padding

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: `calc(100vh - ${HEADER_H}px)`, background: '#f5f7fa' }}>
            {contextHolder}

            {/* ── Top bar ── */}
            <div style={{
                background: '#fff',
                borderBottom: '1px solid #e8e8e8',
                padding: '10px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexShrink: 0,
            }}>
                <Space align="center">
                    <DollarOutlined style={{ fontSize: 20, color: '#1677ff' }} />
                    <Title level={4} style={{ margin: 0 }}>Thu ngân — Thanh toán viện phí</Title>
                    <Badge count={invoices.filter(i => i.status === 'PENDING').length}
                        style={{ backgroundColor: '#faad14' }} />
                </Space>
                <Space>
                    <BellOutlined style={{ color: wsStatus === 'connected' ? '#52c41a' : '#ff4d4f' }} />
                    <Text style={{ fontSize: 12, color: wsStatus === 'connected' ? '#52c41a' : '#ff4d4f' }}>
                        {wsStatus === 'connected' ? 'Realtime' : 'Offline'}
                    </Text>
                    <Select
                        value={statusFilter}
                        onChange={v => { setStatusFilter(v); setSelected(null); }}
                        style={{ width: 150 }}
                        options={[
                            { value: '',          label: 'Tất cả' },
                            { value: 'PENDING',   label: 'Chờ TT' },
                            { value: 'PARTIAL',   label: 'TT một phần' },
                            { value: 'PAID',      label: 'Đã TT' },
                        ]}
                    />
                    <Tooltip title="Làm mới">
                        <Button icon={<ReloadOutlined />} onClick={fetchInvoices} loading={loading} />
                    </Tooltip>
                </Space>
            </div>

            {/* ── 3-column body ── */}
            <div style={{ display: 'flex', flex: 1, overflow: 'hidden', padding: 12, gap: 12 }}>

                {/* ═══ Col 1: Hàng chờ ═══ */}
                <div style={{
                    width: 300,
                    flexShrink: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    background: '#fff',
                    borderRadius: 8,
                    border: '1px solid #e8e8e8',
                    overflow: 'hidden',
                }}>
                    <div style={{ padding: '10px 14px', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
                        <Text strong style={{ fontSize: 13 }}>
                            <ClockCircleOutlined style={{ marginRight: 6, color: '#faad14' }} />
                            Hàng chờ thanh toán
                        </Text>
                    </div>
                    <div style={{ overflowY: 'auto', flex: 1 }}>
                        {loading ? (
                            <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
                        ) : invoices.length === 0 ? (
                            <Empty style={{ marginTop: 40 }} description="Không có bệnh nhân chờ"
                                image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        ) : invoices.map(inv => {
                            const name = inv.patient?.full_name
                                || `${inv.patient?.last_name || ''} ${inv.patient?.first_name || ''}`.trim()
                                || 'Chưa rõ';
                            const isActive = selected?.id === inv.id;
                            return (
                                <div
                                    key={inv.id}
                                    onClick={() => handleSelect(inv)}
                                    style={{
                                        padding: '10px 14px',
                                        cursor: 'pointer',
                                        borderLeft: isActive ? '3px solid #1677ff' : '3px solid transparent',
                                        background: isActive ? '#e6f4ff' : 'transparent',
                                        borderBottom: '1px solid #f5f5f5',
                                        transition: 'background .15s',
                                    }}
                                >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                        <Space size={8}>
                                            <Avatar size={30} icon={<UserOutlined />}
                                                style={{ background: isActive ? '#1677ff' : '#8c8c8c', flexShrink: 0 }} />
                                            <div>
                                                <Text strong style={{ fontSize: 13, color: isActive ? '#1677ff' : undefined }}>
                                                    {name}
                                                </Text>
                                                <br />
                                                <Text type="secondary" style={{ fontSize: 11 }}>{inv.invoice_number}</Text>
                                            </div>
                                        </Space>
                                        <Tag color={statusConfig[inv.status]?.color || 'default'} style={{ fontSize: 11 }}>
                                            {statusConfig[inv.status]?.label || inv.status}
                                        </Tag>
                                    </div>
                                    <div style={{ marginTop: 6, display: 'flex', justifyContent: 'space-between' }}>
                                        <Text type="secondary" style={{ fontSize: 11 }}>
                                            {dayjs(inv.created_time).format('HH:mm')}
                                        </Text>
                                        <Text strong style={{ fontSize: 12, color: '#cf1322' }}>
                                            {vnd(inv.patient_payable)}
                                        </Text>
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* ═══ Col 2: Chi tiết dịch vụ / đơn thuốc ═══ */}
                <div style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    background: '#fff',
                    borderRadius: 8,
                    border: '1px solid #e8e8e8',
                    overflow: 'hidden',
                    minWidth: 0,
                }}>
                    <div style={{ padding: '10px 14px', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
                        <Text strong style={{ fontSize: 13 }}>
                            <FileTextOutlined style={{ marginRight: 6, color: '#1677ff' }} />
                            Chi tiết dịch vụ — Đơn thuốc
                        </Text>
                        {selected && (
                            <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
                                {selected.invoice_number} · {selected.visit_detail?.visit_code}
                            </Text>
                        )}
                    </div>
                    <div style={{ overflowY: 'auto', flex: 1, padding: '0 0 8px' }}>
                        {!selected ? (
                            <Empty style={{ marginTop: 60 }} description="Chọn bệnh nhân từ hàng chờ"
                                image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        ) : (
                            <>
                                {/* Patient info */}
                                <div style={{ padding: '8px 14px', borderBottom: '1px solid #f5f5f5' }}>
                                    <Descriptions size="small" column={2}>
                                        <Descriptions.Item label="Bệnh nhân">
                                            <Text strong>
                                                {selected.patient?.full_name
                                                    || `${selected.patient?.last_name || ''} ${selected.patient?.first_name || ''}`}
                                            </Text>
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Mã BN">
                                            {selected.patient?.patient_code}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Ngày lập HĐ" span={2}>
                                            {dayjs(selected.created_time).format('DD/MM/YYYY HH:mm')}
                                        </Descriptions.Item>
                                    </Descriptions>
                                </div>

                                {/* Items table */}
                                <div style={{ padding: '8px 14px' }}>
                                    <Table
                                        size="small"
                                        dataSource={selected.items}
                                        rowKey="id"
                                        pagination={false}
                                        columns={[
                                            {
                                                title: 'Tên dịch vụ / thuốc',
                                                dataIndex: 'item_name',
                                                key: 'name',
                                                render: (v: string, row: InvoiceItem) => (
                                                    <Space size={4}>
                                                        <span>{v}</span>
                                                        {row.related_order_type === 'PRESCRIPTION' && (
                                                            <Tag color="purple" style={{ fontSize: 10 }}>Thuốc</Tag>
                                                        )}
                                                    </Space>
                                                ),
                                            },
                                            { title: 'SL', dataIndex: 'quantity', key: 'qty', width: 50, align: 'center' },
                                            {
                                                title: 'Đơn giá',
                                                dataIndex: 'unit_price',
                                                key: 'price',
                                                width: 110,
                                                align: 'right',
                                                render: (v: number) => vnd(v),
                                            },
                                            {
                                                title: 'Thành tiền',
                                                dataIndex: 'total_price',
                                                key: 'total',
                                                align: 'right',
                                                width: 120,
                                                render: (v: number) => <Text strong>{vnd(v)}</Text>,
                                            },
                                        ]}
                                        summary={() => (
                                            <Table.Summary.Row>
                                                <Table.Summary.Cell index={0} colSpan={3}>
                                                    <Text strong>Tổng</Text>
                                                </Table.Summary.Cell>
                                                <Table.Summary.Cell index={1} align="right">
                                                    <Text strong>{vnd(totalAmount)}</Text>
                                                </Table.Summary.Cell>
                                            </Table.Summary.Row>
                                        )}
                                    />
                                </div>
                            </>
                        )}
                    </div>
                </div>

                {/* ═══ Col 3: Tính tiền + Thanh toán ═══ */}
                <div style={{
                    width: 320,
                    flexShrink: 0,
                    display: 'flex',
                    flexDirection: 'column',
                    background: '#fff',
                    borderRadius: 8,
                    border: '1px solid #e8e8e8',
                    overflow: 'hidden',
                }}>
                    <div style={{ padding: '10px 14px', borderBottom: '1px solid #f0f0f0', flexShrink: 0 }}>
                        <Text strong style={{ fontSize: 13 }}>
                            <DollarOutlined style={{ marginRight: 6, color: '#52c41a' }} />
                            Tính tiền &amp; Thanh toán
                        </Text>
                    </div>
                    <div style={{ overflowY: 'auto', flex: 1, padding: '10px 14px' }}>
                        {!selected ? (
                            <Empty style={{ marginTop: 60 }} description="Chọn bệnh nhân để tính tiền"
                                image={Empty.PRESENTED_IMAGE_SIMPLE} />
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>

                                {/* Insurance block */}
                                <Card
                                    size="small"
                                    title={
                                        <Space>
                                            <SafetyOutlined style={{ color: '#1677ff' }} />
                                            <span>Bảo hiểm y tế</span>
                                            {insuranceLoading && <Spin size="small" />}
                                        </Space>
                                    }
                                    style={{ borderColor: '#d6e4ff' }}
                                >
                                    {!selected.patient?.insurance_number ? (
                                        <Text type="secondary">Bệnh nhân không có thẻ BHYT — trả 100%</Text>
                                    ) : insurance?.status === 'success' && insurance.data ? (
                                        <Descriptions size="small" column={1}>
                                            <Descriptions.Item label="Mã thẻ">
                                                <Text copyable>{insurance.data.insurance_code}</Text>
                                            </Descriptions.Item>
                                            <Descriptions.Item label="Mức hưởng">
                                                <Tag color="green">{insurance.data.benefit_rate}%</Tag>
                                            </Descriptions.Item>
                                            <Descriptions.Item label="HSD">
                                                {insurance.data.card_expire_date}
                                            </Descriptions.Item>
                                            <Descriptions.Item label="Nơi đăng ký KCB">
                                                <Text ellipsis style={{ maxWidth: 200 }}>
                                                    {insurance.data.registered_hospital_name}
                                                </Text>
                                            </Descriptions.Item>
                                        </Descriptions>
                                    ) : insurance?.status === 'expired' ? (
                                        <Tag color="red">Thẻ BHYT đã hết hạn — trả 100%</Tag>
                                    ) : insurance?.status === 'not_found' ? (
                                        <Tag color="orange">Không tìm thấy thẻ BHYT — trả 100%</Tag>
                                    ) : selected.patient?.insurance_number ? (
                                        <Text type="secondary">Mã thẻ: {selected.patient.insurance_number}</Text>
                                    ) : null}
                                </Card>

                                {/* Cost breakdown */}
                                <div style={{ background: '#f6ffed', borderRadius: 6, padding: '10px 12px', border: '1px solid #b7eb8f' }}>
                                    <Text strong style={{ display: 'block', marginBottom: 8 }}>Chi tiết chi phí</Text>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                        <Text type="secondary">Tổng viện phí:</Text>
                                        <Text>{vnd(totalAmount)}</Text>
                                    </div>
                                    {coverage > 0 && (
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                            <Text type="secondary">
                                                BHYT chi trả ({benefitRate > 0 ? `${Math.round(benefitRate * 100)}%` : ''}):
                                            </Text>
                                            <Text style={{ color: '#52c41a' }}>- {vnd(coverage)}</Text>
                                        </div>
                                    )}
                                    {discount > 0 && (
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                            <Text type="secondary">Giảm giá:</Text>
                                            <Text style={{ color: '#52c41a' }}>- {vnd(discount)}</Text>
                                        </div>
                                    )}
                                    <Divider style={{ margin: '8px 0' }} />
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <Text strong>Bệnh nhân phải trả:</Text>
                                        <Text strong style={{ fontSize: 18, color: '#cf1322' }}>{vnd(patientDue)}</Text>
                                    </div>
                                    {alreadyPaid > 0 && (
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                                            <Text type="secondary">Đã thanh toán:</Text>
                                            <Text style={{ color: '#52c41a' }}>{vnd(alreadyPaid)}</Text>
                                        </div>
                                    )}
                                    {stillOwed > 0 && (
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
                                            <Text style={{ color: '#fa8c16' }} strong>Còn nợ:</Text>
                                            <Text style={{ color: '#fa8c16' }} strong>{vnd(stillOwed)}</Text>
                                        </div>
                                    )}
                                </div>

                                {/* Payment form */}
                                {selected.status !== 'PAID' && selected.status !== 'CANCELLED' ? (
                                    <Form form={form} layout="vertical" onFinish={handlePayment}>
                                        <Form.Item
                                            name="amount"
                                            label="Số tiền nhận"
                                            rules={[{ required: true, message: 'Nhập số tiền' }]}
                                        >
                                            <InputNumber
                                                style={{ width: '100%' }}
                                                size="large"
                                                min={0}
                                                formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                                                addonAfter="₫"
                                            />
                                        </Form.Item>

                                        <Form.Item
                                            name="payment_method"
                                            label="Hình thức"
                                            rules={[{ required: true }]}
                                        >
                                            <Radio.Group
                                                options={paymentMethods}
                                                optionType="button"
                                                buttonStyle="solid"
                                                style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}
                                            />
                                        </Form.Item>

                                        <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
                                            <Tooltip title="In bản nháp">
                                                <Button icon={<PrinterOutlined />}>Bản nháp</Button>
                                            </Tooltip>
                                            <Button
                                                type="primary"
                                                htmlType="submit"
                                                icon={<CheckCircleOutlined />}
                                                loading={paying}
                                                size="large"
                                                style={{ background: '#52c41a', borderColor: '#52c41a' }}
                                            >
                                                Thu tiền
                                            </Button>
                                        </Space>
                                    </Form>
                                ) : (
                                    <div style={{ textAlign: 'center', padding: 24 }}>
                                        <CheckCircleOutlined style={{ fontSize: 40, color: '#52c41a' }} />
                                        <br /><br />
                                        <Text strong style={{ fontSize: 16, color: '#52c41a' }}>
                                            Hóa đơn đã thanh toán
                                        </Text>
                                        <br /><br />
                                        <Button type="primary" icon={<PrinterOutlined />}>In biên lai</Button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

            </div>
        </div>
    );
}
