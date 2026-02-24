'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Card,
    List,
    Button,
    Space,
    Tag,
    message,
    Typography,
    Badge,
    Select,
    Empty,
    Spin,
    Avatar,
    Modal,
    Input,
    Tabs,
    Tooltip,
    Statistic,
    Row,
    Col,
    Divider,
} from 'antd';
import {
    SoundOutlined,
    CheckOutlined,
    ForwardOutlined,
    ReloadOutlined,
    UserOutlined,
    ClockCircleOutlined,
    ThunderboltOutlined,
    CalendarOutlined,
    TeamOutlined,
    AlertOutlined,
    MedicineBoxOutlined,
    QrcodeOutlined,
} from '@ant-design/icons';
import { qmsApi } from '@/lib/services';
import type {
    ServiceStation,
    CalledPatient,
    QueueBoardEntry,
    QueueSourceType,
} from '@/types';

const { Title, Text } = Typography;

// ============================================================================
// Cấu hình hiển thị cho từng loại nguồn
// ============================================================================

const sourceConfig: Record<QueueSourceType, { color: string; icon: React.ReactNode; label: string; tagColor: string }> = {
    EMERGENCY: {
        color: '#ff4d4f',
        icon: <ThunderboltOutlined />,
        label: 'Cấp cứu',
        tagColor: 'red',
    },
    ONLINE_BOOKING: {
        color: '#1890ff',
        icon: <CalendarOutlined />,
        label: 'Đặt lịch',
        tagColor: 'blue',
    },
    WALK_IN: {
        color: '#8c8c8c',
        icon: <TeamOutlined />,
        label: 'Vãng lai',
        tagColor: 'default',
    },
};

const priorityLabel = (priority: number): { text: string; color: string } => {
    if (priority >= 100) return { text: 'CẤP CỨU', color: 'red' };
    if (priority >= 7) return { text: 'Đúng giờ', color: 'green' };
    if (priority >= 3) return { text: 'Trễ nhẹ', color: 'gold' };
    return { text: 'Thường', color: 'default' };
};

const statusConfig: Record<string, { color: string; label: string }> = {
    WAITING: { color: 'gold', label: 'Đang chờ' },
    CALLED: { color: 'blue', label: 'Đã gọi' },
    IN_PROGRESS: { color: 'processing', label: 'Đang phục vụ' },
    COMPLETED: { color: 'success', label: 'Hoàn thành' },
    SKIPPED: { color: 'default', label: 'Bỏ qua' },
    NO_SHOW: { color: 'error', label: 'Không có mặt' },
};

// ============================================================================
// Component chính
// ============================================================================

