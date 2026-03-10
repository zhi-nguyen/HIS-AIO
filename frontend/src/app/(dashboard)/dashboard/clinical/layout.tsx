'use client';

import React from 'react';
import { Layout } from 'antd';
import QueueSidebar from '@/components/clinical/QueueSidebar';

const { Content } = Layout;

export default function ClinicalLayout({ children }: { children: React.ReactNode }) {
    return (
        <Layout className="bg-white flex flex-row" style={{ height: 'calc(100vh - 64px)' }}>
            <QueueSidebar />
            <Content className="bg-white flex-1 p-4 overflow-hidden flex flex-col min-h-0 h-full">
                {children}
            </Content>
        </Layout>
    );
}
