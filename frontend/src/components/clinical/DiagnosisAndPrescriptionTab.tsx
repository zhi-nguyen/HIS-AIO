'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    Card, Button, Input, InputNumber, Select, Space, Tag, Typography, Divider,
    Table, Tooltip, Empty, Spin, Alert, Modal, Form, Row, Col, Badge, message as antMessage,
} from 'antd';
import {
    PlusOutlined, DeleteOutlined, MedicineBoxOutlined, SaveOutlined,
    SearchOutlined, CheckCircleOutlined, WarningOutlined, InfoCircleOutlined,
    FileTextOutlined, PrinterOutlined, ExclamationCircleOutlined,
} from '@ant-design/icons';
import { pharmacyApi } from '@/lib/services';
import type { Medication, PrescriptionDetail, Prescription, PrescriptionDetailInput } from '@/lib/services';
import dayjs from 'dayjs';

const { Text, Title } = Typography;
const { TextArea } = Input;

// ─── ICD-10 types ─────────────────────────────────────────────────────────────
interface ICD10Result {
    code: string;
    name: string;
    subcategory_code: string;
    subcategory_name: string;
}

// ─── ICD-10 Search Select ─────────────────────────────────────────────────────
function ICDSearchSelect({ onSelect }: { onSelect: (item: ICD10Result) => void }) {
    const [options, setOptions] = useState<ICD10Result[]>([]);
    const [loading, setLoading] = useState(false);
    const [value, setValue] = useState<string | undefined>(undefined);
    const [searchQuery, setSearchQuery] = useState('');

    // Debounce via useEffect — chỉ fire 1 request sau 400ms, hủy request cũ bằng AbortController
    useEffect(() => {
        if (!searchQuery || searchQuery.length < 2) {
            setOptions([]);
            return;
        }
        const controller = new AbortController();
        const timer = setTimeout(async () => {
            setLoading(true);
            try {
                const token = localStorage.getItem('his_access_token');
                // Không có trailing slash trước ? — Next.js rewrite strip nó gây Django 301
                const res = await fetch(
                    `/api/v1/core/icd10/search?q=${encodeURIComponent(searchQuery)}&limit=20`,
                    { headers: { Authorization: `Bearer ${token}` }, signal: controller.signal }
                );
                if (res.ok) setOptions(await res.json());
            } catch (e) {
                if ((e as Error).name !== 'AbortError') setOptions([]);
            } finally {
                setLoading(false);
            }
        }, 400);
        return () => { clearTimeout(timer); controller.abort(); };
    }, [searchQuery]);

    const handleSelect = useCallback((code: string) => {
        const item = options.find(o => o.code === code);
        if (item) { onSelect(item); setValue(undefined); setSearchQuery(''); setOptions([]); }
    }, [options, onSelect]);

    return (
        <Select
            showSearch
            filterOption={false}
            onSearch={setSearchQuery}
            onSelect={handleSelect}
            value={value}
            loading={loading}
            placeholder="Tìm mã ICD-10 (VD: I10, tăng huyết áp...)"
            notFoundContent={
                loading ? <Spin size="small" /> :
                searchQuery.length >= 2
                    ? <span style={{ fontSize: 12, color: '#999' }}>Không tìm thấy kết quả.</span>
                    : <span style={{ fontSize: 12, color: '#999' }}>Nhập ít nhất 2 ký tự để tìm kiếm...</span>
            }
            className="w-full"
            size="small"
            popupMatchSelectWidth={false}
            style={{ minWidth: 280 }}
            suffixIcon={<SearchOutlined style={{ color: '#666' }} />}
        >
            {options.map(item => (
                <Select.Option key={item.code} value={item.code}>
                    <div style={{ display: 'flex', flexDirection: 'column', padding: '2px 0' }}>
                        <span style={{ fontWeight: 600, fontFamily: 'monospace', color: '#1677ff', fontSize: 13 }}>
                            {item.code}
                            {' '}
                            <span style={{ fontWeight: 400, color: '#374151', fontFamily: 'inherit', fontSize: 12 }}>
                                — {item.name}
                            </span>
                        </span>
                        <span style={{ fontSize: 11, color: '#9ca3af' }}>{item.subcategory_name}</span>
                    </div>
                </Select.Option>
            ))}
        </Select>
    );
}

