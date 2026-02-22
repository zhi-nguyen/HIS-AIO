'use client';

import { useState } from 'react';
import { Badge, Popover, Input, Button, Space, Typography, Tag } from 'antd';
import {
    ScanOutlined,
    LinkOutlined,
    DisconnectOutlined,
    CheckCircleFilled,
    CloseCircleFilled,
} from '@ant-design/icons';

const { Text } = Typography;

interface ScannerStatusProps {
    isConnected: boolean;
    stationId: string | null;
    lastScan: string | null;
    onSetStationId: (id: string | null) => void;
    onDisconnect: () => void;
}

/**
 * ScannerStatus — Header indicator for remote scanner connection.
 * Shows green/red dot + station ID. Click to pair/unpair.
 */
export default function ScannerStatus({
    isConnected,
    stationId,
    lastScan,
    onSetStationId,
    onDisconnect,
}: ScannerStatusProps) {
    const [inputId, setInputId] = useState('');
    const [popoverOpen, setPopoverOpen] = useState(false);

    const handlePair = () => {
        const trimmed = inputId.trim().toUpperCase();
        if (trimmed) {
            onSetStationId(trimmed);
            setInputId('');
            setPopoverOpen(false);
        }
    };

    const handleUnpair = () => {
        onSetStationId(null);
        onDisconnect();
        setPopoverOpen(false);
    };

    const popoverContent = (
        <div style={{ width: 280 }}>
            {stationId ? (
                <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                        <Text type="secondary">Trạm hiện tại:</Text>
                        <div>
                            <Tag
                                color={isConnected ? 'green' : 'red'}
                                icon={isConnected ? <CheckCircleFilled /> : <CloseCircleFilled />}
                                style={{ fontSize: 14, padding: '4px 12px', marginTop: 4 }}
                            >
                                {stationId}
                            </Tag>
                        </div>
                    </div>

                    <div>
                        <Text type="secondary">Trạng thái:</Text>
                        <div>
                            <Text strong style={{ color: isConnected ? '#52c41a' : '#ff4d4f' }}>
                                {isConnected ? '🟢 Đã kết nối' : '🔴 Mất kết nối (đang thử lại...)'}
                            </Text>
                        </div>
                    </div>

                    {lastScan && (
                        <div>
                            <Text type="secondary">Lần quét cuối:</Text>
                            <div>
                                <Text code style={{ fontSize: 12, wordBreak: 'break-all' }}>
                                    {lastScan.length > 40 ? lastScan.substring(0, 40) + '...' : lastScan}
                                </Text>
                            </div>
                        </div>
                    )}

                    <Button
                        danger
                        block
                        icon={<DisconnectOutlined />}
                        onClick={handleUnpair}
                        style={{ marginTop: 8 }}
                    >
                        Ngắt kết nối
                    </Button>
                </Space>
            ) : (
                <Space direction="vertical" style={{ width: '100%' }}>
                    <Text>Nhập mã trạm để ghép đôi với điện thoại quét:</Text>
                    <Input
                        placeholder="VD: QUAY_TIEP_DON_01"
                        value={inputId}
                        onChange={(e) => setInputId(e.target.value)}
                        onPressEnter={handlePair}
                        prefix={<LinkOutlined />}
                        autoFocus
                    />
                    <Button
                        type="primary"
                        block
                        icon={<ScanOutlined />}
                        onClick={handlePair}
                        disabled={!inputId.trim()}
                    >
                        Ghép đôi Scanner
                    </Button>
                </Space>
            )}
        </div>
    );

    return (
        <Popover
            content={popoverContent}
            title={
                <Space>
                    <ScanOutlined />
                    <span>Remote Scanner</span>
                </Space>
            }
            trigger="click"
            placement="bottomRight"
            open={popoverOpen}
            onOpenChange={setPopoverOpen}
        >
            <Button
                type="text"
                className="text-lg"
                icon={
                    <Badge
                        dot
                        status={isConnected ? 'success' : stationId ? 'error' : 'default'}
                    >
                        <ScanOutlined style={{ fontSize: 18 }} />
                    </Badge>
                }
            />
        </Popover>
    );
}
