'use client';

import { useState, useEffect, useCallback } from 'react';
import { Typography, Card, Tag, Space, Row, Col, Statistic, Badge, Select } from 'antd';
import {
    SoundOutlined,
    UserOutlined,
    MedicineBoxOutlined,
    ClockCircleOutlined,
    ThunderboltOutlined,
    CalendarOutlined,
    TeamOutlined,
} from '@ant-design/icons';
import { qmsApi } from '@/lib/services';
import type {
    ServiceStation,
    CalledPatient,
    QueueBoardEntry,
    QueueSourceType,
} from '@/types';

const { Title, Text } = Typography;

/**
 * QMS Display Screen — Bảng LED Hàng đợi 3 Luồng
 * Hiển thị trên TV/Monitor tại phòng chờ.
 * Tự động refresh từ endpoint GET /qms/queue/board/
 */

const sourceIcon: Record<QueueSourceType, { icon: React.ReactNode; color: string; label: string }> = {
    EMERGENCY: { icon: <ThunderboltOutlined />, color: '#ff4d4f', label: 'CẤP CỨU' },
    ONLINE_BOOKING: { icon: <CalendarOutlined />, color: '#1890ff', label: 'ĐẶT LỊCH' },
    WALK_IN: { icon: <TeamOutlined />, color: '#8c8c8c', label: 'VÃNG LAI' },
};