export default function QMSPage() {
    // --- State ---
    const [stations, setStations] = useState<ServiceStation[]>([]);
    const [selectedStation, setSelectedStation] = useState<string | null>(null);
    const [currentServing, setCurrentServing] = useState<CalledPatient | null>(null);
    const [waitingList, setWaitingList] = useState<QueueBoardEntry[]>([]);
    const [totalWaiting, setTotalWaiting] = useState(0);
    const [estimatedWait, setEstimatedWait] = useState(0);
    const [loading, setLoading] = useState(false);
    const [callLoading, setCallLoading] = useState(false);

    // Walk-in modal
    const [walkinModal, setWalkinModal] = useState(false);
    const [walkinPatientId, setWalkinPatientId] = useState('');
    const [walkinReason, setWalkinReason] = useState('');
    const [walkinLoading, setWalkinLoading] = useState(false);

    // Emergency modal
    const [emergencyModal, setEmergencyModal] = useState(false);
    const [emergencyPatientId, setEmergencyPatientId] = useState('');
    const [emergencyReason, setEmergencyReason] = useState('');
    const [emergencyLoading, setEmergencyLoading] = useState(false);

    // Kiosk modal
    const [kioskModal, setKioskModal] = useState(false);
    const [kioskAppointmentId, setKioskAppointmentId] = useState('');
    const [kioskLoading, setKioskLoading] = useState(false);

    // --- Fetch stations ---
    const fetchStations = useCallback(async () => {
        try {
            const data = await qmsApi.getStations();
            setStations(data);
            if (data.length > 0 && !selectedStation) {
                setSelectedStation(data[0].id);
            }
        } catch (error) {
            console.error('Error fetching stations:', error);
        }
    }, [selectedStation]);

    // --- Fetch queue board ---
    const fetchQueueBoard = useCallback(async () => {
        if (!selectedStation) return;
        setLoading(true);
        try {
            const data = await qmsApi.getQueueBoard(selectedStation);
            setCurrentServing(data.currently_serving?.[0] || null);
            setWaitingList(data.waiting_list);
            setTotalWaiting(data.total_waiting);
            setEstimatedWait(data.estimated_wait_minutes);
        } catch {
            // Fallback: sử dụng legacy endpoint
            try {
                const waitingData = await qmsApi.getWaiting(selectedStation);
                const mapped: QueueBoardEntry[] = waitingData.map((q, idx) => ({
                    position: idx + 1,
                    entry_id: q.id || '',
                    queue_number: q.number_code,
                    daily_sequence: q.daily_sequence || idx + 1,
                    patient_name: '',
                    source_type: 'WALK_IN' as QueueSourceType,
                    priority: q.priority || 0,
                    wait_time_minutes: null,
                }));
                setWaitingList(mapped);
                setTotalWaiting(waitingData.length);
                setCurrentServing(null);
            } catch (fallbackErr) {
                console.error('Error fetching queue:', fallbackErr);
            }
        } finally {
            setLoading(false);
        }
    }, [selectedStation]);

    useEffect(() => { fetchStations(); }, [fetchStations]);
    useEffect(() => {
        if (selectedStation) {
            fetchQueueBoard();
            // Auto-refresh mỗi 10 giây
            const interval = setInterval(fetchQueueBoard, 10000);
            return () => clearInterval(interval);
        }
    }, [selectedStation, fetchQueueBoard]);

    // --- Doctor Call Next ---
    const handleCallNext = async () => {
        if (!selectedStation) return;
        setCallLoading(true);
        try {
            const result = await qmsApi.doctorCallNext(selectedStation);
            if (result.success && result.called_patient) {
                const p = result.called_patient;
                const src = sourceConfig[p.source_type];

                // Speech synthesis
                if ('speechSynthesis' in window) {
                    const utterance = new SpeechSynthesisUtterance(
                        `Mời số ${p.daily_sequence}, ${p.patient_name || ''}, đến ${p.station_name}`
                    );
                    utterance.lang = 'vi-VN';
                    utterance.rate = 0.9;
                    speechSynthesis.speak(utterance);
                }

                message.success({
                    content: (
                        <span>
                            Đã gọi <Tag color={src.tagColor}>{src.label}</Tag>
                            <strong>{p.queue_number}</strong> — {p.patient_name || 'BN'}
                        </span>
                    ),
                    duration: 4,
                });
                fetchQueueBoard();
            } else {
                message.info(result.message || 'Không còn bệnh nhân trong hàng đợi');
            }
        } catch (error) {
            console.error('Error calling next:', error);
            message.error('Không thể gọi bệnh nhân tiếp theo');
        } finally {
            setCallLoading(false);
        }
    };

    // --- Walk-in Check-in ---
    const handleWalkinCheckin = async () => {
        if (!selectedStation || !walkinPatientId) return;
        setWalkinLoading(true);
        try {
            const result = await qmsApi.walkinCheckin({
                patient_id: walkinPatientId,
                station_id: selectedStation,
                reason: walkinReason || undefined,
            });
            message.success(`Số ${result.queue_number} — Vãng lai đã vào hàng đợi`);
            setWalkinModal(false);
            setWalkinPatientId('');
            setWalkinReason('');
            fetchQueueBoard();
        } catch (error: unknown) {
            const err = error as { response?: { data?: { error?: string } } };
            message.error(err?.response?.data?.error || 'Không thể tạo số hàng đợi');
        } finally {
            setWalkinLoading(false);
        }
    };

    // --- Emergency Flag ---
    const handleEmergencyFlag = async () => {
        if (!selectedStation || !emergencyPatientId) return;
        setEmergencyLoading(true);
        try {
            const result = await qmsApi.emergencyFlag({
                patient_id: emergencyPatientId,
                station_id: selectedStation,
                reason: emergencyReason || undefined,
            });
            message.warning({
                content: `🚨 CẤP CỨU — Số ${result.queue_number} (Priority ${result.priority})`,
                duration: 5,
            });
            setEmergencyModal(false);
            setEmergencyPatientId('');
            setEmergencyReason('');
            fetchQueueBoard();
        } catch (error: unknown) {
            const err = error as { response?: { data?: { error?: string } } };
            message.error(err?.response?.data?.error || 'Không thể flag cấp cứu');
        } finally {
            setEmergencyLoading(false);
        }
    };

    // --- Kiosk Check-in (Booking) ---
    const handleKioskCheckin = async () => {
        if (!selectedStation || !kioskAppointmentId) return;
        setKioskLoading(true);
        try {
            const result = await qmsApi.kioskCheckin(kioskAppointmentId, selectedStation);
            const lateCat = result.lateness_info?.category;
            const lateMsg = lateCat === 'ON_TIME' ? '✅ Đúng giờ'
                : lateCat === 'LATE' ? `⚠️ Trễ ${result.lateness_info.minutes} phút`
                    : `❌ Quá trễ (${result.lateness_info.minutes} phút)`;

            message.success({
                content: `Booking check-in: Số ${result.queue_number} — ${lateMsg} — Priority ${result.priority}`,
                duration: 5,
            });
            setKioskModal(false);
            setKioskAppointmentId('');
            fetchQueueBoard();
        } catch (error: unknown) {
            const err = error as { response?: { data?: { error?: string } } };
            message.error(err?.response?.data?.error || 'Không thể check-in booking');
        } finally {
            setKioskLoading(false);
        }
    };

    const currentStation = stations.find((s) => s.id === selectedStation);

    // --- Đếm theo source_type ---
    const emergencyCount = waitingList.filter(w => w.source_type === 'EMERGENCY').length;
    const bookingCount = waitingList.filter(w => w.source_type === 'ONLINE_BOOKING').length;
    const walkinCount = waitingList.filter(w => w.source_type === 'WALK_IN').length;

    return (
        <div className="space-y-4">
            {/* ===== Page Header ===== */}
            <div className="flex justify-between items-center flex-wrap gap-3">
                <div>
                    <Title level={3} className="!mb-0">
                        <MedicineBoxOutlined className="mr-2 text-blue-500" />
                        Hàng chờ Lâm sàng — 3 Luồng
                    </Title>
                    <Text type="secondary">
                        Emergency → Booking ưu tiên → Walk-in FCFS
                    </Text>
                </div>
                <Space wrap>
                    <Select
                        placeholder="Chọn điểm dịch vụ"
                        value={selectedStation}
                        onChange={setSelectedStation}
                        style={{ width: 260 }}
                        options={stations.map((s) => ({
                            value: s.id,
                            label: `[${s.code}] ${s.name}`,
                        }))}
                    />
                    <Button icon={<ReloadOutlined />} onClick={fetchQueueBoard}>
                        Làm mới
                    </Button>
                </Space>
            </div>

            {/* ===== Stats Row ===== */}
            <Row gutter={16}>
                <Col xs={12} sm={6}>
                    <Card size="small">
                        <Statistic
                            title="Tổng chờ"
                            value={totalWaiting}
                            prefix={<ClockCircleOutlined />}
                            styles={{ content: { color: '#faad14' } }}
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card size="small">
                        <Statistic
                            title={<><ThunderboltOutlined className="text-red-500" /> Cấp cứu</>}
                            value={emergencyCount}
                            styles={{ content: { color: emergencyCount > 0 ? '#ff4d4f' : '#8c8c8c' } }}
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card size="small">
                        <Statistic
                            title={<><CalendarOutlined className="text-blue-500" /> Đặt lịch</>}
                            value={bookingCount}
                            styles={{ content: { color: '#1890ff' } }}
                        />
                    </Card>
                </Col>
                <Col xs={12} sm={6}>
                    <Card size="small">
                        <Statistic
                            title={<><TeamOutlined /> Vãng lai</>}
                            value={walkinCount}
                        />
                    </Card>
                </Col>
            </Row>

            {/* ===== Action Buttons Row ===== */}
            <Card size="small">
                <Space wrap>
                    <Button
                        type="primary"
                        size="large"
                        icon={<SoundOutlined />}
                        onClick={handleCallNext}
                        loading={callLoading}
                        disabled={!selectedStation}
                    >
                        GỌI TIẾP
                    </Button>
                    <Divider orientation="vertical" />
                    <Tooltip title="Tiếp nhận vãng lai">
                        <Button
                            icon={<TeamOutlined />}
                            onClick={() => setWalkinModal(true)}
                            disabled={!selectedStation}
                        >
                            Walk-in
                        </Button>
                    </Tooltip>
                    <Tooltip title="Quét QR booking">
                        <Button
                            icon={<QrcodeOutlined />}
                            onClick={() => setKioskModal(true)}
                            disabled={!selectedStation}
                        >
                            Kiosk Check-in
                        </Button>
                    </Tooltip>
                    <Tooltip title="Flag cấp cứu (Priority 100)">
                        <Button
                            danger
                            icon={<AlertOutlined />}
                            onClick={() => setEmergencyModal(true)}
                            disabled={!selectedStation}
                        >
                            🚨 Cấp cứu
                        </Button>
                    </Tooltip>
                    {estimatedWait > 0 && (
                        <>
                            <Divider orientation="vertical" />
                            <Text type="secondary">
                                ⏱ Chờ ~{estimatedWait} phút
                            </Text>
                        </>
                    )}
                </Space>
            </Card>

            {/* ===== Main Grid: Current Serving + Waiting Queue ===== */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                {/* Current Serving */}
                <Card
                    title={
                        <Space>
                            <SoundOutlined className="text-blue-500" />
                            <span>Đang phục vụ</span>
                        </Space>
                    }
                    className="lg:col-span-1"
                >
                    {currentServing ? (
                        <div className="text-center py-4">
                            {/* Source badge */}
                            <Tag
                                color={sourceConfig[currentServing.source_type]?.tagColor}
                                icon={sourceConfig[currentServing.source_type]?.icon}
                                className="mb-3"
                            >
                                {sourceConfig[currentServing.source_type]?.label}
                            </Tag>

                            {/* Số thứ tự lớn */}
                            <div
                                className="text-6xl font-bold mb-2"
                                style={{ color: sourceConfig[currentServing.source_type]?.color || '#1890ff' }}
                            >
                                {currentServing.daily_sequence}
                            </div>
                            <Tag color="blue" className="text-lg px-4 py-1 mb-2">
                                {currentServing.queue_number}
                            </Tag>
                            <div className="text-base text-gray-600 mb-1">
                                {currentServing.patient_name || 'Bệnh nhân'}
                            </div>
                            <Text type="secondary" className="text-xs">
                                {currentServing.display_label}
                            </Text>

                            {/* Priority Tag */}
                            {currentServing.priority > 0 && (() => {
                                const pl = priorityLabel(currentServing.priority);
                                return (
                                    <div className="mt-2">
                                        <Tag color={pl.color}>P{currentServing.priority} — {pl.text}</Tag>
                                    </div>
                                );
                            })()}

                            {/* Wait time */}
                            {currentServing.wait_time_minutes != null && (
                                <div className="mt-1">
                                    <Text type="secondary" className="text-xs">
                                        Chờ {currentServing.wait_time_minutes} phút
                                    </Text>
                                </div>
                            )}

                            <div className="flex justify-center gap-2 mt-4">
                                <Button
                                    type="primary"
                                    icon={<CheckOutlined />}
                                    onClick={async () => {
                                        try {
                                            await qmsApi.completeQueue(currentServing.entry_id);
                                            message.success('Hoàn thành phục vụ');
                                            fetchQueueBoard();
                                        } catch {
                                            message.error('Không thể cập nhật');
                                        }
                                    }}
                                >
                                    Hoàn thành
                                </Button>
                                <Button
                                    danger
                                    icon={<ForwardOutlined />}
                                    onClick={async () => {
                                        try {
                                            await qmsApi.skipQueue(currentServing.entry_id);
                                            message.warning('Bỏ qua');
                                            fetchQueueBoard();
                                        } catch {
                                            message.error('Không thể bỏ qua');
                                        }
                                    }}
                                >
                                    Bỏ qua
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8">
                            <Empty
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                                description="Chưa có bệnh nhân"
                            />
                            <Button
                                type="primary"
                                size="large"
                                icon={<SoundOutlined />}
                                onClick={handleCallNext}
                                loading={callLoading}
                                className="mt-4"
                            >
                                Gọi số tiếp theo
                            </Button>
                        </div>
                    )}
                </Card>

                {/* Waiting Queue */}
                <Card
                    title={
                        <Space>
                            <ClockCircleOutlined className="text-orange-500" />
                            <span>Hàng đợi ({totalWaiting})</span>
                        </Space>
                    }
                    className="lg:col-span-2"
                    extra={
                        <Button
                            type="primary"
                            icon={<SoundOutlined />}
                            onClick={handleCallNext}
                            loading={callLoading}
                            disabled={waitingList.length === 0}
                        >
                            Gọi tiếp
                        </Button>
                    }
                >
                    <Tabs
                        defaultActiveKey="all"
                        size="small"
                        items={[
                            {
                                key: 'all',
                                label: `Tất cả (${waitingList.length})`,
                                children: <QueueList items={waitingList} loading={loading} />,
                            },
                            {
                                key: 'emergency',
                                label: (
                                    <Badge count={emergencyCount} size="small" offset={[8, 0]}>
                                        <span className="text-red-500">🚨 Cấp cứu</span>
                                    </Badge>
                                ),
                                children: <QueueList items={waitingList.filter(w => w.source_type === 'EMERGENCY')} loading={loading} />,
                            },
                            {
                                key: 'booking',
                                label: (
                                    <Badge count={bookingCount} size="small" offset={[8, 0]}>
                                        <span className="text-blue-500">📱 Đặt lịch</span>
                                    </Badge>
                                ),
                                children: <QueueList items={waitingList.filter(w => w.source_type === 'ONLINE_BOOKING')} loading={loading} />,
                            },
                            {
                                key: 'walkin',
                                label: `🚶 Vãng lai (${walkinCount})`,
                                children: <QueueList items={waitingList.filter(w => w.source_type === 'WALK_IN')} loading={loading} />,
                            },
                        ]}
                    />
                </Card>
            </div>

            {/* Station Info */}
            {currentStation && (
                <Card size="small">
                    <Space split={<span className="text-gray-300">|</span>}>
                        <Text type="secondary">
                            Điểm dịch vụ: <Text strong>{currentStation.name}</Text>
                        </Text>
                        <Text type="secondary">
                            Loại: <Text strong>{currentStation.station_type}</Text>
                        </Text>
                        <Text type="secondary">
                            Trạng thái: {currentStation.is_active ? (
                                <Tag color="green">Hoạt động</Tag>
                            ) : (
                                <Tag color="red">Tạm ngưng</Tag>
                            )}
                        </Text>
                    </Space>
                </Card>
            )}

            {/* ===== Walk-in Modal ===== */}
            <Modal
                title={<><TeamOutlined /> Tiếp nhận vãng lai</>}
                open={walkinModal}
                onCancel={() => setWalkinModal(false)}
                onOk={handleWalkinCheckin}
                confirmLoading={walkinLoading}
                okText="Lấy số"
            >
                <div className="space-y-3 py-2">
                    <div>
                        <Text type="secondary">Patient ID *</Text>
                        <Input
                            placeholder="Nhập mã bệnh nhân (UUID)"
                            value={walkinPatientId}
                            onChange={(e) => setWalkinPatientId(e.target.value)}
                        />
                    </div>
                    <div>
                        <Text type="secondary">Lý do khám</Text>
                        <Input.TextArea
                            placeholder="VD: Đau đầu, sốt cao..."
                            value={walkinReason}
                            onChange={(e) => setWalkinReason(e.target.value)}
                            rows={2}
                        />
                    </div>
                </div>
            </Modal>

            {/* ===== Kiosk Check-in Modal ===== */}
            <Modal
                title={<><QrcodeOutlined /> Kiosk Check-in (Booking)</>}
                open={kioskModal}
                onCancel={() => setKioskModal(false)}
                onOk={handleKioskCheckin}
                confirmLoading={kioskLoading}
                okText="Check-in"
            >
                <div className="space-y-3 py-2">
                    <div>
                        <Text type="secondary">Appointment ID *</Text>
                        <Input
                            placeholder="Quét QR hoặc nhập mã lịch hẹn"
                            value={kioskAppointmentId}
                            onChange={(e) => setKioskAppointmentId(e.target.value)}
                        />
                    </div>
                    <div className="bg-blue-50 p-3 rounded-lg text-sm">
                        <Text type="secondary">
                            ⏰ <strong>Quy tắc ưu tiên:</strong><br />
                            • Đúng giờ / trễ ≤15p → Priority 7<br />
                            • Trễ 15-30p → Priority 3<br />
                            • Trễ &gt;30p → Mất ưu tiên (Priority 0)
                        </Text>
                    </div>
                </div>
            </Modal>

            {/* ===== Emergency Modal ===== */}
            <Modal
                title={<span className="text-red-500"><AlertOutlined /> 🚨 Flag Cấp cứu</span>}
                open={emergencyModal}
                onCancel={() => setEmergencyModal(false)}
                onOk={handleEmergencyFlag}
                confirmLoading={emergencyLoading}
                okText="FLAG CẤP CỨU"
                okButtonProps={{ danger: true }}
            >
                <div className="space-y-3 py-2">
                    <div>
                        <Text type="secondary">Patient ID *</Text>
                        <Input
                            placeholder="Mã bệnh nhân cấp cứu"
                            value={emergencyPatientId}
                            onChange={(e) => setEmergencyPatientId(e.target.value)}
                        />
                    </div>
                    <div>
                        <Text type="secondary">Lý do cấp cứu</Text>
                        <Input.TextArea
                            placeholder="VD: Ngưng tim, chấn thương nặng..."
                            value={emergencyReason}
                            onChange={(e) => setEmergencyReason(e.target.value)}
                            rows={2}
                        />
                    </div>
                    <div className="bg-red-50 p-3 rounded-lg text-sm text-red-700">
                        <AlertOutlined /> Priority = 100 — Bệnh nhân sẽ được gọi ngay lập tức,
                        bỏ qua toàn bộ hàng đợi hiện tại.
                    </div>
                </div>
            </Modal>
        </div>
    );
}

// ============================================================================
// Sub-component: Queue List
// ============================================================================

function QueueList({ items, loading }: { items: QueueBoardEntry[]; loading: boolean }) {
    return (
        <Spin spinning={loading}>
            {items.length > 0 ? (
                <List
                    dataSource={items}
                    renderItem={(item) => {
                        const src = sourceConfig[item.source_type] || sourceConfig.WALK_IN;
                        const pl = priorityLabel(item.priority);

                        return (
                            <List.Item>
                                <List.Item.Meta
                                    avatar={
                                        <Badge
                                            count={item.position}
                                            style={{
                                                backgroundColor: item.position === 1 ? '#1E88E5' : '#8c8c8c',
                                            }}
                                        >
                                            <Avatar
                                                icon={src.icon || <UserOutlined />}
                                                style={{
                                                    backgroundColor: item.source_type === 'EMERGENCY' ? '#fff1f0' : undefined,
                                                }}
                                            />
                                        </Badge>
                                    }
                                    title={
                                        <Space>
                                            <Text strong>{item.queue_number}</Text>
                                            <Tag color={src.tagColor} icon={src.icon}>
                                                {src.label}
                                            </Tag>
                                            {item.priority > 0 && (
                                                <Tag color={pl.color}>P{item.priority}</Tag>
                                            )}
                                        </Space>
                                    }
                                    description={
                                        <Space>
                                            {item.patient_name && (
                                                <Text type="secondary">{item.patient_name}</Text>
                                            )}
                                            {item.wait_time_minutes != null && (
                                                <Text type="secondary" className="text-xs">
                                                    • Chờ {item.wait_time_minutes}p
                                                </Text>
                                            )}
                                        </Space>
                                    }
                                />
                                <Tag color={statusConfig.WAITING.color}>
                                    {statusConfig.WAITING.label}
                                </Tag>
                            </List.Item>
                        );
                    }}
                />
            ) : (
                <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="Trống"
                />
            )}
        </Spin>
    );
}
