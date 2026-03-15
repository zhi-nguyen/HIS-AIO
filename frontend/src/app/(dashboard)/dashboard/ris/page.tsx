'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
    Button, Space, Typography, Input, Tabs, Tooltip, message,
} from 'antd';
import {
    SettingOutlined, ZoomInOutlined, AimOutlined,
    SaveOutlined, CheckCircleOutlined, FileTextOutlined,
    AudioOutlined,
} from '@ant-design/icons';
import { risApi } from '@/lib/services';
import { toast } from 'sonner';
import dayjs from 'dayjs';
import dynamic from 'next/dynamic';

const RichTextEditor = dynamic(() => import('@/components/RichTextEditor'), { ssr: false });

const { Text } = Typography;
const { TextArea } = Input;

/* ══════════════════════════════════════════════════════════════════════
   TYPES
   ══════════════════════════════════════════════════════════════════════ */

interface ImagingOrder {
    id: string;
    accession_number?: string;
    visit: { visit_code: string } | string;
    patient: {
        patient_code: string;
        full_name?: string;
        first_name?: string;
        last_name?: string;
        date_of_birth?: string;
        gender?: string;
    };
    procedure: {
        id: string;
        code: string;
        name: string;
        body_part: string;
        modality: { code: string; name: string };
    };
    clinical_indication: string;
    status: string;
    priority: string;
    order_time: string;
    note?: string;
    execution?: {
        dicom_study_uid?: string;
        execution_note?: string;
    };
    result?: {
        findings: string;
        conclusion: string;
        recommendation?: string;
        is_abnormal: boolean;
        is_critical: boolean;
        is_verified: boolean;
    };
}

/* ══════════════════════════════════════════════════════════════════════
   CONFIG
   ══════════════════════════════════════════════════════════════════════ */

const getOhifBase = () => {
    if (typeof window === 'undefined') return 'http://localhost:3001';
    return `http://${window.location.hostname}:3001`;
};
const SOUND_KEY = 'his_ris_sound';

const modalityColors: Record<string, string> = {
    CT: '#6366f1', CR: '#0ea5e9', MR: '#8b5cf6', US: '#14b8a6',
    XR: '#f59e0b', DR: '#0ea5e9', MG: '#ec4899', NM: '#22c55e',
};

/* ══════════════════════════════════════════════════════════════════════
   SOUND
   ══════════════════════════════════════════════════════════════════════ */

function getSoundEnabled(): boolean {
    if (typeof window === 'undefined') return true;
    return localStorage.getItem(SOUND_KEY) !== 'off';
}

function playNotificationSound() {
    try {
        const ctx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.frequency.value = 1600; osc.type = 'sine'; gain.gain.value = 0.25;
        osc.start(); osc.stop(ctx.currentTime + 0.12);

        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.connect(gain2); gain2.connect(ctx.destination);
        osc2.frequency.value = 2000; osc2.type = 'sine'; gain2.gain.value = 0.2;
        osc2.start(ctx.currentTime + 0.18); osc2.stop(ctx.currentTime + 0.3);
        osc2.onended = () => { gain.disconnect(); gain2.disconnect(); ctx.close(); };
    } catch { /* ignore */ }
}

const globalHandledIds = new Set<string>();

/* ══════════════════════════════════════════════════════════════════════
   HELPER
   ══════════════════════════════════════════════════════════════════════ */
function patientName(p: ImagingOrder['patient']): string {
    return p?.full_name || `${p?.last_name || ''} ${p?.first_name || ''}`.trim() || 'Bệnh nhân';
}
function patientAge(p: ImagingOrder['patient']): string {
    if (!p?.date_of_birth) return '--';
    return `${dayjs().diff(dayjs(p.date_of_birth), 'year')}`;
}

/* ══════════════════════════════════════════════════════════════════════
   MAIN COMPONENT
   ══════════════════════════════════════════════════════════════════════ */