export default function DisplayScreen() {
    const [stations, setStations] = useState<ServiceStation[]>([]);
    const [selectedStation, setSelectedStation] = useState<string | null>(null);
    const [currentServing, setCurrentServing] = useState<CalledPatient | null>(null);
    const [waitingList, setWaitingList] = useState<QueueBoardEntry[]>([]);
    const [totalWaiting, setTotalWaiting] = useState(0);
    const [currentTime, setCurrentTime] = useState(new Date());

    // Đồng hồ
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    // Fetch stations
    useEffect(() => {
        const load = async () => {
            try {
                const data = await qmsApi.getStations();
                setStations(data);
                if (data.length > 0) setSelectedStation(data[0].id);
            } catch (e) {
                console.error('Lỗi load stations:', e);
            }
        };
        load();
    }, []);

    // Fetch queue board
    const fetchBoard = useCallback(async () => {
        if (!selectedStation) return;
        try {
            const data = await qmsApi.getQueueBoard(selectedStation);
            setCurrentServing(data.current_serving);
            setWaitingList(data.waiting_list);
            setTotalWaiting(data.total_waiting);
        } catch {
            // Fallback demo
            setCurrentServing(null);
            setWaitingList([]);
        }
    }, [selectedStation]);

    useEffect(() => {
        if (selectedStation) {
            fetchBoard();
            const interval = setInterval(fetchBoard, 5000);
            return () => clearInterval(interval);
        }
    }, [selectedStation, fetchBoard]);

    // Speech synthesis khi có bệnh nhân mới được gọi
    useEffect(() => {
        if (currentServing && 'speechSynthesis' in window) {
            const utterance = new SpeechSynthesisUtterance(
                `Mời số ${currentServing.daily_sequence}, ${currentServing.patient_name || ''}, đến ${currentServing.station_name}`
            );
            utterance.lang = 'vi-VN';
            utterance.rate = 0.9;
            speechSynthesis.speak(utterance);
        }
    }, [currentServing?.entry_id]); // eslint-disable-line react-hooks/exhaustive-deps

    const emergencyCount = waitingList.filter(w => w.source_type === 'EMERGENCY').length;
    const bookingCount = waitingList.filter(w => w.source_type === 'ONLINE_BOOKING').length;
    const walkinCount = waitingList.filter(w => w.source_type === 'WALK_IN').length;

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 p-6 text-white">
            {/* Header */}
            <header className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-4">
                    <MedicineBoxOutlined className="text-4xl text-cyan-400" />
                    <div>
                        <Title level={2} className="!text-white !mb-0">Bệnh Viện Đa Khoa ABC</Title>
                        <Text className="text-blue-200">Hàng chờ lâm sàng — 3 Luồng ưu tiên</Text>
                    </div>
                </div>
                <div className="flex items-center gap-6">
                    <Select
                        value={selectedStation}
                        onChange={setSelectedStation}
                        style={{ width: 220 }}
                        dropdownStyle={{ background: '#1e3a5f' }}
                        options={stations.map(s => ({
                            value: s.id,
                            label: `[${s.code}] ${s.name}`,
                        }))}
                    />
                    <div className="text-right">
                        <div className="text-4xl font-bold text-cyan-400">
                            {currentTime.toLocaleTimeString('vi-VN')}
                        </div>
                        <div className="text-blue-200">
                            {currentTime.toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                        </div>
                    </div>
                </div>
            </header>

            {/* Stats */}
            <Row gutter={16} className="mb-6">
                <Col span={6}>
                    <Card className="bg-white/10 border-white/20">
                        <Statistic
                            title={<span className="text-blue-200">Tổng chờ</span>}
                            value={totalWaiting}
                            styles={{ content: { color: '#fff' } }}
                            prefix={<UserOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card className="bg-white/10 border-white/20">
                        <Statistic
                            title={<span className="text-red-300">🚨 Cấp cứu</span>}
                            value={emergencyCount}
                            styles={{ content: { color: emergencyCount > 0 ? '#ff4d4f' : '#8c8c8c' } }}
                            prefix={<ThunderboltOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card className="bg-white/10 border-white/20">
                        <Statistic
                            title={<span className="text-blue-200">📱 Đặt lịch</span>}
                            value={bookingCount}
                            styles={{ content: { color: '#1890ff' } }}
                            prefix={<CalendarOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={6}>
                    <Card className="bg-white/10 border-white/20">
                        <Statistic
                            title={<span className="text-blue-200">🚶 Vãng lai</span>}
                            value={walkinCount}
                            styles={{ content: { color: '#d9d9d9' } }}
                            prefix={<TeamOutlined />}
                        />
                    </Card>
                </Col>
            </Row>

            {/* Main Display */}
            <Row gutter={24}>
                {/* Current Call — Focus Area */}
                <Col span={16}>
                    <Card
                        title={
                            <Space className="text-xl">
                                <SoundOutlined className="text-red-500 animate-pulse" />
                                <span className="text-white">ĐANG GỌI</span>
                            </Space>
                        }
                        className="bg-white/10 border-white/20"
                        styles={{ header: { borderBottom: '1px solid rgba(255,255,255,0.2)' }, body: { padding: 0 } }}
                    >
                        {currentServing ? (
                            <div className="p-8 flex items-center justify-between animate-pulse">
                                <div className="flex items-center gap-8">
                                    <div
                                        className="text-8xl font-bold"
                                        style={{ color: sourceIcon[currentServing.source_type]?.color || '#22d3ee' }}
                                    >
                                        {currentServing.daily_sequence}
                                    </div>
                                    <div>
                                        <div className="text-3xl font-semibold text-white mb-2">
                                            {currentServing.patient_name || 'Bệnh nhân'}
                                        </div>
                                        <Space>
                                            <Tag
                                                icon={sourceIcon[currentServing.source_type]?.icon}
                                                color={currentServing.source_type === 'EMERGENCY' ? 'red'
                                                    : currentServing.source_type === 'ONLINE_BOOKING' ? 'blue'
                                                        : 'default'}
                                                className="text-base"
                                            >
                                                {sourceIcon[currentServing.source_type]?.label}
                                            </Tag>
                                            {currentServing.priority > 0 && (
                                                <Tag color="gold" className="text-base">
                                                    P{currentServing.priority}
                                                </Tag>
                                            )}
                                        </Space>
                                    </div>
                                </div>
                                <div className="text-right">
                                    <Badge status="processing" />
                                    <div className="text-3xl font-bold text-yellow-400">
                                        {currentServing.station_name}
                                    </div>
                                    <div className="text-sm text-blue-300 mt-1">
                                        {currentServing.queue_number}
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <div className="p-14 text-center text-blue-300">
                                <ClockCircleOutlined className="text-5xl mb-4" />
                                <div className="text-xl">Không có số đang gọi</div>
                            </div>
                        )}
                    </Card>
                </Col>

                {/* Upcoming Queue */}
                <Col span={8}>
                    <Card
                        title={<span className="text-white">SẮP ĐƯỢC GỌI</span>}
                        className="bg-white/10 border-white/20 h-full"
                        styles={{ header: { borderBottom: '1px solid rgba(255,255,255,0.2)' }, body: { padding: 0 } }}
                    >
                        <div className="divide-y divide-white/10">
                            {waitingList.slice(0, 8).map((entry) => {
                                const src = sourceIcon[entry.source_type] || sourceIcon.WALK_IN;

                                return (
                                    <div
                                        key={`${entry.queue_number}-${entry.position}`}
                                        className={`p-4 flex items-center justify-between ${entry.source_type === 'EMERGENCY' ? 'bg-red-900/30' : ''
                                            }`}
                                    >
                                        <div className="flex items-center gap-4">
                                            <div className="text-2xl font-bold text-blue-300">
                                                {entry.position}.
                                            </div>
                                            <div>
                                                <div className="text-xl font-semibold text-white">
                                                    {entry.queue_number}
                                                </div>
                                                <Space size={4}>
                                                    <Tag
                                                        icon={src.icon}
                                                        color={entry.source_type === 'EMERGENCY' ? 'red'
                                                            : entry.source_type === 'ONLINE_BOOKING' ? 'blue'
                                                                : 'default'}
                                                        className="text-xs"
                                                    >
                                                        {src.label}
                                                    </Tag>
                                                    {entry.priority > 0 && (
                                                        <Tag color="gold" className="text-xs">P{entry.priority}</Tag>
                                                    )}
                                                </Space>
                                            </div>
                                        </div>
                                        {entry.patient_name && (
                                            <Text className="text-blue-200 text-sm">
                                                {entry.patient_name}
                                            </Text>
                                        )}
                                    </div>
                                );
                            })}
                            {waitingList.length === 0 && (
                                <div className="p-8 text-center text-blue-300">
                                    Hàng đợi trống
                                </div>
                            )}
                            {waitingList.length > 8 && (
                                <div className="p-3 text-center text-blue-300 text-sm">
                                    ... và {waitingList.length - 8} bệnh nhân khác
                                </div>
                            )}
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* Footer */}
            <footer className="mt-8 text-center text-blue-300">
                <Text>
                    Vui lòng chú ý màn hình và lắng nghe thông báo • Hotline: 1900 1234
                </Text>
            </footer>
        </div>
    );
}
