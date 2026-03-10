'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
    Card, Input, Button, Tag, Typography, Row, Col, Badge, Select,
    Spin, Empty, App, Tooltip,
} from 'antd';
import {
    SearchOutlined, ShoppingCartOutlined, DeleteOutlined,
    SendOutlined, ThunderboltOutlined, CheckCircleOutlined,
} from '@ant-design/icons';
import { clsApi } from '@/lib/services';

const { Text } = Typography;

/* ── Interfaces ─────────────────────────────────────────── */
interface CLSService {
    id: string;
    code: string;
    name: string;
    price: number;
    category: string;
}

interface OrderSetDef {
    label: string;
    /** Danh sách mã dịch vụ (code) thuộc gói */
    codes: string[];
}

/* ── Gói chỉ định nhanh (Order Sets) ─────────────────── */
const ORDER_SETS: OrderSetDef[] = [
    {
        label: 'Bộ mỡ máu',
        codes: ['XN-SH-006', 'XN-SH-007', 'XN-SH-001'],
    },
    {
        label: 'Chức năng Gan - Thận',
        codes: ['XN-SH-004', 'XN-SH-005', 'XN-SH-003', 'XN-SH-008'],
    },
    {
        label: 'Gói Tái khám Tiểu đường',
        codes: ['XN-SH-001', 'XN-SH-002', 'XN-HH-001'],
    },
];

/* ── Màu tag theo category ──────────────────────────────── */
const CATEGORY_COLORS: Record<string, string> = {
    'Huyết học': '#d4380d',
    'Sinh hóa': '#d48806',
    'CĐHA': '#0958d9',
    'Thăm dò chức năng': '#531dab',
};

/* ── Helper: format tiền VND ─────────────────────────────── */
function formatVND(value: number): string {
    return new Intl.NumberFormat('vi-VN').format(value) + ' đ';
}

/* ════════════════════════════════════════════════════════════
   Component chính: CLSOrderTab
   ════════════════════════════════════════════════════════════ */
