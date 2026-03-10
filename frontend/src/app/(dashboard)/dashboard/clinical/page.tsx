'use client';

import { Empty } from 'antd';

export default function ClinicalEmptyPage() {
    return (
        <div className="flex h-full items-center justify-center">
            <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                    <span className="text-gray-500 text-base">
                        Vui lòng chọn bệnh nhân từ hàng đợi bên trái để bắt đầu khám.
                    </span>
                }
            />
        </div>
    );
}
