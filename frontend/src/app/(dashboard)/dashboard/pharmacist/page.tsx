'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
    Card, Badge, Button, Typography, Tag, Descriptions,
    List, Space, Divider, Tooltip, Empty, notification, Row, Col, Avatar,
} from 'antd';
import {
    MedicineBoxOutlined,
    CheckCircleOutlined,
    CloseCircleOutlined,
    BellOutlined,
    UserOutlined,
    CalendarOutlined,
    FileTextOutlined,
    ClockCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/vi';
import { pharmacyApi } from '@/lib/services';

dayjs.locale('vi');

const { Title, Text, Paragraph } = Typography;

interface MedicationItem {
    name: string;
    quantity: number;
    unit: string;
    usage_instruction: string;
    duration_days?: number;
}

interface PrescriptionEntry {
    id: string;
    prescription_code: string;
    visit_code: string;
    patient_name: string;
    patient_dob?: string;
    patient_gender?: string;
    diagnosis: string;
    note: string;
    medications: MedicationItem[];
    total_price: string;
    timestamp: string;
    event_type: string;
}

// Shape of the raw WebSocket message from the backend
interface WsPayload {
    type: string;
    prescription_id: string;
    prescription_code: string;
    visit_code: string;
    patient_name: string;
    patient_dob?: string;
    patient_gender?: string;
    diagnosis: string;
    note: string;
    medications: MedicationItem[];
    total_price: string;
    event_type: string;
    timestamp: string;
}

const genderLabel: Record<string, string> = { M: 'Nam', F: 'Nữ', O: 'Khác' };

export default function PharmacistPage() {
    const [queue, setQueue] = useState<PrescriptionEntry[]>([]);
    const [selected, setSelected] = useState<PrescriptionEntry | null>(null);
    const [loading, setLoading] = useState<string | null>(null); // prescription_id being acted on
    const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('connecting');
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectRef = useRef<NodeJS.Timeout | null>(null);

    const [api, contextHolder] = notification.useNotification();

    const connectWs = useCallback(() => {
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL
            ? `${process.env.NEXT_PUBLIC_WS_URL}/ws/pharmacist/updates/`
            : `ws://${window.location.hostname}:8000/ws/pharmacist/updates/`;

        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;
        setWsStatus('connecting');

        ws.onopen = () => setWsStatus('connected');

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data) as WsPayload;
                if (data.type === 'pharmacist.prescription_ready' && data.event_type === 'ready') {
                    setQueue(prev => {
                        // Tránh duplicate
                        if (prev.some(p => p.id === data.prescription_id)) return prev;
                        return [
                            {
                                id: data.prescription_id,
                                prescription_code: data.prescription_code,
                                visit_code: data.visit_code,
                                patient_name: data.patient_name,
                                patient_dob: data.patient_dob,
                                patient_gender: data.patient_gender,
                                diagnosis: data.diagnosis,
                                note: data.note,
                                medications: data.medications,
                                total_price: data.total_price,
                                timestamp: data.timestamp,
                                event_type: data.event_type,
                            },
                            ...prev,
                        ];
                    });

                    api.info({
                        message: 'Đơn thuốc mới',
                        description: (
                            <span>
                                <b>{data.patient_name}</b> — {data.prescription_code}
                                <br />
                                {data.medications.length} loại thuốc
                            </span>
                        ),
                        icon: <MedicineBoxOutlined style={{ color: '#1677ff' }} />,
                        duration: 6,
                    });
                }
            } catch {
                /* ignore parse error */
            }
        };

        ws.onclose = () => {
            setWsStatus('disconnected');
            reconnectRef.current = setTimeout(connectWs, 3000);
        };

        ws.onerror = () => setWsStatus('disconnected');
    }, [api]);

    useEffect(() => {
        let isMounted = true;
        const fetchInitialQueue = async () => {
            try {
                const res = await pharmacyApi.getPrescriptions({ status: 'PENDING' }) as any;
                if (!isMounted) return;
                
                const dataArray = res.results || res;
                if (Array.isArray(dataArray)) {
                    const entries: PrescriptionEntry[] = dataArray.map((p: any) => ({
                        id: p.id,
                        prescription_code: p.prescription_code,
                        visit_code: p.visit_code,
                        patient_name: p.patient_name,
                        patient_dob: p.patient_dob,
                        patient_gender: p.patient_gender,
                        diagnosis: p.diagnosis || '',
                        note: p.note || '',
                        medications: (p.details || []).map((d: any) => ({
                            name: d.medication_name,
                            quantity: d.quantity,
                            unit: d.medication_unit,
                            usage_instruction: d.usage_instruction,
                            duration_days: d.duration_days,
                        })),
                        total_price: p.total_price,
                        timestamp: p.prescription_date,
                        event_type: 'ready',
                    }));
                    // Set initial queue without overwriting new WS events that might have arrived
                    setQueue(prev => {
                        const existingIds = new Set(prev.map(item => item.id));
                        const newEntries = entries.filter(e => !existingIds.has(e.id));
                        return [...prev, ...newEntries];
                    });
                }
            } catch (err) {
                console.error('Failed to fetch initial prescriptions', err);
            }
        };

        fetchInitialQueue();
        connectWs();
        
        return () => {
            isMounted = false;
            if (reconnectRef.current) clearTimeout(reconnectRef.current);
            wsRef.current?.close();
        };
    }, [connectWs]);

    const removeFromQueue = (prescriptionId: string) => {
        setQueue(prev => prev.filter(p => p.id !== prescriptionId));
        setSelected(prev => (prev?.id === prescriptionId ? null : prev));
    };

    const handleAction = async (action: 'dispense' | 'refuse') => {
        if (!selected) return;
        setLoading(selected.id);
        try {
            let data: any;
            if (action === 'dispense') {
                data = await pharmacyApi.dispense(selected.id);
            } else {
                data = await pharmacyApi.refuse(selected.id, 'Pharmacist refused');
            }

            api.success({
                message: action === 'dispense' ? 'Cấp thuốc thành công' : 'Đã ghi nhận từ chối',
                description: data.detail || 'Hoàn tất',
                icon: action === 'dispense'
                    ? <CheckCircleOutlined style={{ color: '#52c41a' }} />
                    : <CloseCircleOutlined style={{ color: '#ff4d4f' }} />,
            });
            removeFromQueue(selected.id);
        } catch (error: any) {
            api.error({
                message: 'Thao tác thất bại',
                description: error.response?.data?.detail || error.message || 'Có lỗi xảy ra',
            });
        } finally {
            setLoading(null);
        }
    };

    const wsStatusColor = wsStatus === 'connected' ? '#52c41a' : wsStatus === 'connecting' ? '#faad14' : '#ff4d4f';
    const wsStatusLabel = wsStatus === 'connected' ? 'Đang kết nối' : wsStatus === 'connecting' ? 'Đang kết nối...' : 'Mất kết nối';

    return (
        <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', background: '#f5f5f5' }}>
            {contextHolder}

            {/* Header */}
            <div style={{
                background: '#fff',
                borderBottom: '1px solid #e8e8e8',
                padding: '12px 24px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexShrink: 0,
            }}>
                <Space align="center">
                    <MedicineBoxOutlined style={{ fontSize: 22, color: '#1677ff' }} />
                    <Title level={4} style={{ margin: 0 }}>Phòng Dược — Cấp phát thuốc</Title>
                    <Badge count={queue.length} style={{ backgroundColor: '#1677ff' }} />
                </Space>
                <Space>
                    <BellOutlined style={{ color: wsStatusColor }} />
                    <Text style={{ color: wsStatusColor, fontSize: 12 }}>{wsStatusLabel}</Text>
                </Space>
            </div>

            {/* Body */}
            <Row style={{ flex: 1, overflow: 'hidden', padding: 16, gap: 0 }} wrap={false}>
                {/* Left: Queue */}
                <Col
                    flex="340px"
                    style={{
                        overflowY: 'auto',
                        paddingRight: 12,
                        borderRight: '1px solid #e8e8e8',
                        background: '#fff',
                        borderRadius: 8,
                    }}
                >
                    <div style={{ padding: '12px 16px', borderBottom: '1px solid #f0f0f0' }}>
                        <Text strong style={{ fontSize: 14 }}>Hàng chờ cấp thuốc</Text>
                    </div>
                    {queue.length === 0 ? (
                        <Empty
                            style={{ marginTop: 60 }}
                            description="Không có đơn thuốc chờ cấp phát"
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                        />
                    ) : (
                        <List
                            dataSource={queue}
                            renderItem={(entry, index) => {
                                const isActive = selected?.id === entry.id;
                                return (
                                    <List.Item
                                        key={entry.id}
                                        style={{
                                            cursor: 'pointer',
                                            padding: '12px 16px',
                                            background: isActive ? '#e6f4ff' : 'transparent',
                                            borderLeft: isActive ? '3px solid #1677ff' : '3px solid transparent',
                                            transition: 'all .2s',
                                        }}
                                        onClick={() => setSelected(entry)}
                                    >
                                        <Space direction="vertical" size={2} style={{ width: '100%' }}>
                                            <Space>
                                                <Avatar
                                                    size={32}
                                                    icon={<UserOutlined />}
                                                    style={{ background: '#1677ff', flexShrink: 0 }}
                                                />
                                                <div>
                                                    <Text strong>{entry.patient_name}</Text>
                                                    <br />
                                                    <Text type="secondary" style={{ fontSize: 12 }}>
                                                        {entry.visit_code} · {entry.prescription_code}
                                                    </Text>
                                                </div>
                                            </Space>
                                            <Space wrap style={{ marginTop: 4 }}>
                                                <Tag color="blue" style={{ fontSize: 11 }}>
                                                    {entry.medications.length} loại thuốc
                                                </Tag>
                                                <Text type="secondary" style={{ fontSize: 11 }}>
                                                    <ClockCircleOutlined /> {dayjs(entry.timestamp).format('HH:mm')}
                                                </Text>
                                            </Space>
                                        </Space>
                                    </List.Item>
                                );
                            }}
                        />
                    )}
                </Col>

                {/* Right: Detail panel */}
                <Col
                    flex="1"
                    style={{
                        overflowY: 'auto',
                        paddingLeft: 16,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 12,
                    }}
                >
                    {!selected ? (
                        <div style={{
                            flex: 1,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            background: '#fff',
                            borderRadius: 8,
                        }}>
                            <Empty description="Chọn đơn thuốc từ danh sách để xem chi tiết" />
                        </div>
                    ) : (
                        <>
                            {/* Patient info */}
                            <Card
                                size="small"
                                title={
                                    <Space>
                                        <UserOutlined />
                                        <span>Thông tin bệnh nhân</span>
                                    </Space>
                                }
                            >
                                <Descriptions column={2} size="small">
                                    <Descriptions.Item label="Họ tên">
                                        <Text strong>{selected.patient_name}</Text>
                                    </Descriptions.Item>
                                    <Descriptions.Item label="Giới tính">
                                        {genderLabel[selected.patient_gender ?? ''] ?? '—'}
                                    </Descriptions.Item>
                                    <Descriptions.Item label="Ngày sinh">
                                        <CalendarOutlined /> {selected.patient_dob
                                            ? dayjs(selected.patient_dob).format('DD/MM/YYYY')
                                            : '—'}
                                    </Descriptions.Item>
                                    <Descriptions.Item label="Mã lượt khám">
                                        {selected.visit_code}
                                    </Descriptions.Item>
                                    <Descriptions.Item label="Mã đơn thuốc" span={2}>
                                        <Tag color="blue">{selected.prescription_code}</Tag>
                                    </Descriptions.Item>
                                </Descriptions>
                                {selected.diagnosis && (
                                    <>
                                        <Divider style={{ margin: '8px 0' }} />
                                        <Text type="secondary" style={{ fontSize: 12 }}>Chẩn đoán: </Text>
                                        <Text>{selected.diagnosis}</Text>
                                    </>
                                )}
                            </Card>

                            {/* Medication list */}
                            <Card
                                size="small"
                                title={
                                    <Space>
                                        <FileTextOutlined />
                                        <span>Danh sách thuốc</span>
                                        <Tag color="blue">{selected.medications.length} loại</Tag>
                                    </Space>
                                }
                            >
                                {selected.medications.map((med, idx) => (
                                    <div
                                        key={idx}
                                        style={{
                                            padding: '10px 12px',
                                            marginBottom: 8,
                                            background: '#fafafa',
                                            borderRadius: 6,
                                            border: '1px solid #f0f0f0',
                                        }}
                                    >
                                        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                                            <Text strong>{med.name}</Text>
                                            <Tag color="geekblue">{med.quantity} {med.unit}</Tag>
                                        </Space>
                                        <div style={{ marginTop: 4 }}>
                                            <Text type="secondary" style={{ fontSize: 12 }}>
                                                Cách dùng: {med.usage_instruction}
                                            </Text>
                                            {med.duration_days && (
                                                <Text type="secondary" style={{ fontSize: 12, marginLeft: 12 }}>
                                                    · {med.duration_days} ngày
                                                </Text>
                                            )}
                                        </div>
                                    </div>
                                ))}

                                {selected.note && (
                                    <>
                                        <Divider style={{ margin: '8px 0' }} />
                                        <Text type="secondary" style={{ fontSize: 12 }}>Lời dặn bác sĩ: </Text>
                                        <Paragraph style={{ fontSize: 13, marginBottom: 0 }}>
                                            {selected.note}
                                        </Paragraph>
                                    </>
                                )}
                            </Card>

                            {/* Action buttons */}
                            <Card size="small">
                                <Space style={{ width: '100%', justifyContent: 'flex-end' }} size="middle">
                                    <Tooltip title="Bệnh nhân từ chối nhận thuốc — hoàn thành khám">
                                        <Button
                                            danger
                                            icon={<CloseCircleOutlined />}
                                            size="large"
                                            loading={loading === selected.id}
                                            disabled={!!loading}
                                            onClick={() => handleAction('refuse')}
                                        >
                                            Từ chối nhận thuốc
                                        </Button>
                                    </Tooltip>
                                    <Button
                                        type="primary"
                                        icon={<CheckCircleOutlined />}
                                        size="large"
                                        loading={loading === selected.id}
                                        disabled={!!loading}
                                        onClick={() => handleAction('dispense')}
                                        style={{ background: '#52c41a', borderColor: '#52c41a' }}
                                    >
                                        Cấp thuốc
                                    </Button>
                                </Space>
                            </Card>
                        </>
                    )}
                </Col>
            </Row>
        </div>
    );
}
