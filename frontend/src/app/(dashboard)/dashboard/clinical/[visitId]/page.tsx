'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
    Card, Form, Input, Button, Space, Tag, Typography, Divider, Alert,
    Spin, InputNumber, Row, Col, Tabs, App, Progress, Drawer, Tooltip, Descriptions, Badge
} from 'antd';
import {
    HeartOutlined, FileTextOutlined, MedicineBoxOutlined, InfoCircleOutlined,
    WarningOutlined, ExperimentOutlined, UserOutlined, ArrowRightOutlined,
    RobotOutlined, SaveOutlined, CheckCircleOutlined, ArrowLeftOutlined,
    FundViewOutlined, BarcodeOutlined, EyeOutlined, PrinterOutlined, FileImageOutlined,
} from '@ant-design/icons';
import { visitApi, emrApi, aiApi, patientApi, lisApi, risApi } from '@/lib/services';
import type { Visit, Patient } from '@/types';
import { useRouter, useParams } from 'next/navigation';
import dayjs from 'dayjs';
import ReactMarkdown from 'react-markdown';
import CLSOrderTab from '@/components/clinical/CLSOrderTab';

const { Title, Text } = Typography;
const { TextArea } = Input;

interface VitalSigns {
    temperature?: number;
    systolic_bp?: number;
    diastolic_bp?: number;
    heart_rate?: number;
    respiratory_rate?: number;
    spo2?: number;
    weight?: number;
    height?: number;
}

interface ClinicalRecord {
    id: string;
    chief_complaint: string;
    history_of_present_illness?: string;
    physical_exam?: string;
    vital_signs?: VitalSigns;
    final_diagnosis?: string;
    treatment_plan?: string;
    ai_suggestion_json?: Record<string, unknown>;
    triage_agent_summary?: Record<string, unknown>;
    clinical_agent_summary?: Record<string, unknown>;
    is_finalized: boolean;
}

interface ICDCodeItem {
    code: string;
    name: string;
    confidence: number;
    type: 'main' | 'sub';
    in_system?: boolean | null;
    system_name?: string | null;
}

/* ──────────────────────────────────────────────────────────────────────
   KetQuaTab — Tab 3: Kết quả xét nghiệm (LIS) & Chẩn đoán hình ảnh (RIS)
   ────────────────────────────────────────────────────────────────────── */

interface LabResultRow {
    name: string;
    value: string;
    value_numeric: number | null;
    unit: string;
    ref_range: string;
    is_abnormal: boolean;
    is_critical: boolean;
    abnormal_flag: string | null; // 'H' | 'L' | 'HH' | 'LL'
}

interface ImagingResult {
    id: string;
    procedure_name: string;
    order_time: string;
    doctor_name: string;
    findings: string;
    conclusion: string;
    is_abnormal: boolean;
    image_url?: string;
    status: string;
}

