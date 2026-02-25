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
    Divider,
} from 'antd';
import {
    PlusOutlined,
    SearchOutlined,
    UserAddOutlined,
    MedicineBoxOutlined,
    ReloadOutlined,
    CheckOutlined,
    SoundOutlined,
    CloseCircleOutlined,
    ForwardOutlined,
    EyeInvisibleOutlined,
    TeamOutlined,
    PhoneOutlined,
    AlertOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { visitApi, departmentApi, patientApi, qmsApi } from '@/lib/services';
import type { Visit, Department, CalledPatient, ServiceStation, NoShowEntry } from '@/types';
import TriageModal from './TriageModal';
import CreateVisitModal from './CreateVisitModal';
import { useReceptionSocket, WsVisitPayload } from '@/hooks/useReceptionSocket';
import { useQmsSocket } from '@/hooks/useQmsSocket';
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

const sourceConfig: Record<string, { color: string; label: string }> = {
    EMERGENCY: { color: 'red', label: 'Cấp cứu' },
    ONLINE_BOOKING: { color: 'blue', label: 'Đặt lịch' },
    WALK_IN: { color: 'default', label: 'Vãng lai' },
};

const MAX_CONCURRENT = 3;

// ── Component ────────────────────────────────────────────────

export default function ReceptionPage() {
    const { message } = App.useApp();
    const [visits, setVisits] = useState<Visit[]>([]);
    const [loading, setLoading] = useState(false);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [isEmergencyModalOpen, setIsEmergencyModalOpen] = useState(false);

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
    const suppressWsToastUntilRef = useRef<number>(0);

    // QMS state
    const [stations, setStations] = useState<ServiceStation[]>([]);
    const [selectedStation, setSelectedStation] = useState<string | null>(null);
    const [currentlyServing, setCurrentlyServing] = useState<CalledPatient[]>([]);
    const [noShowList, setNoShowList] = useState<NoShowEntry[]>([]);
    const [callLoading, setCallLoading] = useState(false);
    const [pendingEntryId, setPendingEntryId] = useState<string | null>(null);

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

    const fetchStations = useCallback(async () => {
        try {
            // Chỉ lấy stations loại RECEPTION — khớp với station mà kiosk tạo entry
            const data = await qmsApi.getStations('RECEPTION');
            setStations(data);
            if (data.length > 0 && !selectedStation) {
                setSelectedStation(data[0].id);
            }
        } catch (error) {
            console.error('Error fetching stations:', error);
        }
    }, [selectedStation]);

    const fetchQueueBoard = useCallback(async () => {
        if (!selectedStation) return;
        try {
            const data = await qmsApi.getQueueBoard(selectedStation);
            setCurrentlyServing(data.currently_serving || []);
            setNoShowList(data.no_show_list || []);
        } catch (err) {
            console.error('fetchQueueBoard failed:', err);
            setCurrentlyServing([]);
            setNoShowList([]);
        }
    }, [selectedStation]);

    useEffect(() => {
        fetchVisits();
        fetchDepartments();
        fetchStations();
    }, [fetchVisits, fetchDepartments, fetchStations]);

    // Queue board via WebSocket (replaces polling)
    useQmsSocket({
        stationId: selectedStation,
        onBoardUpdate: useCallback((data: { currently_serving: CalledPatient[]; no_show_list: NoShowEntry[] }) => {
            setCurrentlyServing(data.currently_serving || []);
            setNoShowList(data.no_show_list || []);
        }, []),
    });

    // ── WebSocket: Real-time new visits ──────────────────────

    const handleNewVisitWs = useCallback((wsVisit: WsVisitPayload) => {
        // Skip toast if this visit was just created locally (suppress for 3s window)
        const now = Date.now();
        if (now < suppressWsToastUntilRef.current) {
            // Still refresh the table, just skip toast + sound
        } else {
            const patientName = wsVisit.patient?.full_name || 'Bệnh nhân';
            toast.success(`${patientName} vừa đăng ký thành công`, {
                description: `Mã: ${wsVisit.visit_code} — STT: ${wsVisit.queue_number}`,
            });

            if (soundEnabled) {
                playTing();
            }
        }

        fetchVisits();

        setHighlightedIds((prev) => {
            const next = new Set(prev);
            next.add(wsVisit.id);
            return next;
        });

        const timer = setTimeout(() => {
            setHighlightedIds((prev) => {
                const next = new Set(prev);
                next.delete(wsVisit.id);
                return next;
            });
            highlightTimersRef.current.delete(wsVisit.id);
        }, 3000);
        highlightTimersRef.current.set(wsVisit.id, timer);

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

    const handleTriageSuccess = useCallback(async () => {
        fetchVisits();
        // Auto-complete QMS entry after triage is confirmed
        if (pendingEntryId) {
            try {
                await qmsApi.completeQueue(pendingEntryId);
            } catch (e) {
                console.error('Failed to complete QMS entry:', e);
            }
            setPendingEntryId(null);
        }
        fetchQueueBoard();
    }, [fetchVisits, fetchQueueBoard, pendingEntryId]);

    // ── Sound toggle ─────────────────────────────────────────

    const toggleSound = useCallback(() => {
        setSoundEnabled((prev) => {
            const next = !prev;
            localStorage.setItem(SOUND_KEY, next ? 'on' : 'off');
            if (next) playTing();
            return next;
        });
    }, []);

    // ── QMS Actions ──────────────────────────────────────────

    const handleCallNext = async () => {
        if (!selectedStation) return;
        setCallLoading(true);
        try {
            const result = await qmsApi.doctorCallNext(selectedStation);
            if (result.success && result.called_patient) {
                const p = result.called_patient;
                if ('speechSynthesis' in window) {
                    const utterance = new SpeechSynthesisUtterance(
                        `Mời số ${p.daily_sequence}, ${p.patient_name || ''}, đến ${p.station_name}`
                    );
                    utterance.lang = 'vi-VN';
                    utterance.rate = 0.9;
                    speechSynthesis.speak(utterance);
                }
                message.success(`Đã gọi: ${p.queue_number} — ${p.patient_name}`);
                fetchQueueBoard();
            } else {
                message.info(result.message || 'Không còn bệnh nhân trong hàng đợi');
            }
        } catch (error: unknown) {
            const err = error as { response?: { status?: number; data?: { message?: string } } };
            if (err?.response?.status === 429) {
                message.warning(err.response.data?.message || `Đã đạt tối đa ${MAX_CONCURRENT} số đang gọi`);
            } else {
                message.error('Không thể gọi bệnh nhân tiếp theo');
            }
        } finally {
            setCallLoading(false);
        }
    };

    const handleTriageFromCall = useCallback(async (patient: CalledPatient) => {
        try {
            setPendingEntryId(patient.entry_id);
            const visit = await visitApi.getById(patient.visit_id);
            openTriageModal(visit);
        } catch {
            setPendingEntryId(null);
            message.error('Không thể mở phân luồng');
        }
    }, [message, openTriageModal]);

    const handleNoShow = async (entryId: string) => {
        try {
            await qmsApi.noShowQueue(entryId);
            message.warning('Đã gọi nhưng không có mặt');
            fetchQueueBoard();
        } catch {
            message.error('Không thể cập nhật');
        }
    };

    const handleRecall = async (entry: NoShowEntry) => {
        try {
            await qmsApi.recallQueue(entry.entry_id);
            if ('speechSynthesis' in window) {
                const utterance = new SpeechSynthesisUtterance(
                    `Mời số ${entry.daily_sequence}, ${entry.patient_name || ''}, vui lòng quay lại quầy tiếp đón`
                );
                utterance.lang = 'vi-VN';
                utterance.rate = 0.9;
                speechSynthesis.speak(utterance);
            }
            message.success(`Đã gọi lại: ${entry.queue_number} — ${entry.patient_name}`);
            fetchQueueBoard();
        } catch {
            message.error('Không thể gọi lại bệnh nhân');
        }
    };

    // ── Computed Data ────────────────────────────────────────

    const todayVisits = useMemo(() => {
        return visits.filter((v) => ['CHECK_IN', 'TRIAGE', 'WAITING', 'IN_PROGRESS'].includes(v.status));
    }, [visits]);

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
            render: (s: string) => {
                const config = statusConfig[s] || { color: 'default', label: s };
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
        {
            title: 'Khoa',
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
            title: 'Trạng thái',
            key: 'status_display',
            width: 160,
            render: (_: unknown, record: Visit) => {
                const config = statusConfig[record.status] || { color: 'default', label: record.status };
                if (record.confirmed_department_detail) {
                    return (
                        <Space direction="vertical" size={2}>
                            <Tag color={config.color}>{config.label}</Tag>
                            <Tag color="blue" icon={<CheckOutlined />}>{record.confirmed_department_detail.name}</Tag>
                        </Space>
                    );
                }
                return <Tag color={config.color}>{config.label}</Tag>;
            },
        },
    ], []);

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
                    <Select
                        placeholder="Chọn điểm dịch vụ"
                        value={selectedStation}
                        onChange={setSelectedStation}
                        style={{ width: 220 }}
                        options={stations.map((s) => ({
                            value: s.id,
                            label: `[${s.code}] ${s.name}`,
                        }))}
                    />
                    <Input.Search
                        placeholder="Mã màn hình"
                        style={{ width: 160 }}
                        enterButton="Liên kết"
                        onSearch={async (code) => {
                            if (!code.trim()) return;
                            if (!selectedStation) {
                                message.warning('Vui lòng chọn điểm dịch vụ trước');
                                return;
                            }
                            try {
                                const result = await qmsApi.pairDisplay(code, selectedStation);
                                message.success(result.message);
                            } catch (err: unknown) {
                                const error = err as { response?: { data?: { error?: string } } };
                                message.error(error?.response?.data?.error || 'Không thể liên kết');
                            }
                        }}
                    />
                    <Tooltip title={soundEnabled ? 'Tắt âm thanh' : 'Bật âm thanh'}>
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
                    <Button danger icon={<AlertOutlined />} onClick={() => setIsEmergencyModalOpen(true)}>
                        Tiếp nhận cấp cứu
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

            {/* ══════════════ ĐANG GỌI — Multi-Call Panel ══════════════ */}
            <Card
                title={
                    <Space>
                        <SoundOutlined className="text-blue-500" />
                        <span>Đang gọi</span>
                        <Badge
                            count={currentlyServing.length}
                            style={{ backgroundColor: currentlyServing.length >= MAX_CONCURRENT ? '#ff4d4f' : '#1890ff' }}
                        />
                        <Text type="secondary" className="text-xs">
                            (tối đa {MAX_CONCURRENT})
                        </Text>
                    </Space>
                }
                extra={
                    <Space>
                        <Button
                            type="primary"
                            icon={<SoundOutlined />}
                            onClick={handleCallNext}
                            loading={callLoading}
                            disabled={!selectedStation || currentlyServing.length >= MAX_CONCURRENT}
                        >
                            Gọi tiếp
                        </Button>
                        <Button icon={<ReloadOutlined />} onClick={fetchQueueBoard}>
                            Làm mới
                        </Button>
                    </Space>
                }
                className="border-blue-200"
                styles={{ header: { borderBottom: '2px solid #1677ff' } }}
            >
                {currentlyServing.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        {currentlyServing.map((patient) => (
                            <Card
                                key={patient.entry_id}
                                size="small"
                                className="border-2 border-blue-300 bg-blue-50"
                            >
                                <div className="text-center">
                                    <Tag color={sourceConfig[patient.source_type]?.color || 'default'} className="mb-2">
                                        {sourceConfig[patient.source_type]?.label || patient.source_type}
                                    </Tag>
                                    <div
                                        className="text-5xl font-bold mb-1"
                                        style={{ color: patient.source_type === 'EMERGENCY' ? '#ff4d4f' : '#1890ff' }}
                                    >
                                        {patient.daily_sequence}
                                    </div>
                                    <Tag color="blue" className="text-sm px-3 py-0.5 mb-1">
                                        {patient.queue_number}
                                    </Tag>
                                    <div className="text-sm text-gray-600 mb-1">
                                        {patient.patient_name || 'Bệnh nhân'}
                                    </div>
                                    {patient.wait_time_minutes != null && (
                                        <Text type="secondary" className="text-xs">
                                            Chờ {patient.wait_time_minutes} phút
                                        </Text>
                                    )}
                                    <Divider className="!my-2" />
                                    <Space>
                                        <Tooltip title="Phân luồng bệnh nhân">
                                            <Button
                                                type="primary"
                                                size="small"
                                                icon={<MedicineBoxOutlined />}
                                                onClick={() => handleTriageFromCall(patient)}
                                            >
                                                Phân luồng
                                            </Button>
                                        </Tooltip>
                                        <Tooltip title="Đã gọi nhưng không có mặt">
                                            <Button
                                                danger
                                                size="small"
                                                icon={<EyeInvisibleOutlined />}
                                                onClick={() => handleNoShow(patient.entry_id)}
                                            >
                                                Vắng
                                            </Button>
                                        </Tooltip>
                                    </Space>
                                </div>
                            </Card>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-6">
                        <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description="Chưa có bệnh nhân nào đang gọi"
                        />
                        <Button
                            type="primary"
                            size="large"
                            icon={<SoundOutlined />}
                            onClick={handleCallNext}
                            loading={callLoading}
                            disabled={!selectedStation}
                            className="mt-4"
                        >
                            Gọi số đầu tiên
                        </Button>
                    </div>
                )}
            </Card>

            {/* ══════════════ DANH SÁCH VẮNG ══════════════ */}
            {noShowList.length > 0 && (
                <Card
                    size="small"
                    title={
                        <Space>
                            <EyeInvisibleOutlined className="text-red-500" />
                            <span>Vắng mặt</span>
                            <Badge count={noShowList.length} style={{ backgroundColor: '#ff4d4f' }} />
                        </Space>
                    }
                    className="border-red-200"
                    styles={{ header: { borderBottom: '2px solid #ff4d4f' } }}
                >
                    <div className="flex flex-wrap gap-3">
                        {noShowList.map((entry) => (
                            <div
                                key={entry.entry_id}
                                className="flex items-center gap-3 px-3 py-2 bg-red-50 border border-red-200 rounded-lg"
                            >
                                <div>
                                    <Text strong className="text-red-600">
                                        {entry.daily_sequence}
                                    </Text>
                                    <Text type="secondary" className="ml-2 text-xs">
                                        {entry.queue_number}
                                    </Text>
                                </div>
                                <Text className="text-sm">{entry.patient_name}</Text>
                                {entry.end_time && (
                                    <Text type="secondary" className="text-xs">
                                        {entry.end_time}
                                    </Text>
                                )}
                                <Button
                                    size="small"
                                    type="primary"
                                    ghost
                                    icon={<PhoneOutlined />}
                                    onClick={() => handleRecall(entry)}
                                >
                                    Gọi lại
                                </Button>
                            </div>
                        ))}
                    </div>
                </Card>
            )}

            {/* ══════════════ DANH SÁCH LƯỢT KHÁM ══════════════ */}
            <Card
                title={
                    <Space>
                        <TeamOutlined className="text-orange-500" />
                        <span>Lượt khám hôm nay</span>
                        <div className={badgePulse ? 'badge-pulse' : ''}>
                            <Badge
                                count={todayVisits.length}
                                style={{ backgroundColor: '#fa8c16' }}
                                overflowCount={999}
                            />
                        </div>
                    </Space>
                }
                extra={
                    <Button icon={<ReloadOutlined />} onClick={fetchVisits}>
                        Làm mới
                    </Button>
                }
            >
                <Table
                    columns={columns}
                    dataSource={todayVisits}
                    rowKey="id"
                    loading={loading}
                    pagination={{ pageSize: 10, showTotal: (t) => `Tổng ${t} lượt khám` }}
                    scroll={{ x: 1100 }}
                    rowClassName={(record) =>
                        highlightedIds.has(record.id) ? 'reception-highlight-row' : ''
                    }
                    size="small"
                />
            </Card>

            {/* Create Visit Modal */}
            <CreateVisitModal
                open={isModalOpen}
                onClose={() => setIsModalOpen(false)}
                onSuccess={() => { suppressWsToastUntilRef.current = Date.now() + 3000; fetchVisits(); }}
            />

            {/* Emergency Visit Modal */}
            <CreateVisitModal
                open={isEmergencyModalOpen}
                onClose={() => setIsEmergencyModalOpen(false)}
                onSuccess={() => { suppressWsToastUntilRef.current = Date.now() + 3000; fetchVisits(); }}
                emergencyMode
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