export default function CLSOrderTab({
    visitId,
    patientId,
}: {
    visitId: string;
    patientId?: string;
}) {
    const { message } = App.useApp();

    /* ── State ──────────────────────────────────────────── */
    const [services, setServices] = useState<CLSService[]>([]);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [searchText, setSearchText] = useState('');
    const [filterCategory, setFilterCategory] = useState<string | undefined>(undefined);

    /* ── Fetch catalog ─────────────────────────────────── */
    const fetchServices = useCallback(async () => {
        setLoading(true);
        try {
            const data = await clsApi.getServices();
            // Handle both array and paginated response
            const list: CLSService[] = Array.isArray(data) ? data : (data.results || []);
            setServices(list.map((s: CLSService) => ({ ...s, price: Number(s.price) })));
        } catch (e) {
            console.error('Fetch CLS services error:', e);
            message.error('Không thể tải danh mục dịch vụ');
        } finally {
            setLoading(false);
        }
    }, [message]);

    useEffect(() => {
        fetchServices();
    }, [fetchServices]);

    /* ── Derived: categories ───────────────────────────── */
    const categories = useMemo(() => {
        const cats = new Set(services.map(s => s.category));
        return Array.from(cats).sort();
    }, [services]);

    /* ── Derived: filtered list ──────────────────────── */
    const filteredServices = useMemo(() => {
        let list = services;
        if (filterCategory) {
            list = list.filter(s => s.category === filterCategory);
        }
        if (searchText.trim()) {
            const q = searchText.toLowerCase();
            list = list.filter(
                s => s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q)
            );
        }
        return list;
    }, [services, filterCategory, searchText]);

    /* ── Selection helpers ─────────────────────────────── */
    const toggleService = (id: string) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            if (next.has(id)) next.delete(id);
            else next.add(id);
            return next;
        });
    };

    const removeSelected = (id: string) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            next.delete(id);
            return next;
        });
    };

    /* ── Order Set: chọn toàn bộ gói ───────────────────── */
    const applyOrderSet = (set: OrderSetDef) => {
        setSelectedIds(prev => {
            const next = new Set(prev);
            for (const code of set.codes) {
                const svc = services.find(s => s.code === code);
                if (svc) next.add(svc.id);
            }
            return next;
        });
    };

    /* ── Derived: selected items & total ──────────────── */
    const selectedServices = useMemo(() => {
        return services.filter(s => selectedIds.has(s.id));
    }, [services, selectedIds]);

    const totalCost = useMemo(() => {
        return selectedServices.reduce((sum, s) => sum + s.price, 0);
    }, [selectedServices]);

    /* ── Submit ──────────────────────────────────────────── */
    const handleSubmit = async () => {
        if (selectedIds.size === 0) {
            message.warning('Chưa chọn dịch vụ nào');
            return;
        }
        setSubmitting(true);
        try {
            const res = await clsApi.batchOrder({
                visit_id: visitId,
                service_ids: Array.from(selectedIds),
            });
            if (res.success) {
                message.success(`Đã phát hành ${res.count} chỉ định CLS`);
                setSelectedIds(new Set());
            }
        } catch (err: unknown) {
            const error = err as { response?: { status?: number; data?: { duplicates?: string[] } } };
            if (error?.response?.status === 409 && error?.response?.data?.duplicates) {
                message.warning(`Dịch vụ đã được chỉ định: ${error.response.data.duplicates.join(', ')}`);
            } else {
                message.error('Không thể phát hành chỉ định');
            }
        } finally {
            setSubmitting(false);
        }
    };

    /* ── Render: Loading ─────────────────────────────────── */
    if (loading) {
        return (
            <div className="flex items-center justify-center h-full">
                <Spin size="large" />
                <span className="ml-3 text-gray-400">Đang tải danh mục dịch vụ...</span>
            </div>
        );
    }

    /* ── Render ───────────────────────────────────────────── */
    return (
        <div className="h-full overflow-y-auto p-4 pt-2 pb-10" style={{ scrollbarWidth: 'thin' }}>
            <Row gutter={20} className="h-full">
                {/* ======== CỘT TRÁI: Catalog ======== */}
                <Col xs={24} lg={16}>
                    {/* ── Gói chỉ định nhanh ────────── */}
                    <div className="mb-4">
                        <div className="flex items-center gap-2 mb-3">
                            <ThunderboltOutlined className="text-amber-500" />
                            <Text strong className="text-sm text-gray-700 tracking-wide uppercase">
                                Gói chỉ định nhanh (Order Sets)
                            </Text>
                        </div>
                        <div className="flex flex-wrap gap-2">
                            {ORDER_SETS.map(set => (
                                <Button
                                    key={set.label}
                                    size="middle"
                                    onClick={() => applyOrderSet(set)}
                                    className="border-blue-200 text-blue-700 hover:bg-blue-50 font-medium"
                                >
                                    + {set.label}
                                </Button>
                            ))}
                        </div>
                    </div>

                    {/* ── Search + Filter ────────────── */}
                    <div className="flex gap-3 mb-4">
                        <Input
                            placeholder="Tìm kiếm theo mã, tên dịch vụ..."
                            prefix={<SearchOutlined className="text-gray-400" />}
                            allowClear
                            value={searchText}
                            onChange={e => setSearchText(e.target.value)}
                            className="flex-1"
                            size="large"
                        />
                        <Select
                            placeholder="Tất cả danh mục"
                            allowClear
                            value={filterCategory}
                            onChange={v => setFilterCategory(v)}
                            style={{ minWidth: 200 }}
                            size="large"
                            options={[
                                ...categories.map(c => ({ label: c, value: c })),
                            ]}
                        />
                    </div>

                    {/* ── Grid dịch vụ ───────────────── */}
                    {filteredServices.length === 0 ? (
                        <Empty
                            image={Empty.PRESENTED_IMAGE_SIMPLE}
                            description="Không tìm thấy dịch vụ phù hợp"
                        />
                    ) : (
                        <Row gutter={[12, 12]}>
                            {filteredServices.map(svc => {
                                const isSelected = selectedIds.has(svc.id);
                                return (
                                    <Col xs={24} md={12} key={svc.id}>
                                        <Card
                                            hoverable
                                            onClick={() => toggleService(svc.id)}
                                            className={`cursor-pointer transition-all rounded-xl ${isSelected
                                                    ? 'border-blue-400 bg-blue-50/40 shadow-sm'
                                                    : 'border-gray-200 hover:border-blue-200'
                                                }`}
                                            styles={{ body: { padding: '14px 16px' } }}
                                        >
                                            <div className="flex items-center justify-between">
                                                <div className="flex-1 min-w-0">
                                                    <div className="font-semibold text-gray-800 text-sm mb-1.5 truncate">
                                                        {svc.name}
                                                    </div>
                                                    <div className="flex items-center gap-2">
                                                        <Tag
                                                            color={CATEGORY_COLORS[svc.category] || 'default'}
                                                            className="m-0 text-xs border-0"
                                                            bordered={false}
                                                        >
                                                            {svc.category}
                                                        </Tag>
                                                        <Text className="text-xs text-gray-500">
                                                            {formatVND(svc.price)}
                                                        </Text>
                                                    </div>
                                                </div>
                                                {/* Radio-style indicator */}
                                                <div
                                                    className={`w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 ml-3 transition-all ${isSelected
                                                            ? 'border-blue-500 bg-blue-500'
                                                            : 'border-gray-300'
                                                        }`}
                                                >
                                                    {isSelected && (
                                                        <CheckCircleOutlined className="text-white text-xs" />
                                                    )}
                                                </div>
                                            </div>
                                        </Card>
                                    </Col>
                                );
                            })}
                        </Row>
                    )}
                </Col>

                {/* ======== CỘT PHẢI: Dịch vụ đã chọn ======== */}
                <Col xs={24} lg={8}>
                    <div className="bg-white rounded-xl border border-gray-200 shadow-sm sticky top-0">
                        {/* Header */}
                        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                            <div className="flex items-center gap-2 text-gray-700 font-bold text-sm">
                                <ShoppingCartOutlined className="text-base" />
                                Dịch vụ đã chọn
                            </div>
                            <Badge
                                count={selectedIds.size}
                                showZero
                                className="[&_.ant-badge-count]:bg-blue-500"
                            />
                        </div>

                        {/* Selected list */}
                        <div
                            className="px-4 py-3 space-y-2"
                            style={{ maxHeight: 360, overflowY: 'auto', scrollbarWidth: 'thin' }}
                        >
                            {selectedServices.length === 0 ? (
                                <div className="text-center py-10 text-gray-400 text-sm">
                                    <div className="text-3xl mb-2 opacity-30">📋</div>
                                    <div className="font-medium mb-1">Chưa có chỉ định nào</div>
                                    <div className="text-xs text-gray-300">
                                        Hãy chọn dịch vụ từ danh mục hoặc các gói khám nhanh bên trái.
                                    </div>
                                </div>
                            ) : (
                                selectedServices.map(svc => (
                                    <div
                                        key={svc.id}
                                        className="flex items-center justify-between bg-gray-50 rounded-lg px-3 py-2"
                                    >
                                        <div className="flex-1 min-w-0 mr-2">
                                            <div className="text-sm font-medium text-gray-700 truncate">
                                                {svc.name}
                                            </div>
                                            <div className="text-xs text-gray-400">
                                                {formatVND(svc.price)}
                                            </div>
                                        </div>
                                        <Tooltip title="Bỏ chọn">
                                            <Button
                                                type="text"
                                                size="small"
                                                danger
                                                icon={<DeleteOutlined />}
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    removeSelected(svc.id);
                                                }}
                                            />
                                        </Tooltip>
                                    </div>
                                ))
                            )}
                        </div>

                        {/* Footer: Total + Submit */}
                        <div className="px-4 py-3 border-t border-gray-100">
                            <div className="flex items-center justify-between mb-3">
                                <Text strong className="text-gray-600 text-sm">
                                    TỔNG CHI PHÍ:
                                </Text>
                                <Text strong className="text-lg text-blue-700">
                                    {formatVND(totalCost)} <span className="text-xs font-normal text-gray-400">VNĐ</span>
                                </Text>
                            </div>
                            <Button
                                type="primary"
                                block
                                size="large"
                                icon={<SendOutlined />}
                                loading={submitting}
                                disabled={selectedIds.size === 0}
                                onClick={handleSubmit}
                                className="bg-[#1d3557] border-0 h-12 text-base font-bold tracking-wide rounded-lg hover:bg-[#2a4a7f]"
                            >
                                PHÁT HÀNH CHỈ ĐỊNH
                            </Button>
                        </div>
                    </div>
                </Col>
            </Row>
        </div>
    );
}