function KetQuaTab({ visitId, onGoToDiagnosis }: { visitId: string; onGoToDiagnosis: () => void }) {
    const [labRows, setLabRows] = React.useState<LabResultRow[]>([]);
    const [imaging, setImaging] = React.useState<ImagingResult[]>([]);
    const [loadingLis, setLoadingLis] = React.useState(true);
    const [loadingRis, setLoadingRis] = React.useState(true);
    const [aiSummary, setAiSummary] = React.useState<string>('');

    useEffect(() => {
        // Fetch LIS orders for this visit
        lisApi.getOrders({ visit: visitId }).then((res) => {
            const orders = res.results || res || [];
            const rows: LabResultRow[] = [];
            for (const order of orders) {
                for (const detail of order.details || []) {
                    const result = detail.result;
                    if (!result) continue;
                    rows.push({
                        name: detail.test?.name || '--',
                        value: result.value_string || '--',
                        value_numeric: result.value_numeric ?? null,
                        unit: detail.test?.unit || '',
                        ref_range: detail.test?.min_limit != null && detail.test?.max_limit != null
                            ? `${detail.test.min_limit} - ${detail.test.max_limit}`
                            : '--',
                        is_abnormal: result.is_abnormal || false,
                        is_critical: result.is_critical || false,
                        abnormal_flag: result.abnormal_flag || null,
                    });
                }
            }
            setLabRows(rows);

            // Generate simple AI summary from abnormal values
            const abnormals = rows.filter(r => r.is_abnormal);
            if (abnormals.length > 0) {
                const parts = abnormals.map(r => {
                    const dir = (r.abnormal_flag === 'H' || r.abnormal_flag === 'HH') ? 'tăng cao' : 'giảm thấp';
                    return `**${r.name} (${r.value})** ${dir}`;
                });
                setAiSummary(`Bệnh nhân có ${parts.join(', ')}. Cần xem xét chẩn đoán và điều chỉnh phác đồ phù hợp.`);
            }
        }).catch(() => { }).finally(() => setLoadingLis(false));

        // Fetch RIS orders for this visit
        risApi.getOrders({ visit: visitId }).then((res) => {
            const orders = res.results || res || [];
            const imgs: ImagingResult[] = orders
                .filter((o: Record<string, unknown>) => o.result || o.findings)
                .map((o: Record<string, unknown>) => {
                    const result = (o.result || {}) as Record<string, unknown>;
                    return {
                        id: String(o.id),
                        procedure_name: String((o.procedure_detail as Record<string, unknown>)?.name || o.procedure_name || 'Chẩn đoán hình ảnh'),
                        order_time: String(o.order_time || ''),
                        doctor_name: String((o.doctor_detail as Record<string, unknown>)?.full_name || ''),
                        findings: String(result.findings || ''),
                        conclusion: String(result.conclusion || ''),
                        is_abnormal: Boolean(result.is_abnormal),
                        image_url: result.image_url as string | undefined,
                        status: String(o.status || ''),
                    };
                });
            setImaging(imgs);
        }).catch(() => { }).finally(() => setLoadingRis(false));
    }, [visitId]);

    const flagColor = (row: LabResultRow) => {
        if (row.is_critical) return '#cf1322';
        if (row.is_abnormal) return '#d4380d';
        return undefined;
    };

    const flagArrow = (row: LabResultRow) => {
        if (!row.is_abnormal) return null;
        const isHigh = row.abnormal_flag === 'H' || row.abnormal_flag === 'HH';
        return <span style={{ fontSize: 12 }}>{isHigh ? '↑' : '↓'}</span>;
    };

    const hasSummary = aiSummary.length > 0;

    return (
        <div className="h-full overflow-y-auto p-4 pt-3 space-y-3" style={{ scrollbarWidth: 'thin' }}>
            {/* AI Summary Banner */}
            {hasSummary && (
                <div style={{
                    background: 'linear-gradient(135deg, #f0f5ff 0%, #e8f4ff 100%)',
                    border: '1px solid #91caff',
                    borderRadius: 12,
                    padding: '12px 16px',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: 12,
                }}>
                    <div style={{
                        width: 40, height: 40, borderRadius: 10, background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                    }}>
                        <RobotOutlined style={{ color: '#fff', fontSize: 18 }} />
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontWeight: 700, fontSize: 13, color: '#3730a3', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                            ✨ AI Đọc kết quả tự động
                        </div>
                        <div style={{ fontSize: 13, color: '#374151', lineHeight: 1.6 }}>
                            {aiSummary.split('**').map((part, i) =>
                                i % 2 === 1
                                    ? <strong key={i} style={{ color: '#ef4444' }}>{part}</strong>
                                    : <span key={i}>{part}</span>
                            )}
                        </div>
                    </div>
                    <Button
                        type="primary"
                        size="small"
                        icon={<MedicineBoxOutlined />}
                        onClick={onGoToDiagnosis}
                        style={{
                            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
                            border: 'none',
                            borderRadius: 8,
                            fontWeight: 600,
                            fontSize: 12,
                            height: 34,
                            whiteSpace: 'nowrap',
                            flexShrink: 0,
                        }}
                    >
                        Kê đơn ngay
                    </Button>
                </div>
            )}

            {/* Two-column layout */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, alignItems: 'start' }}>

                {/* ── LEFT: LIS Table ─────────────────────────────────────── */}
                <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', overflow: 'hidden' }}>
                    <div style={{ padding: '10px 16px', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ fontWeight: 700, fontSize: 13, color: '#374151', display: 'flex', alignItems: 'center', gap: 6 }}>
                            <ExperimentOutlined style={{ color: '#6366f1' }} />
                            Xét nghiệm (LIS)
                        </div>
                        <Tooltip title="In kết quả">
                            <Button type="text" size="small" icon={<PrinterOutlined />} style={{ color: '#9ca3af' }} />
                        </Tooltip>
                    </div>

                    {loadingLis ? (
                        <div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>
                    ) : labRows.length === 0 ? (
                        <div style={{ padding: 24, textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
                            Chưa có kết quả xét nghiệm.
                        </div>
                    ) : (
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                            <thead>
                                <tr style={{ background: '#f9fafb' }}>
                                    {['TÊN XÉT NGHIỆM', 'KẾT QUẢ', 'ĐƠN VỊ', 'CSBT'].map(h => (
                                        <th key={h} style={{ padding: '7px 12px', textAlign: 'left', fontSize: 11, fontWeight: 700, color: '#6b7280', letterSpacing: '0.04em', borderBottom: '1px solid #f0f0f0' }}>
                                            {h}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {labRows.map((row, idx) => {
                                    const color = flagColor(row);
                                    return (
                                        <tr key={idx} style={{ borderBottom: '1px solid #f9fafb' }}>
                                            <td style={{ padding: '8px 12px', color: row.is_abnormal ? color : '#374151', fontWeight: row.is_abnormal ? 600 : 400 }}>
                                                {row.name}
                                            </td>
                                            <td style={{ padding: '8px 12px' }}>
                                                <span style={{ color: color || '#374151', fontWeight: row.is_abnormal ? 700 : 400 }}>
                                                    {row.value} {flagArrow(row)}
                                                </span>
                                            </td>
                                            <td style={{ padding: '8px 12px', color: '#6b7280' }}>{row.unit}</td>
                                            <td style={{ padding: '8px 12px', color: '#9ca3af', fontSize: 12 }}>{row.ref_range}</td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    )}
                </div>

                {/* ── RIGHT: RIS / PACS Cards ─────────────────────────────── */}
                <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', overflow: 'hidden' }}>
                    <div style={{ padding: '10px 16px', borderBottom: '1px solid #f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                        <div style={{ fontWeight: 700, fontSize: 13, color: '#374151', display: 'flex', alignItems: 'center', gap: 6 }}>
                            <FileImageOutlined style={{ color: '#f59e0b' }} />
                            Chẩn đoán hình ảnh (PACS)
                        </div>
                        {imaging.length > 0 && (
                            <Tag color="blue" style={{ margin: 0, fontSize: 12 }}>{imaging.length} phiếu</Tag>
                        )}
                    </div>

                    {loadingRis ? (
                        <div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>
                    ) : imaging.length === 0 ? (
                        <div style={{ padding: 24, textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
                            Chưa có kết quả chẩn đoán hình ảnh.
                        </div>
                    ) : (
                        <div style={{ maxHeight: 480, overflowY: 'auto', padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: 10 }} className="scrollbar-thin">
                            {imaging.map((img) => (
                                <div key={img.id} style={{
                                    border: `1px solid ${img.is_abnormal ? '#fde68a' : '#e5e7eb'}`,
                                    borderRadius: 10,
                                    background: img.is_abnormal ? '#fffbeb' : '#fafafa',
                                    padding: '12px 14px',
                                }}>
                                    {/* Header row */}
                                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 }}>
                                        <div>
                                            <div style={{ fontWeight: 700, fontSize: 13, color: '#111827' }}>{img.procedure_name}</div>
                                            {(img.order_time || img.doctor_name) && (
                                                <div style={{ fontSize: 11, color: '#9ca3af', marginTop: 2 }}>
                                                    {img.order_time && <span>{dayjs(img.order_time).format('HH:mm')}</span>}
                                                    {img.doctor_name && <span> • Thực hiện: {img.doctor_name}</span>}
                                                </div>
                                            )}
                                        </div>
                                        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                                            {img.is_abnormal && (
                                                <Tooltip title="Kết quả bất thường">
                                                    <WarningOutlined style={{ color: '#f59e0b', fontSize: 16 }} />
                                                </Tooltip>
                                            )}
                                            {img.image_url && (
                                                <Tooltip title="Xem ảnh DICOM">
                                                    <Button size="small" icon={<EyeOutlined />}
                                                        href={img.image_url} target="_blank"
                                                        style={{ fontSize: 11, height: 26, color: '#6366f1', borderColor: '#c7d2fe' }}>
                                                        Xem ảnh
                                                    </Button>
                                                </Tooltip>
                                            )}
                                            {!img.image_url && (
                                                <Button size="small" icon={<EyeOutlined />} disabled
                                                    style={{ fontSize: 11, height: 26 }}>
                                                    Xem ảnh
                                                </Button>
                                            )}
                                        </div>
                                    </div>

                                    {/* Findings */}
                                    {img.findings && (
                                        <div style={{ marginBottom: 6 }}>
                                            <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', letterSpacing: '0.05em', marginBottom: 2 }}>MÔ TẢ:</div>
                                            <div style={{ fontSize: 12, color: '#374151', lineHeight: 1.6 }}>{img.findings}</div>
                                        </div>
                                    )}

                                    {/* Conclusion */}
                                    {img.conclusion && (
                                        <div>
                                            <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', letterSpacing: '0.05em', marginBottom: 2 }}>KẾT LUẬN:</div>
                                            <div style={{ fontSize: 13, fontWeight: 700, color: img.is_abnormal ? '#b45309' : '#166534' }}>{img.conclusion}</div>
                                        </div>
                                    )}
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function ClinicalExamPage() {
    const params = useParams();
    const visitId = params?.visitId as string;
    // key={visitId} forces full remount when switching patients
    return <ClinicalExamContent key={visitId} visitId={visitId} />;
}


function ClinicalExamContent({ visitId }: { visitId: string }) {
    const { message } = App.useApp();
    const router = useRouter();

    const [visit, setVisit] = useState<Visit | null>(null);
    const [record, setRecord] = useState<ClinicalRecord | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [aiLoading, setAiLoading] = useState(false);
    const [triageDrawerOpen, setTriageDrawerOpen] = useState(false);
    const [icdDrawerOpen, setIcdDrawerOpen] = useState(false);
    const [icdCodes, setIcdCodes] = useState<ICDCodeItem[]>([]);
    const [icdSourceWarning, setIcdSourceWarning] = useState<string | null>(null);

    // ── Tab State (controlled) ─────────────────────────────
    const DRAFT_KEY = `clinical-draft-${visitId}`;
    const [activeTab, setActiveTab] = useState<string>(() => {
        try { return localStorage.getItem(`${DRAFT_KEY}-tab`) || '1'; } catch { return '1'; }
    });

    // ── AI Chat State ───────────────────────────────────────
    interface ChatMessage { role: 'user' | 'assistant' | 'system'; content: string; timestamp: Date }
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() => {
        try {
            const saved = localStorage.getItem(`${DRAFT_KEY}-chat`);
            if (saved) {
                const parsed = JSON.parse(saved) as Array<{ role: string; content: string; timestamp: string }>;
                return parsed.map(m => ({ ...m, timestamp: new Date(m.timestamp) })) as ChatMessage[];
            }
        } catch { /* ignore */ }
        return [];
    });
    const [chatInput, setChatInput] = useState('');
    const [chatInitialized, setChatInitialized] = useState<boolean>(() => {
        try { return !!localStorage.getItem(`${DRAFT_KEY}-chat`); } catch { return false; }
    });
    const chatEndRef = useRef<HTMLDivElement>(null);
    const chatSessionRef = useRef(`clinical-${visitId}-${Date.now()}`);

    const [form] = Form.useForm();

    // Listen to form changes to calculate BMI
    const weight = Form.useWatch('weight', form);
    const height = Form.useWatch('height', form);
    const bmi = useMemo(() => {
        if (weight && height) {
            const heightInMeters = height / 100;
            return (weight / (heightInMeters * heightInMeters)).toFixed(1);
        }
        return '--';
    }, [weight, height]);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const visitData = await visitApi.getById(visitId);

            // If the patient is just an ID, fetch it
            if (visitData && typeof visitData.patient === 'string') {
                try {
                    const patientData = await patientApi.getById(visitData.patient);
                    visitData.patient = patientData;
                } catch (e) {
                    console.error('Error fetching patient details:', e);
                }
            }

            setVisit(visitData);

            const recordData = await emrApi.getByVisit(visitId);
            if (recordData) {
                setRecord(recordData);
                form.setFieldsValue({
                    chief_complaint: recordData.chief_complaint,
                    history_of_present_illness: recordData.history_of_present_illness,
                    physical_exam: recordData.physical_exam,
                    final_diagnosis: recordData.final_diagnosis,
                    treatment_plan: recordData.treatment_plan,
                    ...recordData.vital_signs,
                });
            }

            // Tự điền chỉ số sinh hiệu từ bước phân luồng nếu ClinicalRecord chưa có
            const recordVitals = recordData?.vital_signs;
            const hasRecordVitals = recordVitals && Object.values(recordVitals).some((v) => v != null);
            if (!hasRecordVitals && visitData?.vital_signs) {
                const tv = visitData.vital_signs as Record<string, number | undefined>;
                form.setFieldsValue({
                    heart_rate: tv.heart_rate,
                    systolic_bp: tv.bp_systolic,
                    diastolic_bp: tv.bp_diastolic,
                    respiratory_rate: tv.respiratory_rate,
                    temperature: tv.temperature,
                    spo2: tv.spo2,
                    weight: tv.weight,
                    height: tv.height,
                });
            }
        } catch (error) {
            console.error('Error fetching data:', error);
            message.error('Không thể tải thông tin bệnh nhân');
        } finally {
            setLoading(false);
        }
    }, [visitId, form, message]);

    useEffect(() => {
        if (visitId) fetchData();
    }, [visitId, fetchData]);

    // ── Persist draft to localStorage ─────────────────────
    const persistDraft = useCallback(() => {
        try {
            localStorage.setItem(`${DRAFT_KEY}-tab`, activeTab);
            localStorage.setItem(`${DRAFT_KEY}-chat`, JSON.stringify(chatMessages));
            const vals = form.getFieldsValue();
            localStorage.setItem(`${DRAFT_KEY}-form`, JSON.stringify(vals));
        } catch { /* ignore */ }
    }, [DRAFT_KEY, activeTab, chatMessages, form]);

    // Restore form draft after data load (only if record hasn't already populated it)
    useEffect(() => {
        if (loading) return;
        try {
            const savedForm = localStorage.getItem(`${DRAFT_KEY}-form`);
            if (savedForm) {
                const parsed = JSON.parse(savedForm);
                // Only restore draft fields that the server record hasn't set
                const current = form.getFieldsValue();
                const merged: Record<string, unknown> = {};
                Object.keys(parsed).forEach(k => {
                    if (current[k] == null && parsed[k] != null) merged[k] = parsed[k];
                });
                if (Object.keys(merged).length > 0) form.setFieldsValue(merged);
            }
        } catch { /* ignore */ }
    }, [loading, DRAFT_KEY, form]);

    const handleSave = async (values: any) => {
        setSaving(true);
        try {
            const vitalSigns: VitalSigns = {
                temperature: values.temperature,
                systolic_bp: values.systolic_bp,
                diastolic_bp: values.diastolic_bp,
                heart_rate: values.heart_rate,
                respiratory_rate: values.respiratory_rate,
                spo2: values.spo2,
                weight: values.weight,
                height: values.height,
            };

            const data = {
                chief_complaint: values.chief_complaint,
                history_of_present_illness: values.history_of_present_illness,
                physical_exam: values.physical_exam,
                final_diagnosis: values.final_diagnosis,
                treatment_plan: values.treatment_plan,
                vital_signs: vitalSigns,
            };

            if (record) {
                await emrApi.update(record.id, data);
            } else {
                const newRecord = await emrApi.create({
                    visit: visitId,
                    chief_complaint: data.chief_complaint,
                    vital_signs: vitalSigns,
                });
                setRecord(newRecord);
            }
            // Lưu state vào localStorage sau khi lưu server thành công
            persistDraft();
            message.success('Đã lưu nháp hồ sơ');
        } catch (error) {
            console.error('Error saving:', error);
            message.error('Không thể lưu hồ sơ');
        } finally {
            setSaving(false);
        }
    };

    // ── AI Chat Functions ─────────────────────────────────────
    const buildInitialPrompt = useCallback(() => {
        const p = typeof visit?.patient === 'object' ? visit.patient as Patient : null;
        const name = p?.full_name || `${p?.last_name || ''} ${p?.first_name || ''}`.trim() || 'BN';
        const age = p?.date_of_birth ? dayjs().diff(dayjs(p.date_of_birth), 'year') : 'N/A';
        const tv = visit?.vital_signs as Record<string, number | undefined> | undefined;
        const vals = form.getFieldsValue();

        const deptName = visit?.confirmed_department_detail?.name || 'Không rõ';

        return `[CLINICAL_ANALYSIS] Tôi là bác sĩ đang trực tiếp khám bệnh nhân tại ${deptName}. Bệnh nhân HIỆN ĐANG NẰM TẠI ${deptName}.
QUY TẮC TRẢ LỜI:
- Bệnh nhân ĐÃ Ở ${deptName} rồi, KHÔNG nói "cần theo dõi tại ${deptName}" hay "cần chuyển đến ${deptName}" vì đó là thừa.
- Chỉ tập trung vào chẩn đoán, xử trí cụ thể tại khoa này. Đưa ra y lệnh, thuốc, và theo dõi cụ thể.
- KHÔNG đề xuất chuyển khoa trừ khi phát hiện bệnh lý ngoài chuyên khoa và nêu rõ lý do.
- KHÔNG dùng mã code dạng [URGENT_MODERATE], [CODE_RED] trong câu trả lời.

══ THÔNG TIN BỆNH NHÂN ══
Họ tên: ${name} | Tuổi: ${age} | Giới: ${p?.gender === 'M' ? 'Nam' : 'Nữ'}
BHYT: ${p?.insurance_number || 'Không'}

══ SINH HIỆU (TẠI PHÂN LUỒNG) ══
Mạch: ${tv?.heart_rate ?? '--'} l/p | HA: ${tv?.bp_systolic ?? '--'}/${tv?.bp_diastolic ?? '--'} mmHg
SpO2: ${tv?.spo2 ?? '--'}% | Nhịp thở: ${tv?.respiratory_rate ?? '--'} l/p

══ LÝ DO KHÁM ══
${vals.chief_complaint || visit?.chief_complaint || 'Chưa rõ'}

══ TÓM TẮT BỆNH ÁN ══
${visit?.pre_triage_summary?.substring(0, 600) || 'Không có'}

══ QUYẾT ĐỊNH PHÂN LUỒNG ══
Mã: ${visit?.triage_code || 'N/A'} → Khoa: ${visit?.confirmed_department_detail?.name || 'N/A'}
Độ tin cậy: ${visit?.triage_confidence ?? 'N/A'}%
Ý kiến AI: ${visit?.triage_ai_response?.substring(0, 400) || 'Không có'}

══ CƠ SỞ PHÂN LUỒNG ══
${visit?.triage_key_factors?.join('\n') || 'Không có'}

══ LƯU Ý TỪ AI ══
${visit?.triage_hints || 'Không có'}

══ BỆNH SỬ ══
${vals.history_of_present_illness || 'Chưa khai thác'}

══ KHÁM LÂM SÀNG ══
${vals.physical_exam || 'Chưa khám'}

══ YÊU CẦU ══
1. Đưa ra 3-5 chẩn đoán phân biệt xếp theo khả năng (%).
2. Với MỖI chẩn đoán, đưa ra mã ICD-10 gồm:
   - Main ICD (mã chính) kèm tỷ lệ chính xác (%)
   - Sub ICD (mã phụ nếu có) kèm tỷ lệ chính xác (%)
3. Chỉ định cận lâm sàng cần thiết.
4. Hướng xử trí ban đầu.
5. Điểm cần khai thác thêm từ bệnh nhân.
6. Cảnh báo nếu có dấu hiệu nguy hiểm.`;
    }, [visit, form]);

    const sendChatMessage = useCallback(async (text: string, isSystem = false) => {
        if (!visitId || !text.trim()) return;

        const userMsg: ChatMessage = { role: isSystem ? 'system' : 'user', content: text.trim(), timestamp: new Date() };
        setChatMessages(prev => [...prev, userMsg]);
        setAiLoading(true);
        try {
            const result = await aiApi.chat(visitId, text.trim(), chatSessionRef.current);
            const rawText = result?.message || result?.response || JSON.stringify(result);
            // Strip [CODE_*] and [ICD_CODE] bracket tags from display text
            const aiText = rawText.replace(/\[(?:URGENT_\w+|CODE_\w+|ICD_CODE)\]\s*/g, '');
            const aiMsg: ChatMessage = { role: 'assistant', content: aiText, timestamp: new Date() };
            setChatMessages(prev => [...prev, aiMsg]);

            // Extract ICD codes from structured response or parse from text
            const extractedCodes: ICDCodeItem[] = [];
            console.log('[ICD-DEBUG] result keys:', Object.keys(result || {}));
            console.log('[ICD-DEBUG] result.icd_codes:', result?.icd_codes);
            if (result?.icd_codes && Array.isArray(result.icd_codes)) {
                extractedCodes.push(...result.icd_codes.map((c: Record<string, unknown>) => ({
                    code: String(c.code || ''),
                    name: String(c.name || ''),
                    confidence: Number(c.confidence || 0.5),
                    type: (c.type === 'main' || c.type === 'sub') ? c.type : 'sub' as const,
                    in_system: c.in_system as boolean | null ?? null,
                    system_name: c.system_name as string | null ?? null,
                })));
                console.log('[ICD-DEBUG] Extracted from structured:', extractedCodes.length);
            } else {
                // Fallback: parse ICD codes from text (format: code - name, code (name), or code | name)
                const icdRegex = /([A-Z]\d{2}(?:\.\d{1,2}?))\s*[\(\-–:|]\s*([^)\n|,]{3,60})/g;
                let m;
                while ((m = icdRegex.exec(rawText)) !== null) {
                    const letter = m[1][0];
                    if (letter >= 'A' && letter <= 'Z') {
                        extractedCodes.push({
                            code: m[1],
                            name: m[2].trim().replace(/[)\|]$/, '').trim(),
                            type: extractedCodes.length === 0 ? 'main' : 'sub',
                            confidence: 0.6,
                            in_system: null,
                            system_name: null,
                        });
                    }
                }
                console.log('[ICD-DEBUG] Extracted from regex fallback:', extractedCodes.length);
            }
            if (extractedCodes.length > 0) {
                setIcdCodes(prev => {
                    // Merge, keeping latest confidence for duplicate codes
                    const codeMap = new Map(prev.map(c => [c.code, c]));
                    extractedCodes.forEach(c => codeMap.set(c.code, c));
                    return Array.from(codeMap.values());
                });
            }
            // Capture ICD source warning from backend
            if (result?.icd_source_warning) {
                setIcdSourceWarning(String(result.icd_source_warning));
            }
        } catch {
            const errMsg: ChatMessage = { role: 'assistant', content: '❌ Lỗi kết nối AI. Vui lòng thử lại.', timestamp: new Date() };
            setChatMessages(prev => [...prev, errMsg]);
        } finally {
            setAiLoading(false);
        }
    }, [visitId]);

    // Auto-initialize chat khi visit data đã load
    const initializeChat = useCallback(async () => {
        if (chatInitialized || !visit || loading) return;
        setChatInitialized(true);
        // New session each time
        chatSessionRef.current = `clinical-${visitId}-${Date.now()}`;
        const prompt = buildInitialPrompt();
        await sendChatMessage(prompt, true);
    }, [chatInitialized, visit, loading, buildInitialPrompt, sendChatMessage]);

    // Scroll to bottom khi có tin nhắn mới
    useEffect(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [chatMessages]);

    const patient = typeof visit?.patient === 'object' ? visit.patient as Patient : null;

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Spin size="large" />
                <div className="mt-2 text-gray-500 ml-2">Đang tải dữ liệu bệnh án...</div>
            </div>
        );
    }


    const triageCodeMap: Record<string, { label: string; color: string }> = {
        CODE_RED: { label: 'Cấp cứu', color: 'red' },
        CODE_ORANGE: { label: 'Rất khẩn cấp', color: 'orange' },
        CODE_YELLOW: { label: 'Khẩn cấp', color: 'gold' },
        CODE_GREEN: { label: 'Ít khẩn cấp', color: 'green' },
        CODE_BLUE: { label: 'Không khẩn cấp', color: 'blue' },
    };
    const triageInfo = visit?.triage_code ? triageCodeMap[visit.triage_code] : null;
    const triageVitals = visit?.vital_signs as Record<string, number | undefined> | undefined;

    const PatientHeader = () => {
        if (!patient) return null;
        return (
            <div className="flex justify-between items-center mb-4 bg-white p-4 rounded-xl shadow-sm border border-gray-100">
                <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-blue-50 text-blue-500 rounded-full flex items-center justify-center text-xl">
                        <UserOutlined />
                    </div>
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <span className="text-xl font-bold text-gray-800">{patient.full_name || `${patient.last_name || ''} ${patient.first_name || ''}`}</span>
                            <Tag className="m-0 bg-gray-100 text-gray-600 border-0">{patient.patient_code}</Tag>
                            <Tag color="blue" className="m-0 border-0 text-blue-600 bg-blue-50 font-medium">BHYT</Tag>
                        </div>
                        <div className="text-gray-500 text-sm flex items-center gap-2">
                            <span>Tuổi: <strong className="text-gray-700">{patient.date_of_birth ? dayjs().diff(dayjs(patient.date_of_birth), 'year') : '--'}</strong></span>
                            <span className="text-gray-300">|</span>
                            <span>Giới tính: <strong className="text-gray-700">{patient.gender === 'M' ? 'Nam' : 'Nữ'}</strong></span>
                        </div>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    {record?.ai_suggestion_json && !!(record.ai_suggestion_json.drug_interactions || record.ai_suggestion_json.allergy_warnings) && (
                        <div className="flex items-center gap-3 bg-red-50 px-3 py-2 rounded-lg border border-red-100">
                            <WarningOutlined className="text-red-500 text-lg" />
                            <div>
                                <div className="text-red-600 font-semibold text-sm">Cảnh báo</div>
                                <div className="text-red-500 text-xs">Phát hiện nguy cơ sốc phản vệ / tương tác thuốc</div>
                            </div>
                        </div>
                    )}

                    {icdCodes.length > 0 && (
                        <Tooltip title="Xem mã ICD-10 đề xuất">
                            <Badge count={icdCodes.length} size="small" offset={[-2, 2]}>
                                <Button
                                    icon={<BarcodeOutlined />}
                                    onClick={() => setIcdDrawerOpen(true)}
                                    className="h-10 border-purple-200 text-purple-600 hover:bg-purple-50 font-medium"
                                >
                                    ICD Đề xuất
                                </Button>
                            </Badge>
                        </Tooltip>
                    )}

                    {visit?.triage_code && (
                        <Tooltip title="Xem tóm tắt phân luồng">
                            <Button
                                icon={<FundViewOutlined />}
                                onClick={() => setTriageDrawerOpen(true)}
                                className="h-10 border-blue-200 text-blue-600 hover:bg-blue-50 font-medium"
                            >
                                Phân luồng
                            </Button>
                        </Tooltip>
                    )}
                </div>
            </div>
        );
    };

    /* ── Triage Summary Drawer ──────────────────────────────── */
    const TriageDrawer = () => (
        <Drawer
            title={<div className="flex items-center gap-2 font-bold"><FundViewOutlined className="text-blue-500" /> Tóm tắt phân luồng</div>}
            placement="right"
            width={520}
            open={triageDrawerOpen}
            onClose={() => setTriageDrawerOpen(false)}
        >
            {/* 1. Quyết định phân luồng */}
            <div className="mb-5">
                <div className="text-xs font-bold text-gray-400 tracking-wider mb-2">QUYẾT ĐỊNH PHÂN LUỒNG</div>
                <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                    <div className="flex items-center gap-2">
                        <span className="text-gray-500 text-sm">Mã phân luồng:</span>
                        {triageInfo ? <Tag color={triageInfo.color} className="m-0 font-medium">{triageInfo.label} ({visit?.triage_code})</Tag> : <Tag className="m-0">{visit?.triage_code || '--'}</Tag>}
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="text-gray-500 text-sm">Khoa tiếp nhận:</span>
                        <Tag color="blue" className="m-0 font-medium">{visit?.confirmed_department_detail?.name || '--'}</Tag>
                    </div>
                    {visit?.recommended_department_detail && visit.recommended_department_detail.id !== visit.confirmed_department_detail?.id && (
                        <div className="flex items-center gap-2">
                            <span className="text-gray-500 text-sm">AI đề xuất:</span>
                            <Tag className="m-0">{visit.recommended_department_detail.name}</Tag>
                        </div>
                    )}
                    <div className="flex items-center gap-2">
                        <span className="text-gray-500 text-sm">Phương thức:</span>
                        <span className="text-sm font-medium">{visit?.triage_method === 'AI' ? '🤖 AI phân luồng' : '👤 Thủ công'}</span>
                    </div>
                    {visit?.triage_confidence != null && (
                        <div className="flex items-center gap-2">
                            <span className="text-gray-500 text-sm">Độ tin cậy:</span>
                            <Progress percent={visit.triage_confidence} size="small" className="w-32 m-0" />
                        </div>
                    )}
                </div>
            </div>

            <Divider className="my-3" />

            {/* 2. Chỉ số sinh hiệu tại phân luồng */}
            {triageVitals && (
                <div className="mb-5">
                    <div className="text-xs font-bold text-gray-400 tracking-wider mb-2">CHỈ SỐ SINH HIỆU (TẠI PHÂN LUỒNG)</div>
                    <Descriptions column={2} size="small" bordered className="[&_.ant-descriptions-item-label]:bg-gray-50">
                        {triageVitals.heart_rate != null && <Descriptions.Item label="Mạch">{triageVitals.heart_rate} l/p</Descriptions.Item>}
                        {triageVitals.bp_systolic != null && <Descriptions.Item label="Huyết áp">{triageVitals.bp_systolic}/{triageVitals.bp_diastolic} mmHg</Descriptions.Item>}
                        {triageVitals.spo2 != null && <Descriptions.Item label="SpO2">{triageVitals.spo2}%</Descriptions.Item>}
                        {triageVitals.respiratory_rate != null && <Descriptions.Item label="Nhịp thở">{triageVitals.respiratory_rate} l/p</Descriptions.Item>}
                        {triageVitals.temperature != null && <Descriptions.Item label="Nhiệt độ">{triageVitals.temperature}°C</Descriptions.Item>}
                    </Descriptions>
                </div>
            )}

            <Divider className="my-3" />

            {/* 3. Lý do phân luồng (AI response) */}
            {visit?.triage_ai_response && (
                <div className="mb-5">
                    <div className="text-xs font-bold text-gray-400 tracking-wider mb-2">Ý KIẾN AI PHÂN LUỒNG</div>
                    <div className="bg-blue-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed border border-blue-100">
                        {visit.triage_ai_response}
                    </div>
                </div>
            )}

            {/* 4. Key factors */}
            {visit?.triage_key_factors && visit.triage_key_factors.length > 0 && (
                <div className="mb-5">
                    <div className="text-xs font-bold text-gray-400 tracking-wider mb-2">CƠ SỞ PHÂN LUỒNG</div>
                    <div className="space-y-2">
                        {visit.triage_key_factors.map((factor, idx) => (
                            <div key={idx} className="bg-amber-50 rounded-lg p-3 text-sm text-amber-900 border border-amber-100 leading-relaxed">
                                <WarningOutlined className="text-amber-500 mr-2" />
                                {factor}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            <Divider className="my-3" />

            {/* 5. Tóm tắt bệnh án (pre_triage_summary) */}
            {visit?.pre_triage_summary && (
                <div className="mb-5">
                    <div className="text-xs font-bold text-gray-400 tracking-wider mb-2">TÓM TẮT BỆNH ÁN (TRƯỚC PHÂN LUỒNG)</div>
                    <div className="bg-gray-50 rounded-lg p-4 text-sm text-gray-700 whitespace-pre-wrap leading-relaxed border border-gray-200" style={{ maxHeight: 400, overflowY: 'auto' }}>
                        {visit.pre_triage_summary}
                    </div>
                </div>
            )}

            {/* 6. Triage hints */}
            {visit?.triage_hints && (
                <div className="mb-5">
                    <div className="text-xs font-bold text-gray-400 tracking-wider mb-2">LƯU Ý TỪ AI</div>
                    <Alert type="warning" showIcon message={visit.triage_hints} className="text-sm" />
                </div>
            )}
        </Drawer>
    );

    /* ── ICD Code Drawer ──────────────────────────────────── */
    const ICDDrawer = () => {
        const hasExternal = icdCodes.some(c => c.in_system === false);
        const mainCodes = icdCodes.filter(c => c.type === 'main').sort((a, b) => b.confidence - a.confidence);
        const subCodes = icdCodes.filter(c => c.type === 'sub').sort((a, b) => b.confidence - a.confidence);

        const ICDCard = ({ icd, idx }: { icd: ICDCodeItem; idx: number }) => {
            const pct = Math.round(icd.confidence * 100);
            const isMain = icd.type === 'main';
            const isInSystem = icd.in_system === true;
            const isExternal = icd.in_system === false;
            return (
                <div
                    key={`${icd.code}-${idx}`}
                    className={`rounded-lg p-3 border ${isExternal
                        ? 'border-orange-200 bg-orange-50/30'
                        : isMain
                            ? 'border-purple-200 bg-purple-50/50'
                            : 'border-gray-200 bg-gray-50/50'
                        }`}
                >
                    <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-1.5 flex-wrap">
                            <Tag
                                color={isMain ? 'purple' : 'default'}
                                className="m-0 font-mono font-bold text-xs"
                            >
                                {icd.code}
                            </Tag>
                            {isInSystem && (
                                <Tooltip title="Có trong danh mục bệnh viện">
                                    <Tag color="green" className="m-0 text-[10px]" bordered={false}>✅ HT</Tag>
                                </Tooltip>
                            )}
                            {isExternal && (
                                <Tooltip title="KHÔNG có trong danh mục — nguồn bên ngoài">
                                    <Tag color="orange" className="m-0 text-[10px]" bordered={false}>⚠ Ngoài</Tag>
                                </Tooltip>
                            )}
                        </div>
                        <Text
                            strong
                            className={`text-xs ${pct >= 80 ? 'text-green-600'
                                : pct >= 60 ? 'text-orange-500'
                                    : 'text-red-500'
                                }`}
                        >
                            {pct}%
                        </Text>
                    </div>
                    <Text className="text-xs text-gray-700 block mb-1">{icd.name}</Text>
                    {isInSystem && icd.system_name && icd.system_name !== icd.name && (
                        <Text className="text-[10px] text-green-600 block mb-1">HT: {icd.system_name}</Text>
                    )}
                    <Progress
                        percent={pct}
                        size="small"
                        showInfo={false}
                        strokeColor={pct >= 80 ? '#52c41a' : pct >= 60 ? '#faad14' : '#ff4d4f'}
                    />
                </div>
            );
        };

        return (
            <Drawer
                title={<div className="flex items-center gap-2 font-bold text-sm"><BarcodeOutlined className="text-purple-500" /> Mã ICD-10 Đề Xuất</div>}
                placement="right"
                width={420}
                open={icdDrawerOpen}
                onClose={() => setIcdDrawerOpen(false)}
            >
                {icdCodes.length === 0 ? (
                    <div className="text-center py-10 text-gray-400 text-sm">
                        Chưa có mã ICD-10 đề xuất. Hãy nhấn &quot;Bắt đầu&quot; để AI phân tích.
                    </div>
                ) : (
                    <div className="space-y-3">
                        {/* Compact info bar */}
                        <div className="flex items-center gap-2 text-xs text-gray-500 bg-blue-50 rounded px-2.5 py-1.5 border border-blue-100">
                            <InfoCircleOutlined className="text-blue-400" />
                            <span>AI đề xuất — bác sĩ cần xác nhận trước khi lưu hồ sơ.</span>
                        </div>

                        {/* Compact warning for external codes */}
                        {(hasExternal || icdSourceWarning) && (
                            <div className="flex items-start gap-2 text-xs text-orange-700 bg-orange-50 rounded px-2.5 py-1.5 border border-orange-100">
                                <WarningOutlined className="text-orange-400 mt-0.5" />
                                <span>{icdSourceWarning || 'Một số mã không có trong danh mục bệnh viện — AI dùng nguồn bên ngoài.'}</span>
                            </div>
                        )}

                        {/* Main ICD Section */}
                        {mainCodes.length > 0 && (
                            <div>
                                <div className="text-[11px] font-bold text-purple-600 tracking-wider mb-2 uppercase">
                                    Chẩn đoán chính ({mainCodes.length})
                                </div>
                                <div className="space-y-2">
                                    {mainCodes.map((icd, idx) => (
                                        <ICDCard key={`main-${icd.code}-${idx}`} icd={icd} idx={idx} />
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Divider */}
                        {mainCodes.length > 0 && subCodes.length > 0 && (
                            <Divider className="my-2" />
                        )}

                        {/* Sub ICD Section */}
                        {subCodes.length > 0 && (
                            <div>
                                <div className="text-[11px] font-bold text-gray-400 tracking-wider mb-2 uppercase">
                                    Chẩn đoán phụ / kèm theo ({subCodes.length})
                                </div>
                                <div className="space-y-2">
                                    {subCodes.map((icd, idx) => (
                                        <ICDCard key={`sub-${icd.code}-${idx}`} icd={icd} idx={idx} />
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </Drawer>
        );
    };

    return (
        <Form form={form} layout="vertical" onFinish={handleSave} className="h-full flex flex-col overflow-hidden min-h-0">
            <PatientHeader />
            <TriageDrawer />
            <ICDDrawer />

            <div className="flex-1 min-h-0 flex gap-4">
                {/* Left: Tabs with form content */}
                <div className="flex-[2] min-w-0 flex flex-col min-h-0">
                    <Tabs
                        activeKey={activeTab}
                        onChange={(key) => { setActiveTab(key); try { localStorage.setItem(`${DRAFT_KEY}-tab`, key); } catch { /* ignore */ } }}
                        className="bg-white rounded-xl shadow-sm border border-gray-100 pt-2 flex-1 flex flex-col min-h-0 overflow-hidden [&>.ant-tabs-nav]:px-4 [&>.ant-tabs-content-holder]:flex-1 [&>.ant-tabs-content-holder]:min-h-0 [&>.ant-tabs-content-holder]:overflow-hidden [&>.ant-tabs-content-holder]:bg-gray-50/50 [&_.ant-tabs-content]:h-full [&_.ant-tabs-tabpane]:h-full"
                        items={[
                            {
                                key: '1',
                                label: <div className="py-1 text-blue-600 font-semibold flex items-center gap-2"><MedicineBoxOutlined /> 1. Khám bệnh</div>,
                                children: (
                                    <div className="h-full overflow-y-auto p-4 pt-2 pb-10" style={{ scrollbarWidth: 'thin' }}>
                                        <div className="space-y-4">
                                            <Card
                                                title={<Space><HeartOutlined className="text-red-400 opacity-80" /> <span className="text-[13px] font-bold text-gray-700 tracking-wide">CHỈ SỐ SINH HIỆU (VITALS)</span></Space>}
                                                className="shadow-sm border-gray-200 rounded-xl overflow-hidden [&>.ant-card-head]:border-b-0 [&>.ant-card-head]:min-h-[48px] [&>.ant-card-body]:pt-0"
                                            >
                                                <Row gutter={[16, 12]}>
                                                    <Col span={6}><Form.Item name="heart_rate" label="Mạch (l/p)" className="mb-0"><InputNumber min={0} className="w-full bg-gray-50" controls={false} /></Form.Item></Col>
                                                    <Col span={6}><Form.Item name="systolic_bp" label="HA tâm thu" className="mb-0"><InputNumber min={50} max={300} className="w-full bg-gray-50" controls={false} placeholder="120" /></Form.Item></Col>
                                                    <Col span={6}><Form.Item name="diastolic_bp" label="HA tâm trương" className="mb-0"><InputNumber min={30} max={200} className="w-full bg-gray-50" controls={false} placeholder="80" /></Form.Item></Col>
                                                    <Col span={6}><Form.Item name="temperature" label="Nhiệt độ (°C)" className="mb-0"><InputNumber min={35} max={42} step={0.1} className="w-full bg-gray-50" controls={false} /></Form.Item></Col>
                                                    <Col span={6}><Form.Item name="spo2" label="SpO2 (%)" className="mb-0"><InputNumber min={70} max={100} className="w-full bg-gray-50" controls={false} /></Form.Item></Col>
                                                    <Col span={6}><Form.Item name="respiratory_rate" label="Nhịp thở (l/p)" className="mb-0"><InputNumber min={8} max={40} className="w-full bg-gray-50" controls={false} /></Form.Item></Col>
                                                    <Col span={6}><Form.Item name="weight" label="Cân nặng (kg)" className="mb-0"><InputNumber min={1} max={300} step={0.1} className="w-full bg-gray-50" controls={false} /></Form.Item></Col>
                                                    <Col span={6}><Form.Item name="height" label="Chiều cao (cm)" className="mb-0"><InputNumber min={30} max={250} className="w-full bg-gray-50" controls={false} /></Form.Item></Col>
                                                    <Col span={6}><Form.Item label="BMI" className="mb-0"><Input value={bmi} readOnly className="w-full bg-gray-100 font-medium" /></Form.Item></Col>
                                                </Row>
                                            </Card>
                                            <Card
                                                title={<Space><FileTextOutlined className="text-blue-400 opacity-80" /> <span className="text-[13px] font-bold text-gray-700 tracking-wide">HỎI BỆNH (SUBJECTIVE)</span></Space>}
                                                className="shadow-sm border-gray-200 rounded-xl overflow-hidden [&>.ant-card-head]:border-b-0 [&>.ant-card-head]:min-h-[48px] [&>.ant-card-body]:pt-0"
                                            >
                                                <Form.Item name="chief_complaint" label="Lý do vào viện" className="mb-3"><Input placeholder="Nhập lý do vào viện..." className="bg-gray-50" /></Form.Item>
                                                <Form.Item name="history_of_present_illness" label="Bệnh sử" className="mb-0"><TextArea rows={4} placeholder="Mô tả quá trình diễn biến bệnh..." className="bg-gray-50" /></Form.Item>
                                            </Card>
                                            <Card
                                                title={<Space><MedicineBoxOutlined className="text-green-500 opacity-80" /> <span className="text-[13px] font-bold text-gray-700 tracking-wide">KHÁM LÂM SÀNG (OBJECTIVE)</span></Space>}
                                                className="shadow-sm border-gray-200 rounded-xl overflow-hidden [&>.ant-card-head]:border-b-0 [&>.ant-card-head]:min-h-[48px] [&>.ant-card-body]:pt-0"
                                            >
                                                <Row gutter={16}>
                                                    <Col span={12}><Form.Item name="physical_exam" label="Khám toàn thân" className="mb-0"><TextArea rows={4} placeholder="Tỉnh táo, tiếp xúc tốt..." className="bg-gray-50" /></Form.Item></Col>
                                                    <Col span={12}><Form.Item name="body_organs" label="Khám bộ phận (Tim, Phổi, v.v...)" className="mb-0"><TextArea rows={4} placeholder="Tim đều, phổi trong..." className="bg-gray-50" /></Form.Item></Col>
                                                </Row>
                                            </Card>
                                        </div>
                                    </div>
                                )
                            },
                            {
                                key: '2',
                                label: <div className="px-4 py-1 text-gray-500 flex items-center gap-2"><ExperimentOutlined /> 2. Chỉ định CLS</div>,
                                children: <CLSOrderTab visitId={visitId} patientId={patient?.id} />
                            },
                            {
                                key: '3',
                                label: <div className="px-4 py-1 text-gray-500 flex items-center gap-2"><FileTextOutlined /> 3. Kết quả</div>,
                                children: <KetQuaTab visitId={visitId} onGoToDiagnosis={() => { setActiveTab('4'); try { localStorage.setItem(`${DRAFT_KEY}-tab`, '4'); } catch { /* ignore */ } }} />,
                            },
                            {
                                key: '4',
                                label: <div className="px-4 py-1 text-gray-500 flex items-center gap-2"><MedicineBoxOutlined /> 4. Chẩn đoán & Kê đơn</div>,
                                children: <div className="text-center py-10 text-gray-400 h-full overflow-y-auto">Chưa nhập chẩn đoán.</div>
                            }
                        ]}
                    />
                </div>

                {/* Right: AI Chat — always visible regardless of active tab */}
                <div className="w-[340px] shrink-0 flex flex-col min-h-0">
                    <div className="bg-[#f8faff] border border-blue-100 rounded-xl shadow-sm flex flex-col h-full min-h-0">
                        <div className="flex items-center justify-between px-4 py-3 border-b border-blue-100 shrink-0">
                            <div className="flex items-center gap-2 text-blue-700 font-bold tracking-wide text-sm">
                                <RobotOutlined className="text-base" />
                                AI TRỢ LÝ LÂM SÀNG
                            </div>
                            {!chatInitialized && (
                                <Button size="small" type="primary" icon={<RobotOutlined />} onClick={initializeChat}
                                    className="bg-indigo-600 border-0 text-xs font-medium">
                                    Bắt đầu
                                </Button>
                            )}
                        </div>
                        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-3 min-h-0" style={{ scrollbarWidth: 'thin' }}>
                            {chatMessages.length === 0 && (
                                <div className="flex flex-col items-center justify-center h-full text-gray-400 text-sm gap-2 py-10">
                                    <RobotOutlined className="text-3xl text-blue-300" />
                                    <span>Nhấn <strong>Bắt đầu</strong> để AI phân tích bệnh án</span>
                                    <span className="text-xs text-gray-300">AI sẽ nạp tóm tắt phân luồng và đưa ra ICD-10</span>
                                </div>
                            )}
                            {chatMessages.filter(m => m.role !== 'system').map((msg, idx) => (
                                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[92%] rounded-xl px-3 py-2.5 text-sm leading-relaxed ${msg.role === 'user'
                                        ? 'bg-blue-600 text-white rounded-br-sm'
                                        : 'bg-white border border-gray-200 text-gray-700 rounded-bl-sm shadow-sm prose prose-sm max-w-none'
                                        }`}>
                                        {msg.role === 'assistant' ? (
                                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                                        ) : (
                                            <div className="whitespace-pre-wrap break-words">{msg.content}</div>
                                        )}
                                        <div className={`text-[10px] mt-1 ${msg.role === 'user' ? 'text-blue-200' : 'text-gray-300'}`}>
                                            {dayjs(msg.timestamp).format('HH:mm')}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {aiLoading && (
                                <div className="flex justify-start">
                                    <div className="bg-white border border-gray-200 rounded-xl rounded-bl-sm px-4 py-3 shadow-sm">
                                        <div className="flex items-center gap-2 text-blue-500 text-sm">
                                            <Spin size="small" />
                                            <span>Đang suy nghĩ...</span>
                                        </div>
                                    </div>
                                </div>
                            )}
                            <div ref={chatEndRef} />
                        </div>
                        <div className="border-t border-blue-100 px-3 py-2.5 shrink-0">
                            <div className="flex gap-2">
                                <Input.TextArea
                                    value={chatInput}
                                    onChange={e => setChatInput(e.target.value)}
                                    placeholder="Hỏi về chẩn đoán, mã ICD..."
                                    autoSize={{ minRows: 1, maxRows: 3 }}
                                    className="text-sm bg-white"
                                    onPressEnter={e => {
                                        if (!e.shiftKey) {
                                            e.preventDefault();
                                            if (chatInput.trim() && !aiLoading) {
                                                sendChatMessage(chatInput);
                                                setChatInput('');
                                            }
                                        }
                                    }}
                                />
                                <Button
                                    type="primary"
                                    icon={<ArrowRightOutlined />}
                                    disabled={!chatInput.trim() || aiLoading}
                                    onClick={() => { sendChatMessage(chatInput); setChatInput(''); }}
                                    className="bg-indigo-600 border-0 shrink-0 self-end"
                                />
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Bottom Actions — Dynamic based on active tab */}
            <div className="bg-white border-t border-gray-200 p-4 mt-4 flex justify-center gap-4 shrink-0">
                <Button
                    size="large"
                    className="w-[140px] font-medium"
                    icon={<SaveOutlined />}
                    onClick={() => { persistDraft(); form.submit(); }}
                    loading={saving}
                >
                    Lưu nháp
                </Button>

                {activeTab === '4' ? (
                    /* Tab 4: Hoàn Tất Khám */
                    <Button
                        type="primary"
                        size="large"
                        className="w-[200px] font-medium bg-green-600 border-green-600 hover:bg-green-500"
                        icon={<CheckCircleOutlined />}
                        onClick={async () => {
                            await form.validateFields().catch(() => null);
                            form.submit();
                            message.success('Hoàn tất khám bệnh!');
                        }}
                    >
                        Hoàn Tất Khám
                    </Button>
                ) : (
                    /* Tabs 1→2→3: Tiếp tục tới tab kế tiếp */
                    <Button
                        type="primary"
                        size="large"
                        className="w-[220px] font-medium"
                        icon={<ArrowRightOutlined />}
                        iconPosition="end"
                        onClick={() => {
                            const next = String(Number(activeTab) + 1);
                            setActiveTab(next);
                            try { localStorage.setItem(`${DRAFT_KEY}-tab`, next); } catch { /* ignore */ }
                        }}
                    >
                        {activeTab === '1' && 'Tiếp tục bước 2'}
                        {activeTab === '2' && 'Tiếp tục bước 3'}
                        {activeTab === '3' && 'Tiếp tục bước 4'}
                    </Button>
                )}
            </div>
        </Form>
    );
}
