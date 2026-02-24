'use client';

import { useState, useEffect, useCallback } from 'react';
import { Select, Typography } from 'antd';
import {
    SoundOutlined,
    ClockCircleOutlined,
    CheckCircleOutlined,
    EyeInvisibleOutlined,
} from '@ant-design/icons';
import { qmsApi } from '@/lib/services';
import type {
    ServiceStation,
    CalledPatient,
    QueueBoardEntry,
    QueueCompletedEntry,
} from '@/types';

const { Title, Text } = Typography;

const sourceColors: Record<string, string> = {
    EMERGENCY: '#ff4d4f',
    ONLINE_BOOKING: '#1890ff',
    WALK_IN: '#8c8c8c',
};

const statusLabels: Record<string, { label: string; color: string }> = {
    COMPLETED: { label: 'Hoàn thành', color: '#52c41a' },
    SKIPPED: { label: 'Bỏ qua', color: '#faad14' },
    NO_SHOW: { label: 'Vắng mặt', color: '#ff4d4f' },
};

export default function QMSDisplayPage() {
    const [stations, setStations] = useState<ServiceStation[]>([]);
    const [selectedStation, setSelectedStation] = useState<string | null>(null);
    const [currentlyServing, setCurrentlyServing] = useState<CalledPatient[]>([]);
    const [waitingList, setWaitingList] = useState<QueueBoardEntry[]>([]);
    const [completedList, setCompletedList] = useState<QueueCompletedEntry[]>([]);

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

    const fetchBoard = useCallback(async () => {
        if (!selectedStation) return;
        try {
            const data = await qmsApi.getQueueBoard(selectedStation);
            setCurrentlyServing(data.currently_serving || []);
            setWaitingList(data.waiting_list || []);
            setCompletedList(data.completed_list || []);
        } catch {
            // silent
        }
    }, [selectedStation]);

    useEffect(() => {
        fetchStations();
    }, [fetchStations]);

    useEffect(() => {
        if (selectedStation) {
            fetchBoard();
            const interval = setInterval(fetchBoard, 5000);
            return () => clearInterval(interval);
        }
    }, [selectedStation, fetchBoard]);

    const currentStation = stations.find((s) => s.id === selectedStation);
    const nextUp = waitingList.slice(0, 8);

    return (
        <div className="min-h-screen bg-gray-950 text-white p-6">
            {/* Header */}
            <div className="flex justify-between items-center mb-6">
                <div>
                    <Title level={2} className="!text-white !mb-0">
                        🏥 Bảng Gọi Số
                    </Title>
                    {currentStation && (
                        <Text className="text-gray-400 text-lg">
                            {currentStation.name} — [{currentStation.code}]
                        </Text>
                    )}
                </div>
                <Select
                    value={selectedStation}
                    onChange={setSelectedStation}
                    style={{ width: 260 }}
                    options={stations.map((s) => ({
                        value: s.id,
                        label: `[${s.code}] ${s.name}`,
                    }))}
                />
            </div>

            {/* 3-Column Grid */}
            <div className="grid grid-cols-3 gap-6" style={{ height: 'calc(100vh - 140px)' }}>

                {/* ── Column 1: Đang gọi ── */}
                <div className="bg-gray-900 rounded-2xl p-5 flex flex-col">
                    <div className="flex items-center gap-2 mb-4">
                        <SoundOutlined className="text-2xl text-blue-400" />
                        <span className="text-xl font-bold text-blue-400">ĐANG GỌI</span>
                    </div>
                    <div className="flex-1 flex flex-col gap-4 justify-center">
                        {currentlyServing.length > 0 ? (
                            currentlyServing.map((p) => (
                                <div
                                    key={p.entry_id}
                                    className="border-2 rounded-xl p-6 text-center animate-pulse-slow"
                                    style={{
                                        borderColor: sourceColors[p.source_type] || '#1890ff',
                                        backgroundColor: `${sourceColors[p.source_type] || '#1890ff'}15`,
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
                                        <div className="mt-2 text-red-400 font-bold text-lg animate-pulse">
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
                        <ClockCircleOutlined className="text-2xl text-yellow-400" />
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

                {/* ── Column 3: Đã qua ── */}
                <div className="bg-gray-900 rounded-2xl p-5 flex flex-col">
                    <div className="flex items-center gap-2 mb-4">
                        <CheckCircleOutlined className="text-2xl text-green-400" />
                        <span className="text-xl font-bold text-green-400">ĐÃ QUA</span>
                    </div>
                    <div className="flex-1 overflow-auto space-y-2">
                        {completedList.length > 0 ? (
                            completedList.map((entry) => {
                                const st = statusLabels[entry.status] || { label: entry.status, color: '#ccc' };
                                return (
                                    <div
                                        key={entry.entry_id}
                                        className="flex items-center gap-3 bg-gray-800 rounded-lg px-4 py-2 opacity-70"
                                    >
                                        <div className="text-2xl font-bold w-12 text-center text-gray-500">
                                            {entry.daily_sequence}
                                        </div>
                                        <div className="flex-1">
                                            <div className="text-xs text-gray-500">
                                                {entry.queue_number}
                                            </div>
                                            <div className="text-sm text-gray-400">
                                                {entry.patient_name}
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-1 text-xs" style={{ color: st.color }}>
                                            {entry.status === 'NO_SHOW' && <EyeInvisibleOutlined />}
                                            {st.label}
                                        </div>
                                        {entry.end_time && (
                                            <div className="text-xs text-gray-600">
                                                {entry.end_time}
                                            </div>
                                        )}
                                    </div>
                                );
                            })
                        ) : (
                            <div className="text-center text-gray-600 text-lg mt-10">
                                Chưa có
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Subtle animation */}
            <style jsx>{`
                @keyframes pulse-slow {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.85; }
                }
                .animate-pulse-slow {
                    animation: pulse-slow 2s ease-in-out infinite;
                }
            `}</style>
        </div>
    );
}