// ─── Common usage instruction presets ────────────────────────────────────────
const USAGE_PRESETS = [
    'Uống 1 viên x 2 lần/ngày (sáng - tối) sau ăn',
    'Uống 1 viên x 3 lần/ngày (sáng - trưa - tối) sau ăn',
    'Uống 2 viên x 2 lần/ngày (sáng - tối) sau ăn',
    'Uống 1 viên/ngày (buổi sáng) sau ăn',
    'Uống 1 viên khi đau, cách nhau ít nhất 4 giờ, tối đa 4 viên/ngày',
    'Tiêm tĩnh mạch chậm 1 lần/ngày',
    'Bôi ngoài da 2 lần/ngày (sáng - tối)',
    'Nhỏ mắt 1-2 giọt x 3 lần/ngày',
];

// ─── Types ───────────────────────────────────────────────────────────────────
interface DrugRow {
    key: string;
    medication: Medication | null;
    quantity: number;
    usage_instruction: string;
    duration_days: number | null;
}

interface DiagnosisAndPrescriptionTabProps {
    visitId: string;
    doctorId: string;
    /** Chẩn đoán sơ bộ từ AI / ICD (có thể rỗng) */
    initialDiagnosis?: string;
    /** Kế hoạch điều trị từ form khám (field treatment_plan) */
    initialTreatmentPlan?: string;
}

// ─── Medication Search Select ─────────────────────────────────────────────────
function MedSearchSelect({
    value,
    onChange,
}: {
    value: Medication | null;
    onChange: (med: Medication | null) => void;
}) {
    const [options, setOptions] = useState<Medication[]>([]);
    const [loading, setLoading] = useState(false);
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    const handleSearch = useCallback((q: string) => {
        if (timerRef.current) clearTimeout(timerRef.current);
        if (!q || q.length < 2) { setOptions([]); return; }
        timerRef.current = setTimeout(async () => {
            setLoading(true);
            try {
                const meds = await pharmacyApi.searchMedications(q);
                setOptions(meds);
            } catch { setOptions([]); }
            finally { setLoading(false); }
        }, 350);
    }, []);

    return (
        <Select
            showSearch
            filterOption={false}
            onSearch={handleSearch}
            value={value ? `${value.name} — ${value.strength || ''} (${value.dosage_form || ''})` : undefined}
            onChange={(id) => {
                const med = options.find(m => m.id === id) ?? null;
                onChange(med);
            }}
            loading={loading}
            placeholder="Tìm tên thuốc, hoạt chất..."
            notFoundContent={loading ? <Spin size="small" /> : <span className="text-gray-400 text-xs">Nhập ít nhất 2 ký tự...</span>}
            className="w-full"
            size="small"
            popupMatchSelectWidth={false}
            style={{ minWidth: 260 }}
        >
            {options.map(med => (
                <Select.Option key={med.id} value={med.id}>
                    <div className="flex flex-col py-0.5">
                        <span className="font-medium text-gray-800">{med.name}</span>
                        <span className="text-[11px] text-gray-400">
                            {med.active_ingredient} · {med.strength} · {med.dosage_form}
                            {med.inventory_count < 10 && (
                                <span className="text-orange-500 ml-1">⚠ Tồn: {med.inventory_count}</span>
                            )}
                        </span>
                    </div>
                </Select.Option>
            ))}
        </Select>
    );
}

