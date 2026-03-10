'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Layout, Input, Button, Typography, Tag, Space, Spin, Tooltip, Select, Badge } from 'antd';
import { SearchOutlined, SoundOutlined, ClockCircleOutlined, FileTextOutlined, BellOutlined } from '@ant-design/icons';
import { visitApi, qmsApi } from '@/lib/services';
import type { Visit, Patient, ServiceStation } from '@/types';
import { useClinicalSocket, ClinicalVisitPayload } from '@/hooks/useClinicalSocket';
import { toast } from 'sonner';
import dayjs from 'dayjs';
import { useRouter, useParams } from 'next/navigation';

const { Sider } = Layout;
const { Text } = Typography;

// ── Sound ────────────────────────────────────────────────────
const SOUND_KEY = 'his_clinical_sound';

function getSoundEnabled(): boolean {
    if (typeof window === 'undefined') return true;
    const stored = localStorage.getItem(SOUND_KEY);
    return stored !== 'off';
}

function playNotificationSound() {
    try {
        const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        oscillator.frequency.value = 1800;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.3;

        oscillator.start();
        oscillator.stop(audioCtx.currentTime + 0.15);

        // Second beep after a short pause
        const osc2 = audioCtx.createOscillator();
        const gain2 = audioCtx.createGain();
        osc2.connect(gain2);
        gain2.connect(audioCtx.destination);
        osc2.frequency.value = 2200;
        osc2.type = 'sine';
        gain2.gain.value = 0.25;
        osc2.start(audioCtx.currentTime + 0.2);
        osc2.stop(audioCtx.currentTime + 0.35);

        osc2.onended = () => {
            gainNode.disconnect();
            gain2.disconnect();
            audioCtx.close();
        };
    } catch {
        // Silently fail
    }
}

// ── Configs ──────────────────────────────────────────────────
const statusColors: Record<string, string> = {
    WAITING: 'default',
    IN_PROGRESS: 'processing',
    PENDING_RESULTS: 'purple',
    COMPLETED: 'success',
};

const statusLabels: Record<string, string> = {
    WAITING: 'Chờ khám',
    IN_PROGRESS: 'Đang khám',
    PENDING_RESULTS: 'Chờ kết quả',
    COMPLETED: 'Hoàn thành',
};

// Prevent duplicate WS toasts across hot-reloads
const globalHandledVisitIds = new Set<string>();

