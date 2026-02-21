'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
    Card,
    Table,
    Button,
    Input,
    Space,
    Tag,
    Select,
    Typography,
    Tooltip,
    Badge,
    App,
    Descriptions,
    Empty,
} from 'antd';
import {
    PlusOutlined,
    SearchOutlined,
    UserAddOutlined,
    CheckCircleOutlined,
    ReloadOutlined,
    RobotOutlined,
    MedicineBoxOutlined,
    CheckOutlined,
    SoundOutlined,
    CloseCircleOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { visitApi, departmentApi, patientApi } from '@/lib/services';
import type { Visit, Department } from '@/types';
import TriageModal from './TriageModal';
import CreateVisitModal from './CreateVisitModal';
import { useReceptionSocket, WsVisitPayload } from '@/hooks/useReceptionSocket';
import { toast } from 'sonner';
import dayjs from 'dayjs';
import './reception-highlight.css';

const { Title, Text } = Typography;

// ── Helpers ──────────────────────────────────────────────────

function isCCCD(raw: string): boolean {
    return /^\d{12}$/.test(raw.trim());
}

function isBHYT(raw: string): boolean {
    const trimmed = raw.trim();
    return /^[A-Z]{2}\d{8,13}$/.test(trimmed) || /^\d{10,15}$/.test(trimmed);
}

// ── Sound ────────────────────────────────────────────────────

const SOUND_KEY = 'his_reception_sound';

function getSoundEnabled(): boolean {
    if (typeof window === 'undefined') return true;
    const stored = localStorage.getItem(SOUND_KEY);
    return stored !== 'off';
}

function playTing() {
    try {
        const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        oscillator.frequency.value = 2400;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.25;

        oscillator.start();
        oscillator.stop(audioCtx.currentTime + 0.1);

        oscillator.onended = () => {
            gainNode.disconnect();
            audioCtx.close();
        };
    } catch {
        // Silently fail
    }
}

// ── Configs ──────────────────────────────────────────────────

const statusConfig: Record<string, { color: string; label: string }> = {
    CHECK_IN: { color: 'cyan', label: 'Check-in' },
    TRIAGE: { color: 'orange', label: 'Phân luồng' },
    WAITING: { color: 'gold', label: 'Chờ khám' },
    IN_PROGRESS: { color: 'blue', label: 'Đang khám' },
    PENDING_RESULTS: { color: 'purple', label: 'Chờ CLS' },
    COMPLETED: { color: 'green', label: 'Hoàn thành' },
    CANCELLED: { color: 'red', label: 'Đã hủy' },
};

const priorityConfig: Record<string, { color: string; label: string }> = {
    NORMAL: { color: 'default', label: 'Bình thường' },
    PRIORITY: { color: 'orange', label: 'Ưu tiên' },
    EMERGENCY: { color: 'red', label: 'Cấp cứu' },
};

const PRIORITY_ORDER: Record<string, number> = {
    EMERGENCY: 0,
    PRIORITY: 1,
    ONLINE_BOOKING: 2,
    NORMAL: 3,
};

// ── Component ────────────────────────────────────────────────

export default function ReceptionPage() {
    const { message } = App.useApp();
    const [visits, setVisits] = useState<Visit[]>([]);
    const [loading, setLoading] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);

    // Current patient (receptionist is working on)
    const [currentVisit, setCurrentVisit] = useState<Visit | null>(null);

    // Triage
    const [triageModalOpen, setTriageModalOpen] = useState(false);
    const [triageVisit, setTriageVisit] = useState<Visit | null>(null);
    const [departments, setDepartments] = useState<Department[]>([]);
    const [scannedPatientId, setScannedPatientId] = useState<string | null>(null);

    // Highlights & sound
    const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set());
    const [soundEnabled, setSoundEnabled] = useState(true);
    const [badgePulse, setBadgePulse] = useState(false);
    const highlightTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

    // Load sound preference
    useEffect(() => {
        setSoundEnabled(getSoundEnabled());
    }, []);

    // ── Data fetching ────────────────────────────────────────

    const fetchVisits = useCallback(async () => {
        setLoading(true);
        try {
            const response = await visitApi.getAll();
            const list = Array.isArray(response) ? response : (response.results || []);
            setVisits(list);
        } catch (error) {
            console.error('Error fetching visits:', error);
            message.error('Không thể tải danh sách lượt khám');
        } finally {
            setLoading(false);
        }
    }, [message]);

    const fetchDepartments = useCallback(async () => {
        try {
            const depts = await departmentApi.getAll();
            setDepartments(depts);
        } catch (error) {
            console.error('Error fetching departments:', error);
        }
    }, []);

    useEffect(() => {
        fetchVisits();
        fetchDepartments();
    }, [fetchVisits, fetchDepartments]);

    // ── WebSocket: Real-time new visits ──────────────────────

    const handleNewVisitWs = useCallback((wsVisit: WsVisitPayload) => {
        const patientName = wsVisit.patient?.full_name || 'Bệnh nhân';

        // Toast notification
        toast.success(`${patientName} vừa đăng ký thành công`, {
            description: `Mã: ${wsVisit.visit_code} — STT: ${wsVisit.queue_number}`,
        });

        // Sound
        if (soundEnabled) {
            playTing();
        }

        // Re-fetch visits (to get full serialized data with patient_detail etc.)
        fetchVisits();

        // Highlight the new row
        setHighlightedIds((prev) => {
            const next = new Set(prev);
            next.add(wsVisit.id);
            return next;
        });

        // Clear highlight after 3s
        const timer = setTimeout(() => {
            setHighlightedIds((prev) => {
                const next = new Set(prev);
                next.delete(wsVisit.id);
                return next;
            });
            highlightTimersRef.current.delete(wsVisit.id);
        }, 3000);
        highlightTimersRef.current.set(wsVisit.id, timer);

        // Badge pulse
        setBadgePulse(true);
        setTimeout(() => setBadgePulse(false), 2000);
    }, [soundEnabled, fetchVisits]);

    const handleVisitUpdatedWs = useCallback(() => {
        fetchVisits();
    }, [fetchVisits]);

    useReceptionSocket({
        onNewVisit: handleNewVisitWs,
        onVisitUpdated: handleVisitUpdatedWs,
    });

    // Cleanup highlight timers on unmount
    useEffect(() => {
        return () => {
            highlightTimersRef.current.forEach((t) => clearTimeout(t));
        };
    }, []);

    // ── Scanner ──────────────────────────────────────────────

    useEffect(() => {
        const handleScan = async (e: Event) => {
            const rawData = (e as CustomEvent).detail as string;
            if (!rawData) return;

            try {
                if (isCCCD(rawData)) {
                    message.loading({ content: `Đang tra cứu CCCD: ${rawData}...`, key: 'scan' });
                    const patients = await patientApi.search(rawData);
                    if (patients.length > 0) {
                        message.success({ content: `Tìm thấy: ${patients[0].full_name || patients[0].last_name + ' ' + patients[0].first_name}`, key: 'scan' });
                        setScannedPatientId(patients[0].id);
                        setIsModalOpen(true);
                    } else {
                        message.warning({ content: `Không tìm thấy bệnh nhân với CCCD: ${rawData}`, key: 'scan' });
                    }
                } else if (isBHYT(rawData)) {
                    message.loading({ content: `Đang tra cứu BHYT: ${rawData}...`, key: 'scan' });
                    const patients = await patientApi.search(rawData);
                    if (patients.length > 0) {
                        message.success({ content: `Tìm thấy: ${patients[0].full_name || patients[0].last_name + ' ' + patients[0].first_name}`, key: 'scan' });
                        setScannedPatientId(patients[0].id);
                        setIsModalOpen(true);
                    } else {
                        message.warning({ content: `Không tìm thấy bệnh nhân với BHYT: ${rawData}`, key: 'scan' });
                    }
                } else {
                    message.info({ content: `Mã quét: ${rawData.substring(0, 30)}${rawData.length > 30 ? '...' : ''}`, key: 'scan', duration: 3 });
                }
            } catch (error) {
                console.error('Error processing scan:', error);
                message.error({ content: 'Lỗi tra cứu dữ liệu quét', key: 'scan' });
            }
        };

        window.addEventListener('HIS_SCANNED_DATA', handleScan);
        return () => window.removeEventListener('HIS_SCANNED_DATA', handleScan);
    }, [message]);

    // ── Triage ───────────────────────────────────────────────

    const openTriageModal = useCallback(async (visit: Visit) => {
        try {
            if (visit.status === 'TRIAGE') {
                const freshVisit = await visitApi.getById(visit.id);
                setTriageVisit(freshVisit);
            } else {
                setTriageVisit(visit);
            }
        } catch (error) {
            console.error('Error fetching visit:', error);
            setTriageVisit(visit);
        }
        setTriageModalOpen(true);
    }, []);

    const handleTriageSuccess = useCallback(() => {
        fetchVisits();
    }, [fetchVisits]);

    // ── Sound toggle ─────────────────────────────────────────

    const toggleSound = useCallback(() => {
        setSoundEnabled((prev) => {
            const next = !prev;
            localStorage.setItem(SOUND_KEY, next ? 'on' : 'off');
            if (next) playTing(); // preview
            return next;
        });
    }, []);

    // ── Select current patient ───────────────────────────────

    const selectCurrentVisit = useCallback((visit: Visit) => {
        setCurrentVisit(visit);
    }, []);

    const clearCurrentVisit = useCallback(() => {
        setCurrentVisit(null);
    }, []);

    // ── Computed Data ────────────────────────────────────────

    const queueVisits = useMemo(() => {
        return visits
            .filter((v) => ['CHECK_IN', 'TRIAGE', 'WAITING'].includes(v.status))
            .filter((v) => v.id !== currentVisit?.id)
            .sort((a, b) => {
                const pa = PRIORITY_ORDER[a.priority] ?? 99;
                const pb = PRIORITY_ORDER[b.priority] ?? 99;
                if (pa !== pb) return pa - pb;
                // FIFO within same priority
                const ta = a.check_in_time ? new Date(a.check_in_time).getTime() : 0;
                const tb = b.check_in_time ? new Date(b.check_in_time).getTime() : 0;
                return ta - tb;
            });
    }, [visits, currentVisit]);

    const stats = useMemo(() => ({
        total: visits.length,
        waiting: visits.filter((v) => ['CHECK_IN', 'TRIAGE', 'WAITING'].includes(v.status)).length,
        inProgress: visits.filter((v) => v.status === 'IN_PROGRESS').length,
        completed: visits.filter((v) => v.status === 'COMPLETED').length,
    }), [visits]);

    // ── Table columns ────────────────────────────────────────

    const columns: ColumnsType<Visit> = useMemo(() => [
        {
            title: 'STT',
            dataIndex: 'queue_number',
            key: 'queue_number',
            width: 70,
            render: (num: number) => (
                <Badge
                    count={num}
                    style={{ backgroundColor: '#1E88E5', fontSize: 14, minWidth: 32 }}
                    overflowCount={999}
                />
            ),
        },
        {
            title: 'Mã khám',
            dataIndex: 'visit_code',
            key: 'visit_code',
            width: 140,
            render: (code: string) => <Text strong className="text-blue-600">{code}</Text>,
        },
        {
            title: 'Bệnh nhân',
            dataIndex: 'patient',
            key: 'patient',
            render: (_: unknown, record: Visit) => {
                const patient = record.patient_detail || record.patient;
                if (typeof patient === 'object' && patient) {
                    return (
                        <Space style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 0 }}>
                            <Text strong>{patient.full_name || `${patient.last_name} ${patient.first_name}`}</Text>
                            <Text type="secondary" className="text-xs">{patient.patient_code}</Text>
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
            title: 'Ưu tiên',
            dataIndex: 'priority',
            key: 'priority',
            width: 110,
            render: (priority: string) => {
                const config = priorityConfig[priority] || { color: 'default', label: priority };
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
        {
            title: 'Trạng thái',
            dataIndex: 'status',
            key: 'status',
            width: 120,
            render: (status: string) => {
                const config = statusConfig[status] || { color: 'default', label: status };
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
        {
            title: 'Khoa hướng đến',
            key: 'department',
            width: 140,
            render: (_: unknown, record: Visit) => {
                if (record.confirmed_department_detail) {
                    return <Tag color="blue" icon={<CheckOutlined />}>{record.confirmed_department_detail.name}</Tag>;
                }
                if (record.recommended_department_detail) {
                    return <Tag color="orange">{record.recommended_department_detail.name} (AI)</Tag>;
                }
                return <Text type="secondary">-</Text>;
            },
        },
        {
            title: 'Thao tác',
            key: 'actions',
            width: 200,
            render: (_: unknown, record: Visit) => (
                <Space>
                    <Tooltip title="Chọn xử lý">
                        <Button
                            size="small"
                            onClick={() => selectCurrentVisit(record)}
                        >
                            Chọn
                        </Button>
                    </Tooltip>
                    {record.status === 'CHECK_IN' && (
                        <Tooltip title="Phân luồng bằng AI">
                            <Button
                                type="primary"
                                size="small"
                                icon={<RobotOutlined />}
                                onClick={() => openTriageModal(record)}
                            >
                                Phân luồng
                            </Button>
                        </Tooltip>
                    )}
                    {record.status === 'TRIAGE' && !record.confirmed_department && (
                        <Tooltip title="Tiếp tục phân luồng">
                            <Button
                                size="small"
                                icon={<MedicineBoxOutlined />}
                                onClick={() => openTriageModal(record)}
                            >
                                Chốt khoa
                            </Button>
                        </Tooltip>
                    )}
                    {record.status === 'COMPLETED' && (
                        <Tag icon={<CheckCircleOutlined />} color="success">
                            Xong
                        </Tag>
                    )}
                </Space>
            ),
        },
    ], [openTriageModal, selectCurrentVisit]);

    // ── Helper: get patient display info ─────────────────────

    const getPatientInfo = (visit: Visit) => {
        const patient = visit.patient_detail || visit.patient;
        if (typeof patient === 'object' && patient) {
            return {
                name: patient.full_name || `${patient.last_name} ${patient.first_name}`,
                code: patient.patient_code,
                dob: patient.date_of_birth,
                gender: patient.gender,
                phone: patient.contact_number,
            };
        }
        return { name: String(patient || '-'), code: '-' };
    };

    // ── Render ───────────────────────────────────────────────

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex justify-between items-center">
                <div>
                    <Title level={3} className="!mb-0">Tiếp nhận Khám bệnh</Title>
                    <Text type="secondary">Quản lý lượt khám và tiếp nhận bệnh nhân</Text>
                </div>
                <Space>
                    <Tooltip title={soundEnabled ? 'Tắt âm thanh thông báo' : 'Bật âm thanh thông báo'}>
                        <Button
                            type={soundEnabled ? 'primary' : 'default'}
                            ghost={soundEnabled}
                            icon={<SoundOutlined />}
                            onClick={toggleSound}
                        />
                    </Tooltip>
                    <Button type="primary" icon={<UserAddOutlined />} onClick={() => setIsModalOpen(true)}>
                        Tiếp nhận mới
                    </Button>
                </Space>
            </div>

            {/* Stats Cards */}
            <div className="grid grid-cols-4 gap-4">
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Tổng hôm nay</Text>
                        <div className="text-2xl font-bold text-blue-600">{stats.total}</div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Đang chờ</Text>
                        <div className="text-2xl font-bold text-orange-500">{stats.waiting}</div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Đang khám</Text>
                        <div className="text-2xl font-bold text-blue-500">{stats.inProgress}</div>
                    </div>
                </Card>
                <Card size="small">
                    <div className="text-center">
                        <Text type="secondary">Hoàn thành</Text>
                        <div className="text-2xl font-bold text-green-500">{stats.completed}</div>
                    </div>
                </Card>
            </div>

            {/* ══════════════ CURRENT PATIENT ══════════════ */}
            <Card
                title={
                    <Space>
                        <MedicineBoxOutlined className="text-blue-500" />
                        <span>Đang xử lý</span>
                    </Space>
                }
                extra={currentVisit && (
                    <Button
                        size="small"
                        danger
                        icon={<CloseCircleOutlined />}
                        onClick={clearCurrentVisit}
                    >
                        Bỏ chọn
                    </Button>
                )}
                className="border-blue-200"
                styles={{ header: { borderBottom: '2px solid #1677ff' } }}
            >
                {currentVisit ? (
                    <div className="flex gap-6">
                        <div className="flex-1">
                            <Descriptions column={3} size="small" bordered>
                                <Descriptions.Item label="STT">
                                    <Badge
                                        count={currentVisit.queue_number}
                                        style={{ backgroundColor: '#1E88E5', fontSize: 16, minWidth: 36 }}
                                        overflowCount={999}
                                    />
                                </Descriptions.Item>
                                <Descriptions.Item label="Mã khám">
                                    <Text strong className="text-blue-600">{currentVisit.visit_code}</Text>
                                </Descriptions.Item>
                                <Descriptions.Item label="Trạng thái">
                                    <Tag color={statusConfig[currentVisit.status]?.color || 'default'}>
                                        {statusConfig[currentVisit.status]?.label || currentVisit.status}
                                    </Tag>
                                </Descriptions.Item>
                                <Descriptions.Item label="Bệnh nhân" span={2}>
                                    <Text strong>{getPatientInfo(currentVisit).name}</Text>
                                    <Text type="secondary" className="ml-2">{getPatientInfo(currentVisit).code}</Text>
                                </Descriptions.Item>
                                <Descriptions.Item label="Ưu tiên">
                                    <Tag color={priorityConfig[currentVisit.priority]?.color || 'default'}>
                                        {priorityConfig[currentVisit.priority]?.label || currentVisit.priority}
                                    </Tag>
                                </Descriptions.Item>
                                {currentVisit.chief_complaint && (
                                    <Descriptions.Item label="Lý do khám" span={3}>
                                        {currentVisit.chief_complaint}
                                    </Descriptions.Item>
                                )}
                            </Descriptions>
                        </div>
                        <div className="flex flex-col gap-2 min-w-[140px]">
                            {currentVisit.status === 'CHECK_IN' && (
                                <Button
                                    type="primary"
                                    icon={<RobotOutlined />}
                                    onClick={() => openTriageModal(currentVisit)}
                                    block
                                >
                                    Phân luồng AI
                                </Button>
                            )}
                            {currentVisit.status === 'TRIAGE' && !currentVisit.confirmed_department && (
                                <Button
                                    icon={<MedicineBoxOutlined />}
                                    onClick={() => openTriageModal(currentVisit)}
                                    block
                                >
                                    Chốt khoa
                                </Button>
                            )}
                            {currentVisit.confirmed_department_detail && (
                                <Tag color="blue" icon={<CheckOutlined />} className="text-center">
                                    {currentVisit.confirmed_department_detail.name}
                                </Tag>
                            )}
                        </div>
                    </div>
                ) : (
                    <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description="Chọn bệnh nhân từ hàng đợi bên dưới để bắt đầu xử lý"
                    />
                )}
            </Card>

            {/* ══════════════ QUEUE ══════════════ */}
            <Card
                title={
                    <Space>
                        <span>Hàng đợi chờ tiếp đón</span>
                        <div className={badgePulse ? 'badge-pulse' : ''}>
                            <Badge
                                count={queueVisits.length}
                                style={{ backgroundColor: '#fa8c16' }}
                                overflowCount={999}
                            />
                        </div>
                    </Space>
                }
            >
                <div className="flex justify-between items-center mb-4">
                    <Space>
                        <Input.Search
                            placeholder="Tìm mã khám, bệnh nhân..."
                            allowClear
                            style={{ width: 280 }}
                            prefix={<SearchOutlined className="text-gray-400" />}
                        />
                        <Select
                            placeholder="Trạng thái"
                            allowClear
                            style={{ width: 140 }}
                            options={Object.entries(statusConfig).map(([k, v]) => ({
                                value: k,
                                label: v.label,
                            }))}
                        />
                    </Space>
                    <Button icon={<ReloadOutlined />} onClick={fetchVisits}>
                        Làm mới
                    </Button>
                </div>

                <Table
                    columns={columns}
                    dataSource={queueVisits}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10, showTotal: (t) => `Tổng ${t} đang chờ` }}
                    scroll={{ x: 1100 }}
                    rowClassName={(record) =>
                        highlightedIds.has(record.id) ? 'reception-highlight-row' : ''
                    }
                    onRow={(record) => ({
                        onDoubleClick: () => selectCurrentVisit(record),
                        style: { cursor: 'pointer' },
                    })}
                />
            </Card>

            {/* Create Visit Modal */}
            <CreateVisitModal
                open={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSuccess={fetchVisits}
            />

            {/* Triage Modal */}
            <TriageModal
                visit={triageVisit}
                open={triageModalOpen}
                departments={departments}
                onClose={() => setTriageModalOpen(false)}
                onSuccess={handleTriageSuccess}
            />
        </div>
    );
}