// ─── Main Component ───────────────────────────────────────────────────────────
export default function DiagnosisAndPrescriptionTab({
    visitId,
    doctorId,
    initialDiagnosis = '',
    initialTreatmentPlan = '',
}: DiagnosisAndPrescriptionTabProps) {
    // ── Prescription state ───────────────────────────────────────────────────
    const [existingPrescription, setExistingPrescription] = useState<Prescription | null>(null);
    const [loadingRx, setLoadingRx] = useState(true);
    const [saving, setSaving] = useState(false);

    // ── Diagnosis / conclusion fields ────────────────────────────────────────
    // Bệnh chính: 1 mã ICD duy nhất + mô tả tùy chỉnh
    const [mainIcd, setMainIcd] = useState<{ code: string; name: string } | null>(null);
    const [mainNote, setMainNote] = useState('');              // Ghi chú bệnh chính
    // Bệnh phụ: nhiều mã ICD
    const [subIcds, setSubIcds] = useState<{ code: string; name: string }[]>([]);
    const [treatmentPlan, setTreatmentPlan] = useState(initialTreatmentPlan);
    const [note, setNote] = useState('');                      // Lời dặn bác sĩ

    // Tạo chuỗi diagnosis gửi lên backend
    const buildDiagnosis = useCallback(() => {
        const parts: string[] = [];
        if (mainIcd) {
            parts.push(`[Bệnh chính] ${mainIcd.code} - ${mainIcd.name}${mainNote ? `: ${mainNote}` : ''}`);
        }
        if (subIcds.length > 0) {
            subIcds.forEach(s => parts.push(`[Bệnh phụ] ${s.code} - ${s.name}`));
        }
        return parts.join('\n');
    }, [mainIcd, mainNote, subIcds]);

    // Khởi tạo từ initialDiagnosis nếu có
    useEffect(() => {
        if (!initialDiagnosis) return;
        setMainNote(initialDiagnosis);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // ── Drug table rows ──────────────────────────────────────────────────────
    const [drugRows, setDrugRows] = useState<DrugRow[]>([]);

    // ── Load existing prescription on mount ─────────────────────────────────
    useEffect(() => {
        setLoadingRx(true);
        pharmacyApi.getPrescriptionByVisit(visitId)
            .then((rx) => {
                if (!rx) return;
                setExistingPrescription(rx);
                // Lôi tèxt chẩn đoán cũ vào mainNote (hiển thị trong field ghi chú bệnh chính)
                setMainNote(rx.diagnosis || initialDiagnosis);
                setNote(rx.note || '');
                // Hydrate drug rows from details
                setDrugRows(
                    rx.details.map((d) => ({
                        key: d.id,
                        medication: {
                            id: d.medication,
                            name: d.medication_name,
                            strength: d.medication_strength,
                            dosage_form: d.medication_dosage_form,
                            unit: d.medication_unit,
                            selling_price: d.unit_price,
                            inventory_count: 999,
                            code: '',
                            active_ingredient: null,
                            usage_route: null,
                            category_name: null,
                        },
                        quantity: d.quantity,
                        usage_instruction: d.usage_instruction,
                        duration_days: d.duration_days,
                    }))
                );
            })
            .catch(() => { /* ignore, no prescription yet */ })
            .finally(() => setLoadingRx(false));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [visitId]);

    // ── Row manipulation ─────────────────────────────────────────────────────
    const addRow = () => {
        setDrugRows(prev => [
            ...prev,
            {
                key: `new-${Date.now()}`,
                medication: null,
                quantity: 10,
                usage_instruction: '',
                duration_days: 5,
            },
        ]);
    };

    const updateRow = <K extends keyof DrugRow>(key: string, field: K, value: DrugRow[K]) => {
        setDrugRows(prev => prev.map(r => r.key === key ? { ...r, [field]: value } : r));
    };

    const removeRow = (key: string) => {
        setDrugRows(prev => prev.filter(r => r.key !== key));
    };

    // ── Validation ───────────────────────────────────────────────────────────
    const validate = () => {
        if (!mainIcd && !mainNote.trim()) {
            antMessage.warning('Vui lòng chọn bệnh chính (ICD) trước khi lưu đơn.');
            return false;
        }
        for (const row of drugRows) {
            if (!row.medication) {
                antMessage.warning('Vui lòng chọn thuốc cho tất cả các dòng.');
                return false;
            }
            if (!row.usage_instruction.trim()) {
                antMessage.warning(`Vui lòng nhập cách dùng cho thuốc "${row.medication.name}".`);
                return false;
            }
        }
        return true;
    };

    // ── Save / Update ────────────────────────────────────────────────────────
    const handleSave = async () => {
        if (!validate()) return;
        setSaving(true);
        try {
            const detailsInput: PrescriptionDetailInput[] = drugRows
                .filter(r => r.medication)
                .map(r => ({
                    medication: r.medication!.id,
                    quantity: r.quantity,
                    usage_instruction: r.usage_instruction,
                    duration_days: r.duration_days,
                }));

            if (existingPrescription) {
                const updated = await pharmacyApi.updatePrescription(existingPrescription.id, {
                    diagnosis: buildDiagnosis(),
                    note,
                    details_input: detailsInput,
                });
                setExistingPrescription(updated);
                antMessage.success(`Đã cập nhật đơn thuốc ${updated.prescription_code}`);
            } else {
                const created = await pharmacyApi.createPrescription({
                    visit: visitId,
                    doctor: doctorId,
                    diagnosis: buildDiagnosis(),
                    note,
                    details_input: detailsInput,
                });
                setExistingPrescription(created);
                antMessage.success(`Đã tạo đơn thuốc ${created.prescription_code}`);
            }
        } catch (err: unknown) {
            const error = err as { response?: { data?: unknown } };
            console.error('Save prescription error', error?.response?.data);
            antMessage.error('Lưu đơn thuốc thất bại. Vui lòng kiểm tra lại.');
        } finally {
            setSaving(false);
        }
    };

    // ── Total price ──────────────────────────────────────────────────────────
    const totalPrice = drugRows.reduce((sum, r) => {
        return sum + (r.medication?.selling_price ?? 0) * r.quantity;
    }, 0);

    // ── Columns for drug table ────────────────────────────────────────────────
    const columns = [
        {
            title: '#',
            width: 36,
            render: (_: unknown, __: DrugRow, idx: number) => (
                <Text type="secondary" className="text-xs">{idx + 1}</Text>
            ),
        },
        {
            title: 'Thuốc',
            key: 'medication',
            render: (_: unknown, row: DrugRow) => (
                <MedSearchSelect
                    value={row.medication}
                    onChange={(med) => {
                        updateRow(row.key, 'medication', med);
                        // Auto-fill preset usage from route
                        if (med?.usage_route) {
                            const preset = USAGE_PRESETS.find(p => p.toLowerCase().includes(med.usage_route?.toLowerCase() ?? ''));
                            if (preset && !row.usage_instruction) updateRow(row.key, 'usage_instruction', preset);
                        }
                    }}
                />
            ),
        },
        {
            title: 'Hàm lượng',
            width: 110,
            render: (_: unknown, row: DrugRow) => (
                <Text className="text-xs text-gray-500 whitespace-nowrap">
                    {row.medication?.strength || '—'}
                    {row.medication?.dosage_form ? ` · ${row.medication.dosage_form}` : ''}
                </Text>
            ),
        },
        {
            title: 'Số lượng',
            width: 90,
            render: (_: unknown, row: DrugRow) => (
                <InputNumber
                    min={1}
                    max={999}
                    value={row.quantity}
                    onChange={(v) => updateRow(row.key, 'quantity', v ?? 1)}
                    className="w-full"
                    size="small"
                    controls={false}
                    addonAfter={<span className="text-xs">{row.medication?.unit || 'viên'}</span>}
                />
            ),
        },
        {
            title: 'Cách dùng',
            render: (_: unknown, row: DrugRow) => (
                <Select
                    value={row.usage_instruction || undefined}
                    onChange={(v) => updateRow(row.key, 'usage_instruction', v)}
                    placeholder="Chọn hoặc nhập..."
                    className="w-full"
                    size="small"
                    showSearch
                    allowClear
                    mode={undefined}
                    dropdownRender={(menu) => (
                        <>
                            {menu}
                            <Divider className="my-1" />
                            <div className="px-2 pb-1">
                                <Input
                                    size="small"
                                    placeholder="Nhập cách dùng tùy chỉnh..."
                                    onPressEnter={(e) => {
                                        const v = (e.target as HTMLInputElement).value.trim();
                                        if (v) updateRow(row.key, 'usage_instruction', v);
                                    }}
                                />
                            </div>
                        </>
                    )}
                >
                    {USAGE_PRESETS.map(p => (
                        <Select.Option key={p} value={p}>
                            <span className="text-xs">{p}</span>
                        </Select.Option>
                    ))}
                </Select>
            ),
        },
        {
            title: 'Ngày',
            width: 75,
            render: (_: unknown, row: DrugRow) => (
                <InputNumber
                    min={1}
                    max={365}
                    value={row.duration_days ?? undefined}
                    onChange={(v) => updateRow(row.key, 'duration_days', v)}
                    className="w-full"
                    size="small"
                    controls={false}
                    placeholder="ngày"
                />
            ),
        },
        {
            title: 'Thành tiền',
            width: 110,
            render: (_: unknown, row: DrugRow) => {
                const total = (row.medication?.selling_price ?? 0) * row.quantity;
                return (
                    <Text className="text-xs font-medium whitespace-nowrap">
                        {total > 0 ? total.toLocaleString('vi-VN') + 'đ' : '—'}
                    </Text>
                );
            },
        },
        {
            title: '',
            width: 36,
            render: (_: unknown, row: DrugRow) => (
                <Tooltip title="Xóa dòng">
                    <Button
                        type="text"
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={() => removeRow(row.key)}
                    />
                </Tooltip>
            ),
        },
    ];

    if (loadingRx) {
        return (
            <div className="flex items-center justify-center h-full">
                <Spin size="large" />
            </div>
        );
    }

    return (
        <div className="h-full overflow-y-auto p-4 pt-2 pb-10 space-y-4" style={{ scrollbarWidth: 'thin' }}>

            {/* ── Status banner if prescription already exists ── */}
            {existingPrescription && (
                <Alert
                    type={existingPrescription.status === 'DISPENSED' ? 'success' : 'info'}
                    showIcon
                    icon={existingPrescription.status === 'DISPENSED' ? <CheckCircleOutlined /> : <InfoCircleOutlined />}
                    message={
                        <span>
                            Đơn thuốc <strong>{existingPrescription.prescription_code}</strong>
                            {' '}·{' '}
                            {dayjs(existingPrescription.prescription_date).format('DD/MM/YYYY HH:mm')}
                            {' '}·{' '}
                            {existingPrescription.status === 'PENDING' && <Tag color="gold">Chờ phát</Tag>}
                            {existingPrescription.status === 'PARTIAL' && <Tag color="orange">Đã phát 1 phần</Tag>}
                            {existingPrescription.status === 'DISPENSED' && <Tag color="green">Đã phát thuốc</Tag>}
                            {existingPrescription.status === 'CANCELLED' && <Tag color="red">Đã hủy</Tag>}
                        </span>
                    }
                />
            )}

            {/* ── Section 1: Kết luận / Chẩn đoán ── */}
            <Card
                title={
                    <Space>
                        <FileTextOutlined className="text-green-500" />
                        <span className="text-[13px] font-bold text-gray-700 tracking-wide">KẾT LUẬN & CHẨN ĐOÁN</span>
                    </Space>
                }
                className="shadow-sm border-gray-200 rounded-xl [&>.ant-card-head]:border-b-0 [&>.ant-card-head]:min-h-[48px] [&>.ant-card-body]:pt-0"
            >
                <Row gutter={[16, 14]}>
                    {/* Bệnh chính */}
                    <Col span={24}>
                        <div style={{ marginBottom: 4 }}>
                            <span className="font-semibold text-sm text-gray-700">
                                Bệnh chính <span className="text-red-500">*</span>
                                <span className="font-normal text-xs text-gray-400 ml-1">(chỉ 1 mã ICD chính)</span>
                            </span>
                        </div>
                        {/* ICD chính search */}
                        {!mainIcd ? (
                            <ICDSearchSelect onSelect={(item) => setMainIcd(item)} />
                        ) : (
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                                <Tag
                                    color="blue"
                                    closable
                                    onClose={() => setMainIcd(null)}
                                    style={{ fontSize: 13, padding: '3px 10px', borderRadius: 6, fontWeight: 500 }}
                                >
                                    <span style={{ fontFamily: 'monospace', fontWeight: 700 }}>{mainIcd.code}</span>
                                    {' — '}{mainIcd.name}
                                </Tag>
                                <Input
                                    size="small"
                                    value={mainNote}
                                    onChange={e => setMainNote(e.target.value)}
                                    placeholder="Ghi chú thêm (giai đoạn, mức độ...)..."
                                    style={{ flex: 1, minWidth: 160 }}
                                />
                            </div>
                        )}
                    </Col>

                    {/* Bệnh phụ */}
                    <Col span={24}>
                        <div style={{ marginBottom: 4 }}>
                            <span className="font-semibold text-sm text-gray-700">
                                Bệnh phụ
                                <span className="font-normal text-xs text-gray-400 ml-1">(có thể chọn nhiều ICD)</span>
                            </span>
                        </div>
                        <ICDSearchSelect
                            onSelect={(item) => setSubIcds(prev =>
                                prev.find(x => x.code === item.code) ? prev : [...prev, item]
                            )}
                        />
                        {subIcds.length > 0 && (
                            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                                {subIcds.map(icd => (
                                    <Tag
                                        key={icd.code}
                                        closable
                                        onClose={() => setSubIcds(prev => prev.filter(x => x.code !== icd.code))}
                                        color="geekblue"
                                        style={{ fontSize: 12, borderRadius: 4 }}
                                    >
                                        <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{icd.code}</span>
                                        {' '}{icd.name.length > 45 ? icd.name.slice(0, 45) + '…' : icd.name}
                                    </Tag>
                                ))}
                            </div>
                        )}
                    </Col>

                    {/* Kế hoạch điều trị */}
                    <Col span={24}>
                        <Form.Item
                            label={<span className="font-medium text-gray-600 text-sm">Kế hoạch điều trị / Xử lý</span>}
                            className="mb-0"
                        >
                            <TextArea
                                rows={3}
                                value={treatmentPlan}
                                onChange={e => setTreatmentPlan(e.target.value)}
                                placeholder="VD: Dùng thuốc hạ áp, tái khám sau 1 tháng, kiêng mặn..."
                                className="bg-gray-50"
                            />
                        </Form.Item>
                    </Col>
                    <Col span={24}>
                        <Form.Item
                            label={<span className="font-medium text-gray-600 text-sm">Lời dặn bác sĩ</span>}
                            className="mb-0"
                        >
                            <TextArea
                                rows={2}
                                value={note}
                                onChange={e => setNote(e.target.value)}
                                placeholder="VD: Tái khám sau 2 tuần nếu triệu chứng không cải thiện. Uống đủ nước..."
                                className="bg-gray-50"
                            />
                        </Form.Item>
                    </Col>
                </Row>
            </Card>

            {/* ── Section 2: Kê đơn thuốc ── */}
            <Card
                title={
                    <div className="flex items-center justify-between w-full">
                        <Space>
                            <MedicineBoxOutlined className="text-blue-500" />
                            <span className="text-[13px] font-bold text-gray-700 tracking-wide">
                                KÊ ĐƠN THUỐC
                            </span>
                            {drugRows.length > 0 && (
                                <Badge count={drugRows.length} style={{ backgroundColor: '#1890ff' }} />
                            )}
                        </Space>
                        <Button
                            type="dashed"
                            size="small"
                            icon={<PlusOutlined />}
                            onClick={addRow}
                            className="text-blue-600 border-blue-300"
                        >
                            Thêm thuốc
                        </Button>
                    </div>
                }
                className="shadow-sm border-gray-200 rounded-xl [&>.ant-card-head]:border-b-0 [&>.ant-card-head]:min-h-[48px] [&>.ant-card-body]:pt-0"
            >
                {drugRows.length === 0 ? (
                    <Empty
                        image={Empty.PRESENTED_IMAGE_SIMPLE}
                        description={
                            <span className="text-gray-400 text-sm">
                                Chưa có thuốc nào. Nhấn <strong>Thêm thuốc</strong> để bắt đầu kê đơn.
                            </span>
                        }
                    >
                        <Button
                            type="primary"
                            ghost
                            icon={<PlusOutlined />}
                            onClick={addRow}
                        >
                            Thêm thuốc đầu tiên
                        </Button>
                    </Empty>
                ) : (
                    <>
                        <Table
                            dataSource={drugRows}
                            columns={columns}
                            rowKey="key"
                            pagination={false}
                            size="small"
                            className="[&_.ant-table-thead_.ant-table-cell]:bg-gray-50 [&_.ant-table-thead_.ant-table-cell]:text-xs [&_.ant-table-thead_.ant-table-cell]:font-semibold [&_.ant-table-thead_.ant-table-cell]:text-gray-500 [&_.ant-table-thead_.ant-table-cell]:py-2"
                            scroll={{ x: 900 }}
                        />

                        {/* Total price */}
                        <div className="flex justify-end mt-3 pt-3 border-t border-gray-100">
                            <div className="text-right">
                                <Text className="text-gray-500 text-sm mr-3">Tổng tiền thuốc:</Text>
                                <Text strong className="text-lg text-blue-600">
                                    {totalPrice.toLocaleString('vi-VN')}đ
                                </Text>
                            </div>
                        </div>
                    </>
                )}
            </Card>

            {/* ── Save button ── */}
            <div className="flex justify-end gap-3">
                {drugRows.length > 0 && (
                    <Button
                        size="large"
                        icon={<PrinterOutlined />}
                        className="font-medium"
                        disabled={!existingPrescription}
                        onClick={() => {
                            antMessage.info('Tính năng in đơn đang phát triển.');
                        }}
                    >
                        In đơn thuốc
                    </Button>
                )}
                <Button
                    type="primary"
                    size="large"
                    icon={<SaveOutlined />}
                    loading={saving}
                    onClick={handleSave}
                    className="font-medium bg-blue-600 border-blue-600 w-[180px]"
                >
                    {existingPrescription ? 'Cập nhật đơn thuốc' : 'Lưu đơn thuốc'}
                </Button>
            </div>
        </div>
    );
}