export default function RISWorkspacePage() {
    const [orders, setOrders] = useState<ImagingOrder[]>([]);
    const [loading, setLoading] = useState(false);
    const [selectedOrder, setSelectedOrder] = useState<ImagingOrder | null>(null);
    const [activeTab, setActiveTab] = useState('pending');
    const [searchText, setSearchText] = useState('');
    const [mainTab, setMainTab] = useState<'list' | 'report'>('list');

    // Report form
    const [findings, setFindings] = useState('');
    const [conclusion, setConclusion] = useState('');
    const [savingReport, setSavingReport] = useState(false);
    const [verifying, setVerifying] = useState(false);

    // Sound
    const [soundEnabled, setSoundEnabled] = useState(true);
    const soundRef = useRef(true);
    useEffect(() => { setSoundEnabled(getSoundEnabled()); }, []);
    useEffect(() => { soundRef.current = soundEnabled; }, [soundEnabled]);

    const selectedOrderRef = useRef<ImagingOrder | null>(null);
    useEffect(() => { selectedOrderRef.current = selectedOrder; }, [selectedOrder]);

    /* ── Fetch Orders ─────────────────────────────────────── */

    const fetchOrders = useCallback(async () => {
        setLoading(true);
        try {
            const res = await risApi.getOrders();
            setOrders(res.results || res || []);
        } catch {
            message.error('Không thể tải danh sách CĐHA');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => { fetchOrders(); }, [fetchOrders]);

    /* ── WebSocket ─────────────────────────────────────────── */

    useEffect(() => {
        let ws: WebSocket;
        let reconnectTimeout: NodeJS.Timeout;
        let isMounted = true;

        const connectWs = () => {
            if (!isMounted) return;
            const host = window.location.hostname;
            ws = new WebSocket(`ws://${host}:8000/ws/ris/updates/`);

            ws.onopen = () => console.log('WebSocket RIS connected');

            ws.onmessage = async (event) => {
                if (!isMounted) return;
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'ris_order_updated') {
                        const { order_id, action } = data;

                        if (action === 'created' && !globalHandledIds.has(order_id)) {
                            globalHandledIds.add(order_id);
                            try {
                                const newOrder = await risApi.getOrderById(order_id);
                                setOrders(prev => {
                                    const exists = prev.some(o => o.id === order_id);
                                    if (!exists) return [newOrder, ...prev];
                                    return prev.map(o => o.id === order_id ? newOrder : o);
                                });
                                toast.success('Chỉ định CĐHA mới', {
                                    description: `${patientName(newOrder.patient)} - ${newOrder.procedure?.name}`,
                                });
                                if (soundRef.current) playNotificationSound();
                            } catch { fetchOrders(); }
                            return;
                        }

                        try {
                            const updated = await risApi.getOrderById(order_id);
                            setOrders(prev => {
                                const exists = prev.some(o => o.id === order_id);
                                if (!exists) return [updated, ...prev];
                                return prev.map(o => o.id === order_id ? updated : o);
                            });
                            if (selectedOrderRef.current?.id === order_id) {
                                setSelectedOrder(updated);
                            }
                        } catch { fetchOrders(); }
                    }

                    if (data.type === 'ris_new_study') {
                        toast.info('Ảnh DICOM mới từ PACS', {
                            description: `Study: ${data.study_description || data.study_uid?.slice(0, 16)}`,
                        });
                        if (soundRef.current) playNotificationSound();
                        if (data.order_id) {
                            try {
                                const updated = await risApi.getOrderById(data.order_id);
                                setOrders(prev => prev.map(o => o.id === data.order_id ? updated : o));
                                if (selectedOrderRef.current?.id === data.order_id) {
                                    setSelectedOrder(updated);
                                }
                            } catch { /* ignore */ }
                        }
                    }
                } catch { /* parse error */ }
            };

            ws.onclose = () => {
                if (!isMounted) return;
                reconnectTimeout = setTimeout(connectWs, 3000);
            };
            ws.onerror = () => console.error('WebSocket RIS error');
        };

        connectWs();
        return () => {
            isMounted = false;
            clearTimeout(reconnectTimeout);
            ws?.close();
        };
    }, [fetchOrders]);

    /* ── OHIF Viewer ───────────────────────────────────────── */

    const studyUid = selectedOrder?.execution?.dicom_study_uid;
    const ohifUrl = studyUid
        ? `${getOhifBase()}/viewer?StudyInstanceUIDs=${studyUid}`
        : null;

    /* ── Select Order ──────────────────────────────────────── */

    const handleSelectOrder = async (order: ImagingOrder) => {
        try {
            const detail = await risApi.getOrderById(order.id);
            setSelectedOrder(detail);
            setFindings(detail.result?.findings || '');
            setConclusion(detail.result?.conclusion || '');
        } catch {
            setSelectedOrder(order);
            setFindings(order.result?.findings || '');
            setConclusion(order.result?.conclusion || '');
        }
        setMainTab('report');
    };

    /* ── Save / Verify ────────────────────────────────────── */

    const handleSaveReport = async () => {
        if (!selectedOrder) return;
        setSavingReport(true);
        try {
            await risApi.saveResult(selectedOrder.id, { findings, conclusion });
            toast.success('Đã lưu kết quả');
        } catch {
            toast.error('Lưu kết quả thất bại');
        } finally {
            setSavingReport(false);
        }
    };

    const handleVerify = async () => {
        if (!selectedOrder) return;
        setVerifying(true);
        try {
            // Lưu kết quả trước
            await risApi.saveResult(selectedOrder.id, { findings, conclusion });
            // Sau đó verify
            await risApi.verifyResult(selectedOrder.id);
            toast.success('Đã duyệt kết quả');
            setMainTab('list');
            // Refresh order list
            fetchOrders();
        } catch {
            toast.error('Duyệt kết quả thất bại');
        } finally {
            setVerifying(false);
        }
    };

    /* ── Key handler (F9) ─────────────────────────────────── */
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'F9') { e.preventDefault(); handleVerify(); }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [selectedOrder, findings, conclusion]);

    /* ── Derived data ─────────────────────────────────────── */

    const pendingOrders = orders.filter(o =>
        ['COMPLETED', 'REPORTED', 'IN_PROGRESS', 'SCHEDULED', 'PENDING'].includes(o.status)
    );
    const verifiedOrders = orders.filter(o => o.status === 'VERIFIED');
    const pendingCount = pendingOrders.length;
    const verifiedCount = verifiedOrders.length;

    const sourceOrders = activeTab === 'pending' ? pendingOrders : verifiedOrders;
    const filteredOrders = searchText
        ? sourceOrders.filter(o =>
            patientName(o.patient).toLowerCase().includes(searchText.toLowerCase()) ||
            o.procedure?.name?.toLowerCase().includes(searchText.toLowerCase())
        )
        : sourceOrders;

    /* ══════════════════════════════════════════════════════════════════════
       RENDER
       ══════════════════════════════════════════════════════════════════════ */

    return (
        <div style={{ display: 'flex', height: 'calc(100vh - 64px)', overflow: 'hidden', background: '#f5f5f5' }}>

            {/* ═══════ LEFT: DICOM VIEWER ═══════ */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', background: '#1a1a2e' }}>
                {/* Viewer Toolbar */}
                {selectedOrder && (
                    <div style={{
                        height: 40, background: '#16162a', borderBottom: '1px solid #2d2d4a',
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        padding: '0 16px',
                    }}>
                        <Space size={8}>
                            <Tooltip title="Cài đặt"><Button type="text" size="small" icon={<SettingOutlined />} style={{ color: '#9ca3af', border: 'none', background: 'transparent' }} /></Tooltip>
                            <Tooltip title="Zoom"><Button type="text" size="small" icon={<ZoomInOutlined />} style={{ color: '#9ca3af', border: 'none', background: 'transparent' }} /></Tooltip>
                            <Tooltip title="Crosshair"><Button type="text" size="small" icon={<AimOutlined />} style={{ color: '#9ca3af', border: 'none', background: 'transparent' }} /></Tooltip>
                        </Space>
                        <Text style={{ color: '#9ca3af', fontSize: 12, fontFamily: 'monospace' }}>
                            {selectedOrder.accession_number || selectedOrder.id.slice(0, 8).toUpperCase()}
                            {' | Acc: '}{selectedOrder.accession_number || '--'}
                            {' | '}{selectedOrder.procedure?.modality?.code}
                        </Text>
                    </div>
                )}

                {/* Viewer Content */}
                <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {!selectedOrder ? (
                        <div style={{ textAlign: 'center', color: '#6b7280' }}>
                            <FileTextOutlined style={{ fontSize: 48, marginBottom: 12, color: '#4b5563' }} />
                            <div style={{ fontSize: 14 }}>Chọn một phiếu để xem ảnh DICOM</div>
                        </div>
                    ) : ohifUrl ? (
                        <iframe
                            key={studyUid}
                            src={ohifUrl}
                            style={{ width: '100%', height: '100%', border: 'none' }}
                            title="OHIF Viewer"
                            allow="clipboard-read; clipboard-write; fullscreen"
                        />
                    ) : (
                        <div style={{ textAlign: 'center', color: '#6b7280' }}>
                            <FileTextOutlined style={{ fontSize: 48, marginBottom: 12, color: '#4b5563' }} />
                            <div style={{ fontSize: 14 }}>Chưa có ảnh DICOM cho ca này</div>
                            <div style={{ fontSize: 12, color: '#4b5563', marginTop: 4 }}>
                                Ảnh sẽ tự động hiển thị khi máy chụp gửi về PACS
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* ═══════ RIGHT: COMBINED PANEL ═══════ */}
            <div style={{
                width: 400, minWidth: 360, borderLeft: '1px solid #e5e7eb',
                background: '#fff', display: 'flex', flexDirection: 'column',
                overflow: 'hidden',
            }}>
                {/* Custom Tab Header */}
                <div style={{ display: 'flex', borderBottom: '2px solid #f0f0f0', background: '#fafafa' }}>
                    <div
                        onClick={() => setMainTab('list')}
                        style={{
                            flex: 1, textAlign: 'center', padding: '13px 0', cursor: 'pointer',
                            borderBottom: mainTab === 'list' ? '2px solid #4f46e5' : '2px solid transparent',
                            color: mainTab === 'list' ? '#4f46e5' : '#6b7280',
                            fontWeight: mainTab === 'list' ? 600 : 400,
                            transition: 'all 0.2s', fontSize: 13,
                        }}
                    >
                        <FileTextOutlined style={{ marginRight: 6 }} />
                        Danh sách ca ({orders.length})
                    </div>
                    <div
                        onClick={() => setMainTab('report')}
                        style={{
                            flex: 1, textAlign: 'center', padding: '13px 0', cursor: 'pointer',
                            borderBottom: mainTab === 'report' ? '2px solid #4f46e5' : '2px solid transparent',
                            color: mainTab === 'report' ? '#4f46e5' : '#6b7280',
                            fontWeight: mainTab === 'report' ? 600 : 400,
                            transition: 'all 0.2s', fontSize: 13,
                        }}
                    >
                        <FileTextOutlined style={{ marginRight: 6 }} />
                        Viết kết quả
                    </div>
                </div>

                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

                    {/* ─── TAB: LIST ─── */}
                    <div style={{ display: mainTab === 'list' ? 'flex' : 'none', flexDirection: 'column', height: '100%' }}>

                        {/* Search */}
                        <div style={{ padding: '10px 12px 0' }}>
                            <Input
                                placeholder="Tìm bệnh nhân, dịch vụ..."
                                value={searchText}
                                onChange={e => setSearchText(e.target.value)}
                                allowClear
                                size="small"
                            />
                        </div>

                        {/* Sub-tabs: Pending / Verified */}
                        <Tabs
                            activeKey={activeTab}
                            onChange={setActiveTab}
                            size="small"
                            centered
                            style={{ margin: 0, marginTop: 4 }}
                            tabBarStyle={{ marginBottom: 0 }}
                            items={[
                                { key: 'pending', label: <span>Chờ đọc ({pendingCount})</span> },
                                { key: 'verified', label: <span>Đã duyệt ({verifiedCount})</span> },
                            ]}
                        />

                        {/* Order Cards */}
                        <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px', scrollbarWidth: 'thin', background: '#f8fafc' }}>
                            {filteredOrders.length === 0 && (
                                <div style={{ textAlign: 'center', color: '#9ca3af', padding: 32 }}>
                                    Không có phiếu nào
                                </div>
                            )}
                            {filteredOrders.map(order => {
                                const isSelected = selectedOrder?.id === order.id;
                                const modCode = order.procedure?.modality?.code || '?';
                                const _modColor = modalityColors[modCode] || '#6b7280'; // eslint-disable-line @typescript-eslint/no-unused-vars

                                return (
                                    <div
                                        key={order.id}
                                        onClick={() => handleSelectOrder(order)}
                                        style={{
                                            padding: '12px',
                                            borderRadius: 8,
                                            marginBottom: 8,
                                            cursor: 'pointer',
                                            border: isSelected ? '2px solid #4f46e5' : '1px solid #e2e8f0',
                                            background: isSelected ? '#eef2ff' : order.priority === 'STAT' ? '#fef2f2' : '#fff',
                                            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
                                            transition: 'all 0.15s',
                                        }}
                                    >
                                        {/* Header row */}
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                                            <div style={{
                                                background: '#e0e7ff', color: '#4f46e5', borderRadius: 4,
                                                fontWeight: 700, fontSize: 11, padding: '2px 7px',
                                            }}>
                                                {modCode}
                                            </div>
                                            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                                                <Text style={{ fontSize: 11, color: '#94a3b8' }}>
                                                    {dayjs(order.order_time).format('HH:mm DD/MM')}
                                                </Text>
                                                {order.priority === 'STAT' && (
                                                    <Text style={{ fontSize: 11, fontWeight: 700, color: '#ef4444' }}>CẤP CỨU</Text>
                                                )}
                                            </div>
                                        </div>

                                        {/* Patient name */}
                                        <Text strong style={{ fontSize: 14, display: 'block', marginBottom: 2, color: '#0f172a' }}>
                                            {patientName(order.patient)}
                                        </Text>
                                        {/* Procedure */}
                                        <Text style={{ fontSize: 12, color: '#475569', display: 'block', marginBottom: 8 }}>
                                            {order.procedure?.name}
                                        </Text>

                                        {/* Footer row */}
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                            <Text style={{ fontSize: 12, color: '#64748b' }}>
                                                {order.patient?.gender === 'F' ? 'Nữ' : 'Nam'} • {patientAge(order.patient)} tuổi
                                            </Text>
                                            {order.status === 'VERIFIED' ? (
                                                <div style={{ fontSize: 11, color: '#166534', background: '#dcfce7', padding: '2px 8px', borderRadius: 12 }}>
                                                    Đã duyệt
                                                </div>
                                            ) : (
                                                <div style={{ fontSize: 11, color: '#b45309', background: '#fef3c7', padding: '2px 8px', borderRadius: 12 }}>
                                                    Chờ đọc
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    </div>

                    {/* ─── TAB: REPORT ─── */}
                    <div style={{ display: mainTab === 'report' ? 'flex' : 'none', flexDirection: 'column', height: '100%' }}>
                        {!selectedOrder ? (
                            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#9ca3af', gap: 12 }}>
                                <FileTextOutlined style={{ fontSize: 32, color: '#c7d2fe' }} />
                                <Text type="secondary">Chọn ca từ tab &quot;Danh sách ca&quot; để đọc kết quả</Text>
                                <Button size="small" onClick={() => setMainTab('list')}>Xem danh sách</Button>
                            </div>
                        ) : (
                            <>
                                {/* Patient header */}
                                <div style={{ padding: '14px 16px 12px', borderBottom: '1px solid #f0f0f0', background: '#fafafa' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                                        <Text strong style={{ fontSize: 15, color: '#0f172a' }}>
                                            {patientName(selectedOrder.patient)}
                                        </Text>
                                        <Text style={{ fontSize: 11, color: '#64748b' }}>
                                            PID: {selectedOrder.patient?.patient_code}
                                        </Text>
                                    </div>
                                    <Text style={{ fontSize: 12, color: '#64748b', marginTop: 2, display: 'block' }}>
                                        {selectedOrder.patient?.gender === 'F' ? 'Nữ' : 'Nam'} • {patientAge(selectedOrder.patient)} tuổi
                                        {' | '}{selectedOrder.procedure?.name}
                                    </Text>
                                </div>

                                {/* Clinical indication */}
                                <div style={{ padding: '10px 16px', borderBottom: '1px solid #f0f0f0', background: '#fff' }}>
                                    <Text style={{ fontSize: 12, color: '#475569' }}>
                                        Lâm sàng: {selectedOrder.clinical_indication || 'Không ghi'}
                                    </Text>
                                </div>

                                {/* Form body */}
                                <div style={{ flex: 1, overflowY: 'auto', padding: '14px 16px', scrollbarWidth: 'thin' }}>
                                    {/* Toolbar */}
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
                                        <Button size="small" icon={<FileTextOutlined />}>Mẫu KQ</Button>
                                        <Button size="small" icon={<AudioOutlined />} style={{ color: '#ef4444', borderColor: '#fca5a5', background: '#fef2f2' }}>
                                            Voice (F2)
                                        </Button>
                                    </div>

                                    {/* Findings */}
                                    <div style={{ marginBottom: 14 }}>
                                        <Text style={{ fontSize: 12, color: '#475569', display: 'block', marginBottom: 6, fontWeight: 600 }}>
                                            Mô tả hình ảnh (Findings)
                                        </Text>
                                        <RichTextEditor
                                            value={findings}
                                            onChange={setFindings}
                                            placeholder="Mô tả những gì quan sát được trên phim..."
                                        />
                                    </div>

                                    {/* Conclusion */}
                                    <div style={{ marginBottom: 14 }}>
                                        <Text style={{ fontSize: 12, color: '#475569', display: 'block', marginBottom: 6, fontWeight: 600 }}>
                                            Kết luận (Conclusion)
                                        </Text>
                                        <RichTextEditor
                                            value={conclusion}
                                            onChange={setConclusion}
                                            placeholder="Kết luận chẩn đoán..."
                                        />
                                    </div>
                                </div>

                                {/* Action buttons */}
                                <div style={{
                                    padding: '12px 16px', borderTop: '1px solid #e5e7eb',
                                    display: 'flex', gap: 10, background: '#fff',
                                }}>
                                    <Button
                                        icon={<SaveOutlined />}
                                        onClick={handleSaveReport}
                                        loading={savingReport}
                                        style={{ flex: 1, height: 40 }}
                                    >
                                        Lưu tạm
                                    </Button>
                                    <Button
                                        type="primary"
                                        icon={<CheckCircleOutlined />}
                                        onClick={handleVerify}
                                        loading={verifying}
                                        style={{
                                            flex: 1, height: 40,
                                            background: '#4f46e5',
                                            border: 'none',
                                            fontWeight: 600,
                                        }}
                                    >
                                        Duyệt (F9)
                                    </Button>
                                </div>
                            </>
                        )}
                    </div>

                </div>
            </div>
        </div>
    );
}
