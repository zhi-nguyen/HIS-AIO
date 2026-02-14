'use client';

import { Spin, Typography } from 'antd';
import { LoadingOutlined } from '@ant-design/icons';

const { Text } = Typography;

/**
 * Loading Component
 * Hiển thị loading dạng full page hoặc inline
 */

interface LoadingProps {
    fullPage?: boolean;
    tip?: string;
    size?: 'small' | 'default' | 'large';
}

export default function Loading({ fullPage = false, tip, size = 'large' }: LoadingProps) {
    const spinner = (
        <div className="text-center">
            <Spin
                indicator={<LoadingOutlined style={{ fontSize: size === 'large' ? 48 : size === 'default' ? 32 : 24 }} spin />}
            />
            {tip && <div className="mt-2"><Text>{tip}</Text></div>}
        </div>
    );

    if (fullPage) {
        return (
            <div className="fixed inset-0 flex items-center justify-center bg-white/80 z-50">
                <div className="text-center">
                    {spinner}
                </div>
            </div>
        );
    }

    return (
        <div className="flex items-center justify-center py-12">
            {spinner}
        </div>
    );
}
