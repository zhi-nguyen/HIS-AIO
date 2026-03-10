'use client';

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
    Card,
    Table,
    Button,
    Space,
    Typography,
    Badge,
    Input,
    message,
    Tabs,
    Divider,
    Row,
    Col,
    Modal,
    Tooltip,
    Tag
} from 'antd';
import {
    HistoryOutlined,
    PrinterOutlined,
    SaveOutlined,
    CheckOutlined,
    SoundOutlined,
} from '@ant-design/icons';
import { lisApi } from '@/lib/services';
import type { ColumnsType } from 'antd/es/table';
import { toast } from 'sonner';
import dayjs from 'dayjs';

const SOUND_KEY = 'his_lis_sound';

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

// Prevent duplicate WS toasts across hot-reloads
const globalHandledOrderIds = new Set<string>();

const { Title, Text } = Typography;

interface LabTest {
    id: string;
    code: string;
    name: string;
    unit: string;
    min_limit: number | null;
    max_limit: number | null;
    panic_low: number | null;
    panic_high: number | null;
}

interface LabResult {
    id: string;
    value_string: string;
    value_numeric: number | null;
    is_abnormal: boolean;
    is_critical: boolean;
    abnormal_flag: string | null;
    machine_name: string | null;
    result_time: string;
}

interface LabOrderDetail {
    id: string;
    test_name: string;
    test: LabTest;
    result: LabResult | null;
    service_name?: string;
}

interface LabOrder {
    id: string;
    visit: string;
    visit_code: string;
    patient_code: string;
    patient_name: string | null;
    details: LabOrderDetail[];
    status: string;
    priority: string;
    created_at: string;
    order_time: string;
    doctor?: string;
    note?: string;
}

