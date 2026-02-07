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
} from 'antd';
import {
    SoundOutlined,
    CheckOutlined,
    ForwardOutlined,
    ReloadOutlined,
    UserOutlined,
    ClockCircleOutlined,
} from '@ant-design/icons';
import { qmsApi } from '@/lib/services';
import type { QueueNumber, ServiceStation } from '@/types';

const { Title, Text } = Typography;

/**
 * QMS Page
 * Hệ thống quản lý hàng đợi (Queue Management System)
 */

// Extend types locally for QMS-specific fields
interface QueueEntry {
    id: string;
    queue_number: QueueNumber;
    station: ServiceStation;
    status: string;
    priority: number;
    entered_queue_time: string;
    called_time?: string;
}

const statusConfig: Record<string, { color: string; label: string }> = {
    WAITING: { color: 'gold', label: 'Đang chờ' },
    CALLED: { color: 'blue', label: 'Đã gọi' },
    IN_PROGRESS: { color: 'processing', label: 'Đang phục vụ' },
    COMPLETED: { color: 'success', label: 'Hoàn thành' },
    SKIPPED: { color: 'default', label: 'Bỏ qua' },
    NO_SHOW: { color: 'error', label: 'Không có mặt' },
};

export default function QMSPage() {
    const [stations, setStations] = useState<ServiceStation[]>([]);
    const [selectedStation, setSelectedStation] = useState<string | null>(null);
    const [waitingQueue, setWaitingQueue] = useState<QueueNumber[]>([]);
    const [currentServing, setCurrentServing] = useState<QueueNumber | null>(null);
    const [loading, setLoading] = useState(false);

    // Fetch stations
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

    // Fetch queue for selected station
    const fetchQueue = useCallback(async () => {
        if (!selectedStation) return;

        setLoading(true);
        try {
            const data = await qmsApi.getWaiting(selectedStation);
            // Separate current serving from waiting
            const waiting = data.filter((q) => q.status === 'WAITING');
            const serving = data.find((q) => q.status === 'CALLED' || q.status === 'IN_PROGRESS');

            setWaitingQueue(waiting);
            setCurrentServing(serving || null);
        } catch (error) {
            console.error('Error fetching queue:', error);
        } finally {
            setLoading(false);
        }
    }, [selectedStation]);

    useEffect(() => {
        fetchStations();
    }, [fetchStations]);

    useEffect(() => {
        if (selectedStation) {
            fetchQueue();
        }
    }, [selectedStation, fetchQueue]);

    // Call next number
    const handleCallNext = async () => {
        if (!selectedStation) return;

        try {
            const result = await qmsApi.callNext(selectedStation);
            if (result) {
                message.success(`Đã gọi số: ${result.number_code}`);
                // TODO: Play sound notification
                fetchQueue();
            } else {
                message.info('Không còn bệnh nhân trong hàng đợi');
            }
        } catch (error) {
            console.error('Error calling next:', error);
            message.error('Không thể gọi số tiếp theo');
        }
    };

    // Complete current
    const handleComplete = async () => {
        if (!currentServing) return;

        try {
            await qmsApi.completeQueue(currentServing.id);
            message.success('Đã hoàn thành phục vụ');
            fetchQueue();
        } catch (error) {
            console.error('Error completing:', error);
            message.error('Không thể cập nhật trạng thái');
        }
    };

    // Skip current
    const handleSkip = async () => {
        if (!currentServing) return;

        try {
            await qmsApi.skipQueue(currentServing.id);
            message.warning('Đã bỏ qua số hiện tại');
            fetchQueue();
        } catch (error) {
            console.error('Error skipping:', error);
            message.error('Không thể bỏ qua');
        }
    };

    const currentStation = stations.find((s) => s.id === selectedStation);

    return (
        <div className="space-y-4">
            {/* Page Header */}
            <div className="flex justify-between items-center">
                <div>
                    <Title level={3} className="!mb-0">Quản lý Hàng đợi (QMS)</Title>
                    <Text type="secondary">Gọi số và quản lý bệnh nhân tại các điểm dịch vụ</Text>
                </div>
                <Space>
                    <Select
                        placeholder="Chọn điểm dịch vụ"
                        value={selectedStation}
                        onChange={setSelectedStation}
                        style={{ width: 250 }}
                        options={stations.map((s) => ({
                            value: s.id,
                            label: `[${s.code}] ${s.name}`,
                        }))}
                    />
                    <Button icon={<ReloadOutlined />} onClick={fetchQueue}>
                        Làm mới
                    </Button>
                </Space>
            </div>

            <div className="grid grid-cols-3 gap-4">
                {/* Current Serving */}
                <Card
                    title={
                        <Space>
                            <SoundOutlined className="text-blue-500" />
                            <span>Đang phục vụ</span>
                        </Space>
                    }
                    className="col-span-1"
                >
                    {currentServing ? (
                        <div className="text-center py-4">
                            <div className="text-6xl font-bold text-blue-600 mb-4">
                                {currentServing.daily_sequence || '---'}
                            </div>
                            <Tag color="blue" className="text-lg px-4 py-1 mb-4">
                                {currentServing.number_code}
                            </Tag>
                            <div className="flex justify-center gap-2 mt-4">
                                <Button
                                    type="primary"
                                    icon={<CheckOutlined />}
                                    onClick={handleComplete}
                                >
                                    Hoàn thành
                                </Button>
                                <Button
                                    danger
                                    icon={<ForwardOutlined />}
                                    onClick={handleSkip}
                                >
                                    Bỏ qua
                                </Button>
                            </div>
                        </div>
                    ) : (
                        <div className="text-center py-8">
                            <Empty
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                                description="Không có bệnh nhân đang phục vụ"
                            />
                            <Button
                                type="primary"
                                size="large"
                                icon={<SoundOutlined />}
                                onClick={handleCallNext}
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
                            <span>Hàng đợi ({waitingQueue.length})</span>
                        </Space>
                    }
                    className="col-span-2"
                    extra={
                        <Button
                            type="primary"
                            icon={<SoundOutlined />}
                            onClick={handleCallNext}
                            disabled={waitingQueue.length === 0}
                        >
                            Gọi tiếp
                        </Button>
                    }
                >
                    <Spin spinning={loading}>
                        {waitingQueue.length > 0 ? (
                            <List
                                dataSource={waitingQueue}
                                renderItem={(item, index) => (
                                    <List.Item>
                                        <List.Item.Meta
                                            avatar={
                                                <Badge count={index + 1} style={{ backgroundColor: index === 0 ? '#1E88E5' : '#8c8c8c' }}>
                                                    <Avatar icon={<UserOutlined />} />
                                                </Badge>
                                            }
                                            title={
                                                <Space>
                                                    <Text strong>
                                                        {item.number_code}
                                                    </Text>
                                                    {item.priority > 0 && (
                                                        <Tag color="red">Ưu tiên</Tag>
                                                    )}
                                                </Space>
                                            }
                                            description={
                                                <Text type="secondary">
                                                    Chờ từ: {new Date(item.created_time).toLocaleTimeString('vi-VN')}
                                                </Text>
                                            }
                                        />
                                        <Tag color={statusConfig[item.status]?.color || 'default'}>
                                            {statusConfig[item.status]?.label || item.status}
                                        </Tag>
                                    </List.Item>
                                )}
                            />
                        ) : (
                            <Empty
                                image={Empty.PRESENTED_IMAGE_SIMPLE}
                                description="Không có bệnh nhân trong hàng đợi"
                            />
                        )}
                    </Spin>
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
        </div>
    );
}
