'use client';

import { Result, Button, Typography } from 'antd';
import { ReloadOutlined, HomeOutlined } from '@ant-design/icons';

const { Text } = Typography;

/**
 * Empty State Component
 * Hiển thị trạng thái rỗng với hành động
 */

interface EmptyStateProps {
    title?: string;
    description?: string;
    icon?: React.ReactNode;
    actionText?: string;
    onAction?: () => void;
    secondaryActionText?: string;
    onSecondaryAction?: () => void;
}

export default function EmptyState({
    title = 'Không có dữ liệu',
    description = 'Chưa có dữ liệu để hiển thị.',
    icon,
    actionText,
    onAction,
    secondaryActionText,
    onSecondaryAction,
}: EmptyStateProps) {
    return (
        <Result
            icon={icon}
            title={title}
            subTitle={<Text type="secondary">{description}</Text>}
            extra={
                <>
                    {actionText && onAction && (
                        <Button type="primary" onClick={onAction}>
                            {actionText}
                        </Button>
                    )}
                    {secondaryActionText && onSecondaryAction && (
                        <Button onClick={onSecondaryAction}>
                            {secondaryActionText}
                        </Button>
                    )}
                </>
            }
        />
    );
}

/**
 * Not Found Component
 */
export function NotFound({ onGoBack, onGoHome }: { onGoBack?: () => void; onGoHome?: () => void }) {
    return (
        <Result
            status="404"
            title="Không tìm thấy trang"
            subTitle="Xin lỗi, trang bạn đang tìm kiếm không tồn tại."
            extra={[
                onGoBack && (
                    <Button key="back" icon={<ReloadOutlined />} onClick={onGoBack}>
                        Quay lại
                    </Button>
                ),
                <Button key="home" type="primary" icon={<HomeOutlined />} onClick={onGoHome || (() => window.location.href = '/dashboard')}>
                    Về trang chủ
                </Button>,
            ]}
        />
    );
}

/**
 * Access Denied Component
 */
export function AccessDenied({ onGoBack }: { onGoBack?: () => void }) {
    return (
        <Result
            status="403"
            title="Không có quyền truy cập"
            subTitle="Xin lỗi, bạn không có quyền truy cập trang này."
            extra={
                <Button type="primary" onClick={onGoBack || (() => window.location.href = '/dashboard')}>
                    Quay lại
                </Button>
            }
        />
    );
}