export default function LISPage() {
    const [orders, setOrders] = useState<LabOrder[]>([]);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('ROUTINE');
    const [selectedOrder, setSelectedOrder] = useState<LabOrder | null>(null);
    const [selectedServiceGroup, setSelectedServiceGroup] = useState<string | null>(null);
    const [inputValues, setInputValues] = useState<Record<string, string>>({});

    // Khởi tạo refs mảng 2 chiều cho inputs để focus/nhảy bằng Enter
    const inputRefs = useRef<(HTMLInputElement | null)[]>([]);

    const [soundEnabled, setSoundEnabled] = useState(true);
    const soundEnabledRef = useRef(true);

    useEffect(() => {
        setSoundEnabled(getSoundEnabled());
    }, []);

    useEffect(() => {
        soundEnabledRef.current = soundEnabled;
    }, [soundEnabled]);

    const toggleSound = useCallback(() => {
        setSoundEnabled((prev) => {
            const next = !prev;
            localStorage.setItem(SOUND_KEY, next ? 'on' : 'off');
            if (next) playNotificationSound();
            return next;
        });
    }, []);

    const fetchOrders = useCallback(async () => {
        setLoading(true);
        try {
            // Fetch directly from LIS API
            // Filter locally based on tab, or pass status if requested
            const response = await lisApi.getOrders();
            setOrders(response.results || response);
        } catch (error) {
            console.error('Error fetching lab orders:', error);
            message.error('Không thể tải dữ liệu LIS');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchOrders();
    }, [fetchOrders]);

    // selectedOrderRef: tránh stale closure trong WebSocket onmessage
    const selectedOrderRef = useRef<LabOrder | null>(null);
    useEffect(() => {
        selectedOrderRef.current = selectedOrder;
    }, [selectedOrder]);

    // WebSocket cho Real-time UI
    // isMounted guard: chống React StrictMode double-mount và stray reconnect sau unmount
    useEffect(() => {
        let ws: WebSocket;
        let reconnectTimeout: NodeJS.Timeout;
        let isMounted = true;

        const connectWs = () => {
            if (!isMounted) return;

            const host = window.location.hostname;
            const wsUrl = `ws://${host}:8000`;
            ws = new WebSocket(`${wsUrl}/ws/lis/updates/`);

            ws.onopen = () => {
                console.log("WebSocket LIS connected");
            };

            ws.onmessage = async (event) => {
                if (!isMounted) return;
                try {
                    const data = JSON.parse(event.data);
                    if (data.type !== 'lis_order_updated') return;

                    const { order_id, action } = data;

                    if (action === 'created') {
                        try {
                            const newOrder = await lisApi.getOrderById(order_id);

                            if (!globalHandledOrderIds.has(order_id)) {
                                globalHandledOrderIds.add(order_id);
                                const patientName = newOrder.patient_name || 'Bệnh nhân';
                                toast.success(`Chỉ định xét nghiệm mới`, {
                                    description: `${patientName} - SID: ${newOrder.id.slice(0, 6).toUpperCase()}`,
                                });

                                if (soundEnabledRef.current) {
                                    playNotificationSound();
                                }
                            }

                            setOrders(prev => {
                                const exists = prev.some(o => o.id === order_id);
                                if (!exists) return [newOrder, ...prev];
                                return prev.map(o => o.id === order_id ? newOrder : o);
                            });
                        } catch (err) {
                            // Fallback if detail fetch fails
                            setTimeout(fetchOrders, 500);
                        }
                        return;
                    }

                    // Order đã tồn tại: fetch full detail để lấy cả results mới
                    try {
                        const updatedOrder = await lisApi.getOrderById(order_id);

                        // Cập nhật worklist
                        setOrders(prev => {
                            const exists = prev.some(o => o.id === order_id);
                            if (!exists) {
                                // Order chưa có trong list (filter tab khác?) → append
                                return [updatedOrder, ...prev];
                            }
                            return prev.map(o => o.id === order_id ? updatedOrder : o);
                        });

                        // Thông báo khi có thay đổi (chỉ định thêm dịch vụ mới vào phiếu cũ)
                        toast.info(`Phiếu xét nghiệm được cập nhật`, {
                            description: `${updatedOrder.patient_name || 'Bệnh nhân'} - SID: ${updatedOrder.id.slice(0, 6).toUpperCase()}`,
                        });
                        if (soundEnabledRef.current) {
                            playNotificationSound();
                        }

                        // Nếu đang xem order này → cập nhật selectedOrder và inputValues
                        if (selectedOrderRef.current?.id === order_id) {
                            setSelectedOrder(updatedOrder);
                            // Cập nhật inputValues từ results mới (nếu có)
                            const vals: Record<string, string> = {};
                            if (updatedOrder.details) {
                                updatedOrder.details.forEach((d: { id: string; result?: { value_string: string } }) => {
                                    if (d.result) {
                                        vals[d.id] = d.result.value_string;
                                    }
                                });
                            }
                            if (Object.keys(vals).length > 0) {
                                setInputValues(vals);
                            }
                        }
                    } catch {
                        // Nếu không fetch được (order bị xóa?), refresh toàn bộ
                        fetchOrders();
                    }
                } catch (err) {
                    console.error("WS Parse error", err);
                }
            };

            ws.onclose = (e) => {
                if (!isMounted) return;
                console.log(`WebSocket LIS closed (code=${e.code}). Reconnecting in 3s...`);
                reconnectTimeout = setTimeout(connectWs, 3000);
            };

            ws.onerror = () => {
                console.error("WebSocket LIS error");
            };
        };

        connectWs();

        return () => {
            isMounted = false;
            clearTimeout(reconnectTimeout);
            if (ws && ws.readyState !== WebSocket.CLOSED) {
                ws.close(1000, "Component unmounted");
            }
        };
    }, [fetchOrders]);


    const filteredOrders = orders.filter(o => {
        if (o.status === 'VERIFIED' || o.status === 'CANCELLED') return false; // Ẩn hoàn toàn đã duyệt & hủy
        if (activeTab === 'STAT') return o.priority === 'STAT' || o.priority === 'URGENT';
        // ROUTINE shows ALL orders except VERIFIED/CANCELLED (which are already removed above)
        if (activeTab === 'ROUTINE') return true;
        return true;
    });

    const statCount = orders.filter(o => (o.priority === 'STAT' || o.priority === 'URGENT') && o.status !== 'VERIFIED' && o.status !== 'CANCELLED').length;
    // ROUTINE count is all unverified orders
    const routineCount = orders.filter(o => o.status !== 'VERIFIED' && o.status !== 'CANCELLED').length;

    const handleSelectOrder = (order: LabOrder) => {
        setSelectedOrder(order);

        // Cập nhật inputValues từ kết quả đã có (nếu có)
        const vals: Record<string, string> = {};
        if (order.details) {
            order.details.forEach(d => {
                if (d.result) {
                    vals[d.id] = d.result.value_string;
                }
            });
        }
        setInputValues(vals);
    };

    const handleInputChange = (detailId: string, val: string) => {
        setInputValues(prev => ({ ...prev, [detailId]: val }));
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, index: number) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            // Focus on next input
            const nextInput = inputRefs.current[index + 1];
            if (nextInput) {
                nextInput.focus();
            }
        }
    };

    // F9 handler
    const handleVerify = async () => {
        if (!selectedOrder) return;

        // Kiểm tra có giá trị nào được nhập không
        const hasAnyValue = selectedOrder.details.some(d => inputValues[d.id]?.trim());
        if (!hasAnyValue) {
            message.warning('Vui lòng nhập ít nhất một kết quả trước khi duyệt.');
            return;
        }

        try {
            // Bước 1: Tự động lưu kết quả hiện tại trước khi duyệt
            const resultsPayload = selectedOrder.details
                .filter(d => inputValues[d.id]?.trim())
                .map(d => ({
                    detail_id: d.id,
                    value_string: inputValues[d.id] || '',
                    value_numeric: isNaN(parseFloat(inputValues[d.id]))
                        ? undefined
                        : parseFloat(inputValues[d.id])
                }));

            await lisApi.enterResults(selectedOrder.id, resultsPayload);

            // Bước 2: Duyệt kết quả
            await lisApi.verifyOrder(selectedOrder.id);
            message.success('Đã duyệt kết quả thành công!');
            fetchOrders();
            setSelectedOrder(null);
        } catch (error: unknown) {
            console.error('Verify error:', error);
            const errMsg = (error as { response?: { data?: { detail?: string } } })
                ?.response?.data?.detail || 'Lỗi khi duyệt kết quả';
            message.error(errMsg);
        }
    };

    const handleSaveTemp = async () => {
        if (!selectedOrder) return;

        const resultsPayload = selectedOrder.details
            .filter(d => inputValues[d.id] && inputValues[d.id].trim() !== '')
            .map(d => ({
                detail_id: d.id,
                value_string: inputValues[d.id] || '',
                value_numeric: isNaN(parseFloat(inputValues[d.id]))
                    ? undefined
                    : parseFloat(inputValues[d.id])
            }));

        try {
            await lisApi.enterResults(selectedOrder.id, resultsPayload);
            message.success('Lưu tạm thành công');
            fetchOrders();
        } catch (err) {
            console.error('Save err', err);
            message.error('Lưu kết quả thất bại');
        }
    };

    // F9 shortcut: Duyệt kết quả
    useEffect(() => {
        const handleGlobalKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'F9') {
                e.preventDefault();
                handleVerify();
            }
        };
        window.addEventListener('keydown', handleGlobalKeyDown);
        return () => window.removeEventListener('keydown', handleGlobalKeyDown);
    }, [selectedOrder, inputValues]); // Re-bind khi order hoặc input values thay đổi

    const columns: ColumnsType<LabOrderDetail> = [
        {
            title: 'THÔNG SỐ (PARAMETER)',
            key: 'name',
            render: (_, record) => (
                <Space direction="vertical" size={2}>
                    <Text strong>{record.test?.name}</Text>
                    <Text type="secondary" className="text-xs">{record.test?.code}</Text>
                </Space>
            )
        },
        {
            title: 'KẾT QUẢ',
            key: 'result',
            width: 150,
            render: (_, record, index) => {
                // Determine if abnormal locally based on input value for preview
                const val = parseFloat(inputValues[record.id] || '');
                let isAbnormal = false;
                if (!isNaN(val) && record.test) {
                    if (record.test.min_limit !== null && val < record.test.min_limit) isAbnormal = true;
                    if (record.test.max_limit !== null && val > record.test.max_limit) isAbnormal = true;
                }

                return (
                    <Input
                        value={inputValues[record.id] || ''}
                        onChange={(e) => {
                            if (record.id) {
                                handleInputChange(record.id, e.target.value)
                            }
                        }}
                        onKeyDown={(e) => handleKeyDown(e, index)}
                        ref={(el) => {
                            inputRefs.current[index] = el?.input || null;
                        }}
                        style={{ color: isAbnormal ? 'var(--ant-color-error)' : 'inherit' }}
                    />
                );
            }
        },
        {
            title: 'CỜ (FLAG)',
            key: 'flag',
            width: 100,
            render: (_, record) => {
                if (!record.test) return '-';
                const val = parseFloat(inputValues[record.id] || '');
                if (isNaN(val)) return '-';
                if (record.test.min_limit !== null && val < record.test.min_limit) {
                    return <Text type="danger">↓ Thấp</Text>;
                }
                if (record.test.max_limit !== null && val > record.test.max_limit) {
                    return <Text type="danger">↑ Cao</Text>;
                }
                return '-';
            }
        },
        {
            title: 'ĐƠN VỊ',
            key: 'unit',
            dataIndex: ['test', 'unit'],
            width: 100,
        },
        {
            title: 'KHOẢNG THAM CHIẾU',
            key: 'reference',
            width: 150,
            render: (_, record) => {
                if (record.test && record.test.min_limit !== null && record.test.max_limit !== null) {
                    return `${record.test.min_limit} - ${record.test.max_limit}`;
                }
                return '-';
            }
        },
        {
            title: 'KẾT QUẢ CŨ',
            key: 'old_result',
            width: 120,
            render: () => <Text type="secondary">-</Text>
        }
    ];

    // Group tests by service_name
    const groupedServices = useMemo(() => {
        if (!selectedOrder || !selectedOrder.details) return [];
        const groups: Record<string, LabOrderDetail[]> = {};
        selectedOrder.details.forEach(detail => {
            const groupName = detail.service_name || 'Khác';
            if (!groups[groupName]) {
                groups[groupName] = [];
            }
            groups[groupName].push(detail);
        });
        return Object.entries(groups).map(([name, activeTests]) => ({
            name,
            tests: activeTests
        }));
    }, [selectedOrder]);

    return (
        <Row gutter={16} className="h-full">
            {/* Cột trái: Worklist */}
            <Col xs={24} md={8} lg={6} className="h-[calc(100vh-100px)] overflow-y-auto" style={{ borderRight: '1px solid #f0f0f0' }}>
                <Card bodyStyle={{ padding: '8px' }} bordered={false}>
                    <div className="flex justify-between items-center mb-2 px-1">
                        <Text strong>Danh sách chỉ định</Text>
                        <Tooltip title={soundEnabled ? 'Tắt âm báo' : 'Bật âm báo'}>
                            <Button
                                type="text"
                                size="small"
                                icon={<SoundOutlined />}
                                onClick={toggleSound}
                                style={{ color: soundEnabled ? '#1890ff' : '#bfbfbf' }}
                            />
                        </Tooltip>
                    </div>
                    <Tabs
                        activeKey={activeTab}
                        onChange={setActiveTab}
                        size="small"
                        items={[
                            { key: 'ROUTINE', label: `Ca thường (${routineCount})` },
                            { key: 'STAT', label: <span className="text-red-500 font-medium">Cấp cứu ({statCount})</span> },
                        ]}
                    />

                    <div className="flex flex-col gap-2 mt-4">
                        {filteredOrders.map(order => (
                            <div
                                key={order.id}
                                className={`p-3 border rounded-md cursor-pointer transition-colors ${selectedOrder?.id === order.id ? 'bg-blue-50 border-blue-300' : 'hover:bg-gray-50'}`}
                                onClick={() => handleSelectOrder(order)}
                            >
                                <div className="flex justify-between items-start mb-1">
                                    <Text type="secondary" className="font-mono text-xs">
                                        SID-{order.id.slice(0, 6).toUpperCase()}
                                    </Text>
                                    <Text type="secondary" className="text-xs">
                                        {dayjs(order.order_time).format('HH:mm')}
                                    </Text>
                                </div>
                                <div className="flex items-center gap-2 mb-1">
                                    <Text strong className="text-sm">{order.patient_name || 'Bệnh nhân'}</Text>
                                    {order.priority === 'STAT' && <Tag color="red" className="m-0 text-[10px] leading-none py-1">STAT</Tag>}
                                </div>
                                <div className="flex justify-between items-center mt-2">
                                    <Text type="secondary" className="text-xs">
                                        {order.patient_code || ''}
                                    </Text>
                                    <Badge status={
                                        order.status === 'PROCESSING' || order.status === 'SAMPLING' ? 'processing' :
                                            order.status === 'COMPLETED' ? 'warning' :
                                                order.status === 'VERIFIED' ? 'success' : 'default'
                                    } text={<span className="text-xs font-medium">
                                        {order.status === 'PROCESSING' || order.status === 'SAMPLING' ? 'Đang chạy' :
                                            order.status === 'COMPLETED' ? 'Chờ duyệt' :
                                                order.status === 'VERIFIED' ? '✓ Đã duyệt' : 'Chờ nhận'}
                                    </span>} />
                                </div>
                            </div>
                        ))}
                    </div>
                </Card>
            </Col>

            {/* Cột phải: Content */}
            <Col xs={24} md={16} lg={18}>
                <Card bodyStyle={{ padding: '24px' }} className="h-full" bordered={false}>
                    {selectedOrder ? (
                        <div className="flex flex-col space-y-6">
                            {/* Header Bệnh nhân */}
                            <div className="flex justify-between items-start">
                                <div>
                                    <Title level={4} className="!mb-2">{selectedOrder.patient_name || '—'}</Title>
                                    <Space split={<Divider type="vertical" />} className="text-gray-500">
                                        <Text>SID: <span className="font-mono font-medium">SID-{selectedOrder.id.slice(0, 6).toUpperCase()}</span></Text>
                                        <Text>Mã BN: {selectedOrder.patient_code}</Text>
                                    </Space>
                                </div>
                                <div className="text-right">
                                    <div className="mb-1">
                                        <Space>
                                            <Tooltip title={soundEnabled ? 'Tắt âm báo' : 'Bật âm báo'}>
                                                <Button
                                                    type="text"
                                                    size="small"
                                                    icon={<SoundOutlined />}
                                                    onClick={toggleSound}
                                                    style={{ color: soundEnabled ? '#1890ff' : '#bfbfbf', padding: '0 4px', marginRight: 8 }}
                                                />
                                            </Tooltip>
                                            <Badge status={selectedOrder.status === 'COMPLETED' ? 'warning' : 'processing'} text={selectedOrder.status === 'COMPLETED' ? 'Chờ duyệt' : 'Đang xử lý'} />
                                        </Space>
                                    </div>
                                    <Text type="secondary" className="text-xs">
                                        Chỉ định lúc: {dayjs(selectedOrder.order_time).format('HH:mm • DD/MM')}
                                    </Text>
                                </div>
                            </div>

                            {/* Toolbar */}
                            <div className="flex justify-between items-center bg-gray-50 p-3 rounded-lg border">
                                <Space size="large">
                                    <div>
                                        <Text type="secondary" className="block text-xs">Máy do</Text>
                                        <Text>Sysmex XN-1000</Text>
                                    </div>
                                    <Divider type="vertical" className="h-8" />
                                    <div>
                                        <Text type="secondary" className="block text-xs">Loại mẫu</Text>
                                        <Text>Máu toàn phần (EDTA)</Text>
                                    </div>
                                </Space>
                                <Space>
                                    <Button icon={<HistoryOutlined />}>Lịch sử</Button>
                                    <Button icon={<PrinterOutlined />}>In nhãn</Button>
                                </Space>
                            </div>

                            <div className="p-4 border rounded bg-gray-50 flex items-start gap-3">
                                <div className="flex-1">
                                    <Text strong className="block mb-1">Ghi chú lâm sàng:</Text>
                                    <Text>{selectedOrder.note || 'Không có ghi chú'}</Text>
                                </div>
                                <div className="flex gap-2">
                                    <Button icon={<SaveOutlined />} onClick={handleSaveTemp}>
                                        Lưu tất cả
                                    </Button>
                                    <Button type="primary" icon={<CheckOutlined />} onClick={handleVerify} className="bg-green-600">
                                        Duyệt KQ (F9)
                                    </Button>
                                </div>
                            </div>

                            <Table
                                columns={[
                                    {
                                        title: 'TÊN DỊCH VỤ',
                                        dataIndex: 'name',
                                        key: 'name',
                                        render: (text) => <Text strong>{text}</Text>
                                    },
                                    {
                                        title: 'SỐ THÔNG SỐ',
                                        key: 'count',
                                        render: (_, record) => `${record.tests.length} thông số`
                                    },
                                    {
                                        title: 'TRẠNG THÁI',
                                        key: 'status',
                                        render: (_, record) => {
                                            const filledCount = record.tests.filter((t: LabOrderDetail) => inputValues[t.id] !== undefined && inputValues[t.id].trim() !== '').length;
                                            return <Text type={filledCount === record.tests.length ? 'success' : 'warning'}>{filledCount}/{record.tests.length} đã nhập</Text>;
                                        }
                                    },
                                    {
                                        title: 'THAO TÁC',
                                        key: 'action',
                                        width: 150,
                                        render: (_, record) => (
                                            <Button type="primary" size="small" onClick={() => setSelectedServiceGroup(record.name)}>
                                                Nhập kết quả
                                            </Button>
                                        )
                                    }
                                ]}
                                dataSource={groupedServices}
                                rowKey="name"
                                pagination={false}
                                size="small"
                                bordered
                            />
                        </div>
                    ) : (
                        <div className="h-full flex flex-col items-center justify-center text-gray-400">
                            <HistoryOutlined style={{ fontSize: 48, marginBottom: 16 }} />
                            <Text className="text-gray-400">Chọn một phiếu xét nghiệm để xem kết quả</Text>
                        </div>
                    )}
                </Card>
            </Col>

            {/* Modal Nhập Kết Quả */}
            <Modal
                title={`Nhập kết quả: ${selectedServiceGroup}`}
                open={!!selectedServiceGroup}
                onCancel={() => setSelectedServiceGroup(null)}
                width={900}
                style={{ top: 20 }}
                destroyOnClose
                footer={[
                    <Button key="cancel" onClick={() => setSelectedServiceGroup(null)}>
                        Đóng
                    </Button>,
                    <Button key="save" type="primary" icon={<SaveOutlined />} onClick={() => {
                        handleSaveTemp();
                        setSelectedServiceGroup(null);
                    }}>
                        Lưu kết quả nhóm này
                    </Button>
                ]}
            >
                <Table
                    columns={columns}
                    dataSource={selectedServiceGroup ? groupedServices.find(g => g.name === selectedServiceGroup)?.tests || [] : []}
                    rowKey="id"
                    pagination={false}
                    size="small"
                    bordered
                    scroll={{ y: 'calc(100vh - 250px)' }}
                />
            </Modal>
        </Row>
    );
}
