'use client';

import { useState, useEffect, useCallback } from 'react';
import { Typography, Card, Tag, Space, Row, Col, Statistic, Badge } from 'antd';
import {
    SoundOutlined,
    UserOutlined,
    MedicineBoxOutlined,
    ExperimentOutlined,
    DollarOutlined,
    ClockCircleOutlined,
} from '@ant-design/icons';
import { qmsApi } from '@/lib/services';

const { Title, Text } = Typography;

/**
 * QMS Display Screen - Màn hình gọi số
 * Hiển thị trên màn hình TV/Monitor tại phòng chờ
 */

interface QueueCall {
    id: string;
    queue_number: string;
    patient_name: string;
    service_point: string;
    service_type: 'CLINICAL' | 'LAB' | 'IMAGING' | 'PHARMACY' | 'CASHIER';
    status: 'CALLING' | 'IN_SERVICE' | 'COMPLETED';
    called_at?: string;
}

const serviceConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
    CLINICAL: { icon: <MedicineBoxOutlined />, color: 'blue', label: 'Khám bệnh' },
    LAB: { icon: <ExperimentOutlined />, color: 'purple', label: 'Xét nghiệm' },
    IMAGING: { icon: <MedicineBoxOutlined />, color: 'cyan', label: 'Chẩn đoán HA' },
    PHARMACY: { icon: <MedicineBoxOutlined />, color: 'green', label: 'Nhà thuốc' },
    CASHIER: { icon: <DollarOutlined />, color: 'gold', label: 'Thu ngân' },
};