// ── Component ────────────────────────────────────────────────
export default function QueueSidebar() {
    const router = useRouter();
    const params = useParams();
    const activeVisitId = params?.visitId as string | undefined;

    const [visits, setVisits] = useState<Visit[]>([]);
    const [loading, setLoading] = useState(false);
    const [searchText, setSearchText] = useState('');

    // Station selection
    const [stations, setStations] = useState<ServiceStation[]>([]);
    const [selectedStation, setSelectedStation] = useState<string | null>(null);

    // Sound & notification
    const [soundEnabled, setSoundEnabled] = useState(true);
    const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set());
    const highlightTimersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

    // Load sound preference
    useEffect(() => {
        setSoundEnabled(getSoundEnabled());
    }, []);

    // ── Fetch stations (DOCTOR type) ─────────────────────────
    const fetchStations = useCallback(async () => {
        try {
            const data = await qmsApi.getStations('DOCTOR');
            setStations(data);
            if (data.length > 0 && !selectedStation) {
                setSelectedStation(data[0].id);
            }
        } catch (error) {
            console.error('Error fetching stations:', error);
        }
    }, [selectedStation]);

    useEffect(() => {
        fetchStations();
    }, [fetchStations]);

    // ── Fetch visits (filtered by station) ───────────────────
    const fetchVisits = useCallback(async () => {
        if (!selectedStation) return;
        setLoading(true);
        try {
            const response = await visitApi.getAll({
                today: true,
                station_id: selectedStation,
                status: 'WAITING,IN_PROGRESS,PENDING_RESULTS',
            });
            const list = Array.isArray(response) ? response : (response.results || []);
            // Filter by clinical statuses (in case backend doesn't support comma-sep)
            const clinicalVisits = list.filter((v: Visit) =>
                ['WAITING', 'IN_PROGRESS', 'PENDING_RESULTS'].includes(v.status)
            );
            setVisits(clinicalVisits);
        } catch (error) {
            console.error('Error fetching queue:', error);
        } finally {
            setLoading(false);
        }
    }, [selectedStation]);

    useEffect(() => {
        fetchVisits();
    }, [fetchVisits]);

    // ── WebSocket: Real-time notifications ───────────────────

    const handleNewPatientAssigned = useCallback((wsVisit: ClinicalVisitPayload) => {
        if (globalHandledVisitIds.has(wsVisit.id)) return;
        globalHandledVisitIds.add(wsVisit.id);

        const patientName = wsVisit.patient_name || 'Bệnh nhân';
        toast.success(`${patientName} được phân đến phòng`, {
            description: `Mã: ${wsVisit.visit_code} — ${wsVisit.chief_complaint || 'Khám bệnh'}`,
        });

        if (soundEnabled) {
            playNotificationSound();
        }

        // Refresh visits list
        fetchVisits();

        // Highlight the new visit
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
        }, 5000);
        highlightTimersRef.current.set(wsVisit.id, timer);
    }, [soundEnabled, fetchVisits]);

    const handleQueueUpdate = useCallback(() => {
        fetchVisits();
    }, [fetchVisits]);

    const { isConnected } = useClinicalSocket({
        stationId: selectedStation,
        onNewPatientAssigned: handleNewPatientAssigned,
        onQueueUpdate: handleQueueUpdate,
    });

    // Cleanup highlight timers
    useEffect(() => {
        return () => {
            highlightTimersRef.current.forEach((t) => clearTimeout(t));
        };
    }, []);

    // ── Sound toggle ─────────────────────────────────────────
    const toggleSound = useCallback(() => {
        setSoundEnabled((prev) => {
            const next = !prev;
            localStorage.setItem(SOUND_KEY, next ? 'on' : 'off');
            if (next) playNotificationSound();
            return next;
        });
    }, []);

    // ── Search filter ────────────────────────────────────────
    const filteredVisits = visits.filter(visit => {
        if (!searchText) return true;
        const patient = (typeof visit.patient === 'object' ? visit.patient : (visit as unknown as Record<string, unknown>).patient_detail) as Patient | null;
        if (!patient) return false;
        const searchLower = searchText.toLowerCase();
        const fullName = (patient.full_name || `${patient.last_name || ''} ${patient.first_name || ''}`).toLowerCase();
        const code = (patient.patient_code || '').toLowerCase();
        return fullName.includes(searchLower) || code.includes(searchLower);
    });

    // ── Call next patient ────────────────────────────────────
    const callNextPatient = () => {
        const nextWaiting = visits.find(v => v.status === 'WAITING');
        if (nextWaiting) {
            handleSelectPatient(nextWaiting);
            toast.info('Đã gọi bệnh nhân tiếp theo');
        } else {
            toast.info('Không có bệnh nhân đang chờ');
        }
    };

    const handleSelectPatient = async (visit: Visit) => {
        if (visit.status === 'WAITING') {
            try {
                await visitApi.update(visit.id, { status: 'IN_PROGRESS' });
                fetchVisits();
            } catch (error) {
                console.error('Error updating status:', error);
            }
        }
        router.push(`/dashboard/clinical/${visit.id}`);
    };

    // Count by status
    const waitingCount = visits.filter(v => v.status === 'WAITING').length;
    const inProgressCount = visits.filter(v => v.status === 'IN_PROGRESS').length;

    return (
        <Sider
            width={300}
            theme="light"
            className="border-r border-gray-200 flex flex-col h-full !bg-white queue-sidebar"
            style={{ height: 'calc(100vh - 64px)', overflow: 'hidden', backgroundColor: '#ffffff' }}
        >
            <div className="px-2 py-1.5 border-b border-gray-200 flex flex-col gap-1">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <Space size={4}>
                        <FileTextOutlined className="text-blue-500" />
                        <Text strong style={{ fontSize: 13 }}>Hàng đợi</Text>
                        <Badge count={visits.length} style={{ backgroundColor: '#1890ff' }} overflowCount={99} />
                    </Space>
                    <Space size={2}>
                        <Tooltip title={isConnected ? 'Đã kết nối' : 'Mất kết nối'}>
                            <Badge dot color={isConnected ? 'green' : 'red'}>
                                <BellOutlined style={{ fontSize: 12, color: '#999' }} />
                            </Badge>
                        </Tooltip>
                        <Tooltip title={soundEnabled ? 'Tắt âm thanh' : 'Bật âm thanh'}>
                            <Button type="text" size="small" icon={<SoundOutlined />} onClick={toggleSound}
                                style={{ color: soundEnabled ? '#1890ff' : '#bfbfbf', padding: '0 4px' }} />
                        </Tooltip>
                    </Space>
                </div>
                {/* Station + status row */}
                <Select
                    placeholder="Chọn phòng khám"
                    value={selectedStation}
                    onChange={(value) => setSelectedStation(value)}
                    style={{ width: '100%' }}
                    size="small"
                    options={stations.map((s) => ({ value: s.id, label: `[${s.code}] ${s.name}` }))}
                    notFoundContent="Chưa có phòng khám"
                />
                <div className="flex gap-1">
                    <Tag color="gold" className="flex-1 text-center m-0" style={{ fontSize: 11, lineHeight: '20px' }}>Chờ: {waitingCount}</Tag>
                    <Tag color="blue" className="flex-1 text-center m-0" style={{ fontSize: 11, lineHeight: '20px' }}>Khám: {inProgressCount}</Tag>
                </div>
                <Button type="primary" icon={<SoundOutlined />} size="small" className="w-full"
                    onClick={callNextPatient} disabled={!selectedStation || waitingCount === 0}>
                    <span style={{ fontSize: 12, fontWeight: 600 }}>Gọi bệnh nhân tiếp</span>
                </Button>
                <Input prefix={<SearchOutlined className="text-gray-400" />} placeholder="Tìm tên, PID..."
                    value={searchText} onChange={(e) => setSearchText(e.target.value)} size="small" />
            </div>

            <div className="flex-1 overflow-y-auto bg-slate-50 px-1.5 py-1">
                <Spin spinning={loading}>
                    {filteredVisits.length === 0 ? (
                        <div className="text-center text-gray-400 text-sm py-8">
                            {selectedStation ? 'Chưa có bệnh nhân' : 'Chọn phòng khám'}
                        </div>
                    ) : filteredVisits.map((item) => {
                        const patient = (typeof item.patient === 'object' ? item.patient : (item as unknown as Record<string, unknown>).patient_detail) as Patient | null;
                        const isSelected = activeVisitId === item.id;
                        const isHighlighted = highlightedIds.has(item.id);
                        const checkInTime = item.check_in_time ? dayjs(item.check_in_time).format('HH:mm') : '--:--';
                        const fullName = patient ? (patient.full_name || `${patient.last_name || ''} ${patient.first_name || ''}`.trim()) : 'Unknown';
                        const pid = patient ? patient.patient_code : 'Unknown';
                        const age = patient?.date_of_birth ? dayjs().diff(dayjs(patient.date_of_birth), 'year') : '--';
                        const gender = patient?.gender === 'M' ? 'Nam' : 'Nữ';
                        const reason = item.chief_complaint || 'Khám bệnh';

                        return (
                            <div
                                key={item.id}
                                onClick={() => handleSelectPatient(item)}
                                className={`mb-1 px-2.5 py-1.5 rounded-lg border cursor-pointer transition-all ${isHighlighted ? 'bg-green-50 border-green-400 shadow-md animate-pulse'
                                    : isSelected ? 'bg-blue-50 border-blue-400 shadow-sm'
                                        : 'bg-white border-gray-200 hover:border-blue-300 hover:shadow-sm'
                                    }`}
                            >
                                <div className="flex justify-between items-center">
                                    <Text strong style={{ fontSize: 13 }} className={isHighlighted ? 'text-green-700' : isSelected ? 'text-blue-700' : 'text-gray-800'}>
                                        {fullName}
                                    </Text>
                                    <span className="text-gray-400" style={{ fontSize: 11 }}>
                                        <ClockCircleOutlined style={{ marginRight: 2 }} />{checkInTime}
                                    </span>
                                </div>
                                <div style={{ fontSize: 11 }} className="text-gray-500">{pid} • {age}T - {gender}</div>
                                <div className="flex justify-between items-center mt-0.5">
                                    <span style={{ fontSize: 11 }} className="text-gray-500 truncate flex-1 mr-2">{reason}</span>
                                    <Tag color={statusColors[item.status] || 'default'}
                                        className="m-0 rounded-full border-0" style={{ fontSize: 10, lineHeight: '16px', padding: '0 6px' }}>
                                        {statusLabels[item.status] || item.status}
                                    </Tag>
                                </div>
                            </div>
                        );
                    })}
                </Spin>
            </div>
        </Sider>
    );
}
