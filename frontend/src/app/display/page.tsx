'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { qmsApi } from '@/lib/services';
import type {
    CalledPatient,
    QueueBoardEntry,
    NoShowEntry,
} from '@/types';

const sourceColors: Record<string, string> = {
    EMERGENCY: '#ff4d4f',
    ONLINE_BOOKING: '#1890ff',
    WALK_IN: '#8c8c8c',
};

// Derive WS base URL from API URL
function getWsUrl(stationId: string): string {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
    const base = apiUrl.replace(/\/api\/v1\/?$/, '').replace(/^http/, 'ws');
    return `${base}/ws/qms/display/${stationId}/`;
}

export default function PublicDisplayPage() {
    const [pairingCode, setPairingCode] = useState<string | null>(null);
    const [stationId, setStationId] = useState<string | null>(null);
    const [stationName, setStationName] = useState<string>('');
    const [currentlyServing, setCurrentlyServing] = useState<CalledPatient[]>([]);
    const [waitingList, setWaitingList] = useState<QueueBoardEntry[]>([]);
    const [noShowList, setNoShowList] = useState<NoShowEntry[]>([]);
    const [wsConnected, setWsConnected] = useState(false);
    const [clock, setClock] = useState('');
    const wsRef = useRef<WebSocket | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    // Clock
    useEffect(() => {
        const tick = () => setClock(new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
        tick();
        const interval = setInterval(tick, 1000);
        return () => clearInterval(interval);
    }, []);

    // Step 1: Register and get pairing code
    useEffect(() => {
        const register = async () => {
            try {
                const { code } = await qmsApi.registerDisplay();
                setPairingCode(code);
            } catch (e) {
                console.error('Failed to register display:', e);
            }
        };
        register();
    }, []);

    // Step 2: Poll for pairing (only until paired)
    useEffect(() => {
        if (!pairingCode || stationId) return;

        const poll = async () => {
            try {
                const result = await qmsApi.checkDisplay(pairingCode);
                if (result.paired && result.station_id) {
                    setStationId(result.station_id);
                    setStationName(result.station_name || '');
                }
            } catch {
                // silent
            }
        };

        pollRef.current = setInterval(poll, 3000);
        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
        };
    }, [pairingCode, stationId]);

    // Apply board data from WebSocket message
    const applyBoardData = useCallback((data: Record<string, unknown>) => {
        setCurrentlyServing((data.currently_serving as CalledPatient[]) || []);
        setWaitingList((data.waiting_list as QueueBoardEntry[]) || []);
        setNoShowList((data.no_show_list as NoShowEntry[]) || []);
    }, []);

    // Step 3: Connect WebSocket once paired
    useEffect(() => {
        if (!stationId) return;

        let alive = true;

        const connect = () => {
            if (!alive) return;
            const url = getWsUrl(stationId);
            console.log('[WS] Connecting to', url);
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                console.log('[WS] Connected');
                setWsConnected(true);
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'queue_update' && msg.data) {
                        applyBoardData(msg.data);
                    }
                } catch {
                    // ignore parse errors
                }
            };

            ws.onclose = (e) => {
                console.log('[WS] Disconnected', e.code);
                setWsConnected(false);
                wsRef.current = null;
                // Auto-reconnect after 3s
                if (alive) {
                    reconnectTimeoutRef.current = setTimeout(connect, 3000);
                }
            };

            ws.onerror = () => {
                console.error('[WS] Error — will reconnect');
                ws.close();
            };
        };

        connect();

        // Ping keepalive every 30s
        const pingInterval = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);

        return () => {
            alive = false;
            clearInterval(pingInterval);
            if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
            if (wsRef.current) {
                wsRef.current.onclose = null; // prevent reconnect on intentional close
                wsRef.current.close();
            }
        };
    }, [stationId, applyBoardData]);

    const nextUp = waitingList.slice(0, 8);

    // ── PAIRING SCREEN ──────────────────────────────────────
    if (!stationId) {
        return (
            <div className="min-h-screen bg-gray-950 flex items-center justify-center">
                <div className="text-center">
                    <div className="text-6xl mb-6">🏥</div>
                    <h1 className="text-4xl font-bold text-white mb-4">Bảng Gọi Số</h1>
                    <p className="text-gray-400 text-lg mb-8">
                        Nhập mã dưới đây tại quầy Tiếp nhận để liên kết màn hình
                    </p>

                    {pairingCode ? (
                        <div className="bg-gray-900 rounded-2xl p-8 inline-block">
                            <p className="text-gray-500 text-sm mb-3 uppercase tracking-widest">
                                Mã liên kết
                            </p>
                            <div className="text-7xl font-mono font-black text-blue-400 tracking-[0.3em] select-all">
                                {pairingCode}
                            </div>
                            <p className="text-gray-600 text-sm mt-4 animate-pulse">
                                Đang chờ liên kết...
                            </p>
                        </div>
                    ) : (
                        <div className="text-gray-500 text-xl animate-pulse">
                            Đang tạo mã...
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // ── QUEUE DISPLAY ────────────────────────────────────────
    return (
        <div className="min-h-screen bg-gray-950 text-white p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <h2 className="text-3xl font-bold text-white mb-0">
                        🏥 Bảng Gọi Số
                    </h2>
                    <p className="text-gray-400 text-lg">
                        {stationName}
                    </p>
                </div>
                <div className="flex items-center gap-4">
                    <div className={`w-3 h-3 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-red-500'}`}
                        title={wsConnected ? 'WebSocket connected' : 'Reconnecting...'} />
                    <div className="text-gray-500 text-3xl font-mono">
                        {clock}
                    </div>
                </div>
            </div>

            {/* 3-Column Grid */}
            <div className="grid grid-cols-3 gap-6" style={{ height: 'calc(100vh - 140px)' }}>

                {/* ── Column 1: Đang gọi ── */}
                <div className="bg-gray-900 rounded-2xl p-5 flex flex-col">
                    <div className="flex items-center gap-2 mb-4">
                        <span className="text-2xl">🔔</span>
                        <span className="text-xl font-bold text-blue-400">ĐANG GỌI</span>
                    </div>
                    <div className="flex-1 flex flex-col gap-4 justify-center">
                        {currentlyServing.length > 0 ? (
                            currentlyServing.map((p) => (
                                <div
                                    key={p.entry_id}
                                    className="border-2 rounded-xl p-6 text-center"
                                    style={{
                                        borderColor: sourceColors[p.source_type] || '#1890ff',
                                        backgroundColor: `${sourceColors[p.source_type] || '#1890ff'}15`,
                                        animation: 'pulse-slow 2s ease-in-out infinite',
                                    }}
                                >
                                    <div
                                        className="text-8xl font-black mb-2"
                                        style={{ color: sourceColors[p.source_type] || '#1890ff' }}
                                    >
                                        {p.daily_sequence}
                                    </div>
                                    <div className="text-lg text-gray-300 mb-1">
                                        {p.queue_number}
                                    </div>
                                    <div className="text-xl font-semibold text-white">
                                        {p.patient_name || 'Bệnh nhân'}
                                    </div>
                                    {p.source_type === 'EMERGENCY' && (
                                        <div className="mt-2 text-red-400 font-bold text-lg" style={{ animation: 'pulse 1s infinite' }}>
                                            🚨 CẤP CỨU
                                        </div>
                                    )}
                                </div>
                            ))
                        ) : (
                            <div className="text-center text-gray-600 text-xl">
                                — Trống —
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Column 2: Tiếp theo ── */}
                <div className="bg-gray-900 rounded-2xl p-5 flex flex-col">
                    <div className="flex items-center gap-2 mb-4">
                        <span className="text-2xl">⏳</span>
                        <span className="text-xl font-bold text-yellow-400">TIẾP THEO</span>
                        <span className="text-gray-500 text-sm ml-auto">
                            {waitingList.length} đang chờ
                        </span>
                    </div>
                    <div className="flex-1 overflow-auto space-y-2">
                        {nextUp.length > 0 ? (
                            nextUp.map((entry) => (
                                <div
                                    key={entry.entry_id}
                                    className="flex items-center gap-4 bg-gray-800 rounded-lg px-4 py-3"
                                >
                                    <div
                                        className="text-3xl font-bold w-16 text-center"
                                        style={{ color: sourceColors[entry.source_type] || '#fff' }}
                                    >
                                        {entry.daily_sequence}
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-sm text-gray-400">
                                            {entry.queue_number}
                                        </div>
                                        <div className="text-base text-white">
                                            {entry.patient_name || 'BN'}
                                        </div>
                                    </div>
                                    {entry.priority > 0 && (
                                        <div className="text-xs px-2 py-0.5 rounded bg-orange-900 text-orange-300">
                                            P{entry.priority}
                                        </div>
                                    )}
                                </div>
                            ))
                        ) : (
                            <div className="text-center text-gray-600 text-lg mt-10">
                                Hàng đợi trống
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Column 3: Vắng mặt ── */}
                <div className="bg-gray-900 rounded-2xl p-5 flex flex-col">
                    <div className="flex items-center gap-2 mb-4">
                        <span className="text-2xl">⚠️</span>
                        <span className="text-xl font-bold text-red-400">VẮNG MẶT</span>
                        <span className="text-gray-500 text-sm ml-auto">
                            {noShowList.length} số
                        </span>
                    </div>
                    <div className="flex-1 overflow-auto space-y-2">
                        {noShowList.length > 0 ? (
                            noShowList.map((entry) => (
                                <div
                                    key={entry.entry_id}
                                    className="flex items-center gap-3 bg-gray-800 rounded-lg px-4 py-3 border-l-4 border-red-500"
                                >
                                    <div className="text-3xl font-bold w-14 text-center text-red-400">
                                        {entry.daily_sequence}
                                    </div>
                                    <div className="flex-1">
                                        <div className="text-sm text-gray-400">
                                            {entry.queue_number}
                                        </div>
                                        <div className="text-base text-white">
                                            {entry.patient_name || 'BN'}
                                        </div>
                                    </div>
                                    {entry.end_time && (
                                        <div className="text-xs text-gray-500">
                                            {entry.end_time}
                                        </div>
                                    )}
                                </div>
                            ))
                        ) : (
                            <div className="text-center text-gray-600 text-lg mt-10">
                                Không có
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Animation styles */}
            <style jsx>{`
                @keyframes pulse-slow {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.85; }
                }
                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }
            `}</style>
        </div>
    );
}