export default function DisplayScreen() {
    const [currentCalls, setCurrentCalls] = useState<QueueCall[]>([]);
    const [upcomingCalls, setUpcomingCalls] = useState<QueueCall[]>([]);
    const [currentTime, setCurrentTime] = useState(new Date());
    const [stats, setStats] = useState({ total: 0, completed: 0, waiting: 0 });

    // Update time every second
    useEffect(() => {
        const timer = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(timer);
    }, []);

    // Fetch queue data
    const fetchQueueData = useCallback(async () => {
        try {
            const data = await qmsApi.getDisplayQueue();
            setCurrentCalls(data.current_calls || []);
            setUpcomingCalls(data.upcoming || []);
            setStats(data.stats || { total: 0, completed: 0, waiting: 0 });
        } catch (error) {
            console.error('Error fetching queue:', error);
            // Demo data for display
            setCurrentCalls([
                { id: '1', queue_number: 'A-001', patient_name: 'Nguyễn Văn A', service_point: 'Phòng khám 1', service_type: 'CLINICAL', status: 'CALLING' },
                { id: '2', queue_number: 'B-015', patient_name: 'Trần Thị B', service_point: 'Phòng XN 2', service_type: 'LAB', status: 'CALLING' },
                { id: '3', queue_number: 'C-008', patient_name: 'Lê Văn C', service_point: 'Quầy thuốc', service_type: 'PHARMACY', status: 'CALLING' },
            ]);
            setUpcomingCalls([
                { id: '4', queue_number: 'A-002', patient_name: 'Phạm D', service_point: 'Phòng khám 1', service_type: 'CLINICAL', status: 'IN_SERVICE' },
                { id: '5', queue_number: 'A-003', patient_name: 'Hoàng E', service_point: 'Phòng khám 2', service_type: 'CLINICAL', status: 'IN_SERVICE' },
                { id: '6', queue_number: 'D-012', patient_name: 'Vũ F', service_point: 'Thu ngân 1', service_type: 'CASHIER', status: 'IN_SERVICE' },
            ]);
            setStats({ total: 150, completed: 89, waiting: 61 });
        }
    }, []);

    useEffect(() => {
        fetchQueueData();
        const interval = setInterval(fetchQueueData, 5000); // Refresh every 5 seconds
        return () => clearInterval(interval);
    }, [fetchQueueData]);

    // Play sound for new calls
    useEffect(() => {
        if (currentCalls.some(c => c.status === 'CALLING')) {
            // Browser speech synthesis
            if ('speechSynthesis' in window) {
                const call = currentCalls.find(c => c.status === 'CALLING');
                if (call) {
                    const utterance = new SpeechSynthesisUtterance(
                        `Mời số ${call.queue_number.replace('-', ' ')} đến ${call.service_point}`
                    );
                    utterance.lang = 'vi-VN';
                    utterance.rate = 0.9;
                    speechSynthesis.speak(utterance);
                }
            }
        }
    }, [currentCalls]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-900 via-blue-800 to-indigo-900 p-6 text-white">
            {/* Header */}
            <header className="flex items-center justify-between mb-8">
                <div className="flex items-center gap-4">
                    <MedicineBoxOutlined className="text-4xl text-cyan-400" />
                    <div>
                        <Title level={2} className="!text-white !mb-0">Bệnh Viện Đa Khoa ABC</Title>
                        <Text className="text-blue-200">Hệ thống gọi số tự động</Text>
                    </div>
                </div>
                <div className="text-right">
                    <div className="text-4xl font-bold text-cyan-400">
                        {currentTime.toLocaleTimeString('vi-VN')}
                    </div>
                    <div className="text-blue-200">
                        {currentTime.toLocaleDateString('vi-VN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}
                    </div>
                </div>
            </header>

            {/* Stats */}
            <Row gutter={16} className="mb-8">
                <Col span={8}>
                    <Card className="bg-white/10 border-white/20">
                        <Statistic
                            title={<span className="text-blue-200">Tổng số lượt</span>}
                            value={stats.total}
                            valueStyle={{ color: '#fff' }}
                            prefix={<UserOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card className="bg-white/10 border-white/20">
                        <Statistic
                            title={<span className="text-blue-200">Đã hoàn thành</span>}
                            value={stats.completed}
                            valueStyle={{ color: '#52c41a' }}
                            prefix={<ClockCircleOutlined />}
                        />
                    </Card>
                </Col>
                <Col span={8}>
                    <Card className="bg-white/10 border-white/20">
                        <Statistic
                            title={<span className="text-blue-200">Đang chờ</span>}
                            value={stats.waiting}
                            valueStyle={{ color: '#faad14' }}
                            prefix={<ClockCircleOutlined />}
                        />
                    </Card>
                </Col>
            </Row>

            {/* Main Display */}
            <Row gutter={24}>
                {/* Current Calls - Main Focus */}
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
                        <div className="divide-y divide-white/10">
                            {currentCalls.map((call) => (
                                <div
                                    key={call.id}
                                    className="p-6 flex items-center justify-between animate-pulse"
                                >
                                    <div className="flex items-center gap-6">
                                        <div className="text-6xl font-bold text-cyan-400">
                                            {call.queue_number}
                                        </div>
                                        <div>
                                            <div className="text-2xl font-semibold text-white">
                                                {call.patient_name}
                                            </div>
                                            <Tag
                                                icon={serviceConfig[call.service_type]?.icon}
                                                color={serviceConfig[call.service_type]?.color}
                                                className="text-lg mt-2"
                                            >
                                                {serviceConfig[call.service_type]?.label}
                                            </Tag>
                                        </div>
                                    </div>
                                    <div className="text-right">
                                        <Badge status="processing" />
                                        <div className="text-3xl font-bold text-yellow-400">
                                            {call.service_point}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {currentCalls.length === 0 && (
                                <div className="p-12 text-center text-blue-300">
                                    <ClockCircleOutlined className="text-4xl mb-4" />
                                    <div>Không có số đang gọi</div>
                                </div>
                            )}
                        </div>
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
                            {upcomingCalls.map((call, index) => (
                                <div
                                    key={call.id}
                                    className="p-4 flex items-center justify-between"
                                >
                                    <div className="flex items-center gap-4">
                                        <div className="text-2xl font-bold text-blue-300">
                                            {index + 1}.
                                        </div>
                                        <div>
                                            <div className="text-xl font-semibold text-white">
                                                {call.queue_number}
                                            </div>
                                            <Text className="text-blue-200 text-sm">
                                                {call.patient_name}
                                            </Text>
                                        </div>
                                    </div>
                                    <Tag color={serviceConfig[call.service_type]?.color}>
                                        {call.service_point}
                                    </Tag>
                                </div>
                            ))}
                            {upcomingCalls.length === 0 && (
                                <div className="p-8 text-center text-blue-300">
                                    Không có số chờ
                                </div>
                            )}
                        </div>
                    </Card>
                </Col>
            </Row>

            {/* Footer */}
            <footer className="mt-8 text-center text-blue-300">
                <Text>Vui lòng chú ý màn hình và lắng nghe thông báo • Hotline: 1900 1234</Text>
            </footer>
        </div>
    );
}
