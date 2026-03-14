'use client';

import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import {
    Card, Form, Input, Button, Space, Tag, Typography, Divider, Alert,
    Spin, InputNumber, Row, Col, Tabs, App, Progress, Drawer, Tooltip, Descriptions, Badge, Modal
} from 'antd';
import {
    HeartOutlined, FileTextOutlined, MedicineBoxOutlined, InfoCircleOutlined,
    WarningOutlined, ExperimentOutlined, UserOutlined, ArrowRightOutlined,
    RobotOutlined, SaveOutlined, CheckCircleOutlined, ArrowLeftOutlined,
    FundViewOutlined, BarcodeOutlined, EyeOutlined, PrinterOutlined, FileImageOutlined,
} from '@ant-design/icons';
import { visitApi, emrApi, patientApi, lisApi, risApi } from '@/lib/services';
import type { Visit, Patient } from '@/types';
import { useRouter, useParams } from 'next/navigation';
import { useAuth } from '@/contexts/AuthContext';

import dayjs from 'dayjs';

import CLSOrderTab from '@/components/clinical/CLSOrderTab';
import DiagnosisAndPrescriptionTab from '@/components/clinical/DiagnosisAndPrescriptionTab';
import AIChat from '@/components/clinical/AIChat';

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
    doctor?: string;       // staff ID of the assigned doctor
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
    dicom_study_uid?: string;
    orthanc_instance_id?: string;
    status: string;
    // Approval / verification fields
    patient_name?: string;
    patient_code?: string;
    radiologist_name?: string;
    verified_by_name?: string;
    verified_time?: string;
    modality_name?: string;
    clinical_indication?: string;
    body_part?: string;
}

function KetQuaTab({
    visitId,
    onGoToDiagnosis,
    onNewResult,
    onDataLoaded,
}: {
    visitId: string;
    onGoToDiagnosis: () => void;
    /** Callback khi có kết quả mới từ LIS/RIS — gửi prompt tới AI agent */
    onNewResult?: (prompt: string) => void;
    /** Callback đẩy dữ liệu lên cha */
    onDataLoaded?: (lab: LabResultRow[], img: ImagingResult[]) => void;
}) {
    const [labRows, setLabRows] = React.useState<LabResultRow[]>([]);
    const [imaging, setImaging] = React.useState<ImagingResult[]>([]);

    React.useEffect(() => {
        if (onDataLoaded) onDataLoaded(labRows, imaging);
    }, [labRows, imaging, onDataLoaded]);

    const [loadingLis, setLoadingLis] = React.useState(true);
    const [loadingRis, setLoadingRis] = React.useState(true);
    const [aiSummary, setAiSummary] = React.useState<string>('');
    const [viewerStudyUid, setViewerStudyUid] = React.useState<string | null>(null);

    // Giữ ref cho callback để không cần thêm vào deps của WS effect
    const onNewResultRef = React.useRef(onNewResult);
    React.useEffect(() => { onNewResultRef.current = onNewResult; }, [onNewResult]);

    // Track order_id đã trigger AI để tránh gửi lặp (REPORTED + VERIFIED = 2 events)
    const lastTriggeredRisOrderRef = React.useRef<string | null>(null);
    const [detailModalImg, setDetailModalImg] = React.useState<ImagingResult | null>(null);

    const fetchLis = useCallback(() => {
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
    }, [visitId]);

    useEffect(() => {
        fetchLis();
    }, [fetchLis]);

    const fetchRis = useCallback(() => {
        // Fetch RIS orders for this visit
        risApi.getOrders({ visit: visitId }).then((res) => {
            const orders = res.results || res || [];
            const imgs: ImagingResult[] = orders
                .filter((o: Record<string, unknown>) => o.status === 'VERIFIED')
                .map((o: Record<string, unknown>) => {
                    const result = (o.result || {}) as Record<string, unknown>;
                    const execution = (o.execution || {}) as Record<string, unknown>;
                    return {
                        id: String(o.id),
                        procedure_name: String((o.procedure_detail as Record<string, unknown>)?.name || o.procedure_name || 'Chẩn đoán hình ảnh'),
                        order_time: String(o.order_time || ''),
                        doctor_name: String((o.doctor_detail as Record<string, unknown>)?.full_name || o.doctor_name || ''),
                        findings: String(result.findings || ''),
                        conclusion: String(result.conclusion || ''),
                        is_abnormal: Boolean(result.is_abnormal),
                        image_url: result.image_url as string | undefined,
                        dicom_study_uid: execution.dicom_study_uid as string | undefined,
                        orthanc_instance_id: execution.orthanc_instance_id as string | undefined,
                        status: String(o.status || ''),
                        // Approval fields
                        patient_name: String(o.patient_name || ''),
                        patient_code: String(o.patient_code || ''),
                        radiologist_name: String(result.radiologist_name || ''),
                        verified_by_name: String(result.verified_by_name || ''),
                        verified_time: String(result.verified_time || ''),
                        modality_name: String(o.modality_name || ''),
                        clinical_indication: String(o.clinical_indication || ''),
                        body_part: String((o.procedure_detail as Record<string, unknown>)?.body_part || ''),
                    };
                });
            setImaging(imgs);
        }).catch(() => { }).finally(() => setLoadingRis(false));
    }, [visitId]);

    useEffect(() => {
        fetchRis();
    }, [fetchRis]);

    // WebSocket for realtime updates
    useEffect(() => {
        if (!visitId) return;
        let ws: WebSocket;
        let reconnectTimeout: NodeJS.Timeout;
        let isMounted = true;

        const connectWs = () => {
            if (!isMounted) return;
            const host = window.location.hostname;
            ws = new WebSocket(`ws://${host}:8000/ws/clinical/${visitId}/updates/`);

            ws.onopen = () => console.log('WebSocket Clinical connected for visit', visitId);

            ws.onmessage = (event) => {
                if (!isMounted) return;
                try {
                    const data = JSON.parse(event.data) as Record<string, unknown>;
                    if (data.type === 'cls_result_updated' || data.type === 'clinical.cls_updated') {
                        if (data.service_type === 'ris') {
                            // Refresh imaging table
                            fetchRis();

                            // Trigger AI re-analysis with RIS findings/conclusion
                            const procedureName = String(data.procedure_name || 'Chẩn đoán hình ảnh');
                            const findings = String(data.findings || '');
                            const conclusion = String(data.conclusion || '');
                            const isAbnormal = Boolean(data.is_abnormal);

                            if (onNewResultRef.current && (findings || conclusion)) {
                                // Chỉ trigger AI một lần cho mỗi order (tránh REPORTED + VERIFIED gửi 2 lần)
                                const orderId = String(data.order_id || '');
                                if (orderId && orderId === lastTriggeredRisOrderRef.current) return;
                                lastTriggeredRisOrderRef.current = orderId;

                                const aiPrompt = [
                                    `[KẾT QUẢ CĐHA MỚI - ${procedureName}]`,
                                    findings ? `Mô tả: ${findings}` : '',
                                    conclusion ? `Kết luận: ${conclusion}` : '',
                                    '',
                                    'Dựa trên kết quả CĐHA vừa nhận, hãy:',
                                    '1. Cập nhật các chẩn đoán phân biệt.',
                                    '2. Nhận xét ý nghĩa của hình ảnh trong bệnh cảnh hiện tại.',
                                    '3. Đề xuất hướng xử trí tiếp theo.',
                                ].filter(Boolean).join('\n');
                                onNewResultRef.current(aiPrompt);
                            }

                        } else if (data.service_type === 'lis') {
                            // Refresh LIS table
                            fetchLis();

                            // Trigger AI re-analysis with LIS abnormal summary
                            const abnormalItems = (data.abnormal_items as Array<Record<string, unknown>>) || [];

                            if (onNewResultRef.current) {
                                let aiPrompt: string;
                                if (abnormalItems.length > 0) {
                                    const lines = abnormalItems.map(item => {
                                        const flag = String(item.flag || '');
                                        const dir = (flag === 'H' || flag === 'HH') ? '↑ cao' : '↓ thấp';
                                        const critical = item.is_critical ? ' ⚠️ CẤP CỨU' : '';
                                        return `  - ${item.name}: ${item.value} ${item.unit} (${dir}${critical})`;
                                    }).join('\n');
                                    aiPrompt = [
                                        '[KẾT QUẢ XÉT NGHIỆM MỚI]',
                                        `Có ${abnormalItems.length} chỉ số bất thường:`,
                                        lines,
                                        '',
                                        'Dựa trên kết quả xét nghiệm vừa nhận, hãy:',
                                        '1. Giải thích ý nghĩa lâm sàng của các giá trị bất thường.',
                                        '2. Cập nhật các chẩn đoán phân biệt có trọng số theo kết quả này.',
                                        '3. Gợi ý phác đồ điều trị phù hợp.',
                                    ].filter(Boolean).join('\n');
                                } else {
                                    aiPrompt = [
                                        '[KẾT QUẢ XÉT NGHIỆM MỚI]',
                                        'Tất cả các chỉ số trong giới hạn bình thường.',
                                        '',
                                        'Dựa trên kết quả xét nghiệm bình thường, có cần điều chỉnh hướng chẩn đoán không?',
                                    ].join('\n');
                                }
                                onNewResultRef.current(aiPrompt);
                            }
                        }
                    }
                } catch { /* parse error */ }
            };

            ws.onclose = () => {
                if (!isMounted) return;
                reconnectTimeout = setTimeout(connectWs, 3000);
            };
            ws.onerror = () => console.error('WebSocket Clinical error');
        };

        connectWs();
        return () => {
            isMounted = false;
            clearTimeout(reconnectTimeout);
            ws?.close();
        };
    }, [visitId, fetchRis, fetchLis]);

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

    return (
        <div className="h-full overflow-y-auto p-4 pt-3 space-y-3" style={{ scrollbarWidth: 'thin' }}>


            {/* Unified Clinical Results Panel (Now Tabs) */}
            <div style={{ background: '#fff', borderRadius: 12, border: '1px solid #e5e7eb', overflow: 'hidden', display: 'flex', flexDirection: 'column', height: '100%' }}>
                <Tabs
                    defaultActiveKey="lis"
                    items={[
                        {
                            key: 'lis',
                            label: (
                                <span style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, padding: '0 16px' }}>
                                    <FundViewOutlined style={{ color: '#10b981' }} /> Xét nghiệm (LIS)
                                    {labRows.length > 0 && <Tag color="green" style={{ margin: 0, fontSize: 11 }}>{labRows.length}</Tag>}
                                </span>
                            ),
                            children: (
                                <div style={{ padding: '16px', overflowY: 'auto', maxHeight: 'calc(100vh - 350px)' }} className="scrollbar-thin">
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
                            ),
                        },
                        {
                            key: 'ris',
                            label: (
                                <span style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6, padding: '0 16px' }}>
                                    <FileImageOutlined style={{ color: '#f59e0b' }} /> Chẩn đoán hình ảnh (RIS/PACS)
                                    {imaging.length > 0 && <Tag color="blue" style={{ margin: 0, fontSize: 11 }}>{imaging.length}</Tag>}
                                </span>
                            ),
                            children: (
                                <div style={{ padding: '16px', overflowY: 'auto', maxHeight: 'calc(100vh - 350px)' }} className="scrollbar-thin">
                                    {loadingRis ? (
                                        <div style={{ padding: 24, textAlign: 'center' }}><Spin size="small" /></div>
                                    ) : imaging.length === 0 ? (
                                        <div style={{ padding: 24, textAlign: 'center', color: '#9ca3af', fontSize: 13 }}>
                                            Chưa có kết quả chẩn đoán hình ảnh.
                                        </div>
                                    ) : (
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
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
                                                        <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
                                                            {img.is_abnormal && (
                                                                <Tooltip title="Kết quả bất thường">
                                                                    <WarningOutlined style={{ color: '#f59e0b', fontSize: 16 }} />
                                                                </Tooltip>
                                                            )}
                                                            <Tooltip title="Xem chi tiết kết quả">
                                                                <Button size="small" icon={<EyeOutlined />}
                                                                    onClick={() => setDetailModalImg(img)}
                                                                    style={{ fontSize: 11, height: 26, color: '#6366f1', borderColor: '#c7d2fe' }}>
                                                                    Xem chi tiết
                                                                </Button>
                                                            </Tooltip>
                                                        </div>
                                                    </div>

                                                    {/* Brief conclusion preview */}
                                                    {img.conclusion && (
                                                        <div style={{ marginTop: 4 }}>
                                                            <div style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', letterSpacing: '0.05em', marginBottom: 2 }}>KẾT LUẬN:</div>
                                                            <div
                                                                style={{ fontSize: 12, fontWeight: 600, color: img.is_abnormal ? '#b45309' : '#166534', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                                                                dangerouslySetInnerHTML={{ __html: img.conclusion }}
                                                            />
                                                        </div>
                                                    )}
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ),
                        },
                    ]}
                    tabBarStyle={{
                        marginBottom: 0,
                        padding: '8px 16px 0 16px',
                        background: '#f8fafc',
                        borderBottom: '1px solid #e2e8f0',
                    }}
                />
            </div>

            {/* ── RIS Detail Modal ───────────────────────────────────────── */}
            <Modal
                open={!!detailModalImg}
                onCancel={() => setDetailModalImg(null)}
                footer={null}
                width={960}
                title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <FileImageOutlined style={{ color: '#6366f1', fontSize: 18 }} />
                        <span style={{ fontWeight: 700, fontSize: 15 }}>Chi tiết kết quả chẩn đoán hình ảnh</span>
                    </div>
                }
                styles={{ body: { padding: '16px 24px 12px' } }}
                destroyOnClose
            >
                {detailModalImg && (
                    <div>
                        {/* Two-column layout */}
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, overflow: 'hidden' }}>
                            {/* LEFT: Patient Info + Findings */}
                            <div style={{ minWidth: 0 }}>
                                <div style={{ marginBottom: 16 }}>
                                    <div style={{ fontSize: 12, fontWeight: 700, color: '#6b7280', letterSpacing: '0.04em', marginBottom: 8, textTransform: 'uppercase' }}>
                                        Thông tin bệnh nhân
                                    </div>
                                    <div style={{ background: '#f9fafb', borderRadius: 8, padding: '10px 14px', border: '1px solid #f0f0f0' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                            <Text style={{ fontSize: 12, color: '#6b7280' }}>Họ tên:</Text>
                                            <Text style={{ fontSize: 13, fontWeight: 600, color: '#111827' }}>{detailModalImg.patient_name || '--'}</Text>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                            <Text style={{ fontSize: 12, color: '#6b7280' }}>Mã BN:</Text>
                                            <Text style={{ fontSize: 13, color: '#374151' }}>{detailModalImg.patient_code || '--'}</Text>
                                        </div>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                            <Text style={{ fontSize: 12, color: '#6b7280' }}>Kỹ thuật:</Text>
                                            <Text style={{ fontSize: 13, color: '#374151' }}>{detailModalImg.procedure_name}</Text>
                                        </div>
                                        {detailModalImg.modality_name && (
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                                                <Text style={{ fontSize: 12, color: '#6b7280' }}>Loại máy:</Text>
                                                <Text style={{ fontSize: 13, color: '#374151' }}>{detailModalImg.modality_name}</Text>
                                            </div>
                                        )}
                                        {detailModalImg.clinical_indication && (
                                            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                                <Text style={{ fontSize: 12, color: '#6b7280' }}>Chỉ định:</Text>
                                                <Text style={{ fontSize: 13, color: '#374151', maxWidth: 200, textAlign: 'right' }}>{detailModalImg.clinical_indication}</Text>
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Findings / Mô tả */}
                                <div>
                                    <div style={{ fontSize: 12, fontWeight: 700, color: '#6b7280', letterSpacing: '0.04em', marginBottom: 8, textTransform: 'uppercase' }}>
                                        Mô tả hình ảnh (Findings)
                                    </div>
                                    {detailModalImg.findings ? (
                                        <div
                                            style={{ background: '#f9fafb', borderRadius: 8, padding: '10px 14px', border: '1px solid #f0f0f0', fontSize: 13, color: '#374151', lineHeight: 1.7 }}
                                            dangerouslySetInnerHTML={{ __html: detailModalImg.findings }}
                                        />
                                    ) : (
                                        <div style={{ padding: 12, textAlign: 'center', color: '#9ca3af', fontSize: 13, background: '#f9fafb', borderRadius: 8 }}>
                                            Chưa có mô tả.
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* RIGHT: Image + Conclusion */}
                            <div style={{ minWidth: 0 }}>
                                {/* Image Preview */}
                                <div style={{ marginBottom: 16 }}>
                                    <div style={{ fontSize: 12, fontWeight: 700, color: '#6b7280', letterSpacing: '0.04em', marginBottom: 8, textTransform: 'uppercase' }}>
                                        Hình ảnh
                                    </div>
                                    <div style={{ borderRadius: 8, overflow: 'hidden', border: '1px solid #e5e7eb', background: '#1a1a2e', minHeight: 200, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                                        {detailModalImg.orthanc_instance_id ? (
                                            <img
                                                src={`http://${window.location.hostname}:8042/instances/${detailModalImg.orthanc_instance_id}/preview`}
                                                alt="DICOM Preview"
                                                style={{ width: '100%', maxHeight: 400, objectFit: 'contain' }}
                                            />
                                        ) : detailModalImg.dicom_study_uid ? (
                                            <iframe
                                                src={`http://localhost:3001/viewer?StudyInstanceUIDs=${detailModalImg.dicom_study_uid}`}
                                                style={{ width: '100%', height: 350, border: 'none' }}
                                                title="OHIF Viewer"
                                                allow="clipboard-read; clipboard-write; fullscreen"
                                            />
                                        ) : (
                                            <div style={{ padding: 40, textAlign: 'center', color: '#6b7280', fontSize: 13 }}>
                                                <FileImageOutlined style={{ fontSize: 32, marginBottom: 8, display: 'block', color: '#9ca3af' }} />
                                                Chưa có ảnh DICOM
                                            </div>
                                        )}
                                    </div>
                                </div>

                                {/* Conclusion */}
                                <div>
                                    <div style={{ fontSize: 12, fontWeight: 700, color: '#6b7280', letterSpacing: '0.04em', marginBottom: 8, textTransform: 'uppercase' }}>
                                        Kết luận
                                    </div>
                                    {detailModalImg.conclusion ? (
                                        <div
                                            style={{
                                                background: detailModalImg.is_abnormal ? '#fffbeb' : '#f0fdf4',
                                                borderRadius: 8,
                                                padding: '10px 14px',
                                                border: `1px solid ${detailModalImg.is_abnormal ? '#fde68a' : '#bbf7d0'}`,
                                                fontSize: 13,
                                                fontWeight: 600,
                                                color: detailModalImg.is_abnormal ? '#b45309' : '#166534',
                                                lineHeight: 1.7,
                                            }}
                                            dangerouslySetInnerHTML={{ __html: detailModalImg.conclusion }}
                                        />
                                    ) : (
                                        <div style={{ padding: 12, textAlign: 'center', color: '#9ca3af', fontSize: 13, background: '#f9fafb', borderRadius: 8 }}>
                                            Chưa có kết luận.
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>

                        {/* Footer: Approval info */}
                        <Divider style={{ margin: '16px 0 10px' }} />
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: 12, color: '#6b7280' }}>
                            <div style={{ display: 'flex', gap: 24 }}>
                                <div>
                                    <span style={{ fontWeight: 600, marginRight: 4 }}>Ngày duyệt:</span>
                                    <span style={{ color: '#374151' }}>
                                        {detailModalImg.verified_time ? dayjs(detailModalImg.verified_time).format('DD/MM/YYYY HH:mm') : '--'}
                                    </span>
                                </div>
                                <div>
                                    <span style={{ fontWeight: 600, marginRight: 4 }}>Người duyệt:</span>
                                    <span style={{ color: '#374151' }}>{detailModalImg.verified_by_name || '--'}</span>
                                </div>
                            </div>
                            <div>
                                <span style={{ fontWeight: 600, marginRight: 4 }}>BS đọc KQ:</span>
                                <span style={{ color: '#374151' }}>{detailModalImg.radiologist_name || '--'}</span>
                            </div>
                        </div>
                    </div>
                )}
            </Modal>
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
    const { user } = useAuth();   // Lấy staff profile của bác sĩ đang đăng nhập
    // ── AI Drawer State ───────────────────────────
    const [aiDrawerOpen, setAiDrawerOpen] = useState(false);
    const [aiContext, setAiContext] = useState<string>('');
    const [aiUnreadCount, setAiUnreadCount] = useState(0);

    const [visit, setVisit] = useState<Visit | null>(null);
    const [record, setRecord] = useState<ClinicalRecord | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [triageDrawerOpen, setTriageDrawerOpen] = useState(false);
    const [icdDrawerOpen, setIcdDrawerOpen] = useState(false);
    const [icdCodes, setIcdCodes] = useState<ICDCodeItem[]>([]);
    const [aiLabTests, setAiLabTests] = useState<string>('');
    const [icdSourceWarning, setIcdSourceWarning] = useState<string | null>(null);

    // States lifted from KetQuaTab for AI Context
    const [lisData, setLisData] = useState<LabResultRow[]>([]);
    const [risData, setRisData] = useState<ImagingResult[]>([]);
    const [pendingAiPrompt, setPendingAiPrompt] = useState<string | null>(null);

    // Lắng nghe sự kiện cập nhật lab tests và ICD từ AIChat
    useEffect(() => {
        const handleUpdate = (e: any) => {
            if (e.detail?.tests) {
                setAiLabTests(e.detail.tests);
            }
            if (e.detail?.icds && e.detail.icds.length > 0) {
                setIcdCodes(e.detail.icds);
            }
        };
        window.addEventListener('ai_suggestions_update', handleUpdate);
        return () => window.removeEventListener('ai_suggestions_update', handleUpdate);
    }, []);

    // ── Tab State (controlled) ─────────────────────────────
    const DRAFT_KEY = `clinical-draft-${visitId}`;
    const [activeTab, setActiveTab] = useState<string>(() => {
        try { return localStorage.getItem(`${DRAFT_KEY}-tab`) || '1'; } catch { return '1'; }
    });

    const [form] = Form.useForm();

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
            const vals = form.getFieldsValue();
            localStorage.setItem(`${DRAFT_KEY}-form`, JSON.stringify(vals));
        } catch { /* ignore */ }
    }, [DRAFT_KEY, activeTab, form]);

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

    const saveData = async (values: any, silent = false): Promise<string | null> => {
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

            let currentRecordId = record?.id;
            if (currentRecordId) {
                await emrApi.update(currentRecordId, data);
            } else {
                const newRecord = await emrApi.create({
                    visit: visitId,
                    chief_complaint: data.chief_complaint,
                    vital_signs: vitalSigns,
                });
                setRecord(newRecord);
                currentRecordId = newRecord.id;
            }
            // Lưu state vào localStorage sau khi lưu server thành công
            persistDraft();
            if (!silent) message.success('Đã lưu nháp hồ sơ');
            return currentRecordId || null;
        } catch (error) {
            console.error('Error saving:', error);
            if (!silent) message.error('Không thể lưu hồ sơ');
            return null;
        } finally {
            setSaving(false);
        }
    };

    const handleSave = async (values: any) => {
        await saveData(values);
    };

    // ── Build AI context tổng hợp ──────────────────────
    const buildAIContext = useCallback(() => {
        const p = typeof visit?.patient === 'object' ? visit.patient as Patient : null;
        const name = p?.full_name || `${p?.last_name || ''} ${p?.first_name || ''}`.trim() || 'BN';
        const age = p?.date_of_birth ? dayjs().diff(dayjs(p.date_of_birth), 'year') : 'N/A';
        const tv = visit?.vital_signs as Record<string, number | undefined> | undefined;
        const vals = form.getFieldsValue();
        const deptName = visit?.confirmed_department_detail?.name || 'Không rõ';

        let lisRisText = '';
        if (lisData.length > 0 || risData.length > 0) {
            lisRisText = '\n══ KẾT QUẢ CẬN LÂM SÀNG ══\n';
            if (lisData.length > 0) {
                lisRisText += 'Xét nghiệm (LIS):\n';
                lisData.forEach(r => {
                    const flag = r.is_abnormal ? ` [BẤT THƯỜNG: ${r.abnormal_flag}]` : '';
                    lisRisText += `- ${r.name}: ${r.value} ${r.unit}${flag}\n`;
                });
                lisRisText += '\n';
            }
            if (risData.length > 0) {
                lisRisText += 'CĐHA (RIS):\n';
                risData.forEach(r => {
                    lisRisText += `- ${r.procedure_name}:\n  Mô tả: ${r.findings}\n  Kết luận: ${r.conclusion}\n`;
                });
            }
        }

        const context = `[CLINICAL_ANALYSIS] Tôi là bác sĩ đang trực tiếp khám bệnh nhân tại ${deptName}.
QUY TẮC TRẢ LỜI:
- Bệnh nhân ĐÃ Ở ${deptName} rồi, KHÔNG nói "cần theo dõi tại ${deptName}" hay "cần chuyển đến ${deptName}".
- Chỉ tập trung vào chẩn đoán, xử trí cụ thể tại khoa này.
- KHÔNG dùng mã code dạng [URGENT_MODERATE] trong câu trả lời.

══ THÔNG TIN BỆNH NHÂN ══
Họ tên: ${name} | Tuổi: ${age} | Giới: ${p?.gender === 'M' ? 'Nam' : 'Nữ'}
BHYT: ${p?.insurance_number || 'Không'}

══ SINH HIỆU (TẠI PHÂN LUỒNG) ══
Mạch: ${tv?.heart_rate ?? '--'} l/p | HA: ${tv?.bp_systolic ?? '--'}/${tv?.bp_diastolic ?? '--'} mmHg
SpO2: ${tv?.spo2 ?? '--'}% | Nhiệt độ: ${tv?.temperature ?? '--'}°C

══ LÝ DO KHÁM ══
${vals.chief_complaint || visit?.chief_complaint || 'Chưa rõ'}

══ BỆNH Sừ ══
${vals.history_of_present_illness || 'Chưa khai thác'}

══ KHÁM LÂM SÀNG ══
${vals.physical_exam || 'Chưa khám'}

══ TÓM TẮT BỆNH ÁN (PHÂN LUỒNG) ══
${visit?.pre_triage_summary?.substring(0, 600) || 'Không có'}

══ TÓM TẮT AI PHÂN LUỒNG ══
Mã: ${visit?.triage_code || 'N/A'} → Khoa: ${deptName}
Độ tin cậy: ${visit?.triage_confidence ?? 'N/A'}%
Ý kiến AI: ${visit?.triage_ai_response?.substring(0, 300) || 'Không có'}
${lisRisText}
══ YÊU CẦU ══
1. Đưa ra 3-5 chẩn đoán phân biệt xếp theo khả năng (%).
2. Với MỔI chẩn đoán, đưa ra mã ICD-10 chính + phụ kèm tỷ lệ chính xác (%).
3. Chỉ định cận lâm sàng cần thiết.
4. Hướng xử trí ban đầu.
5. Cảnh báo nếu có dấu hiệu nguy hiểm.`;
        return context;
    }, [visit, form, lisData, risData]);

    useEffect(() => {
        setAiContext(buildAIContext());
    }, [buildAIContext]);

    // Mở AI Drawer (có thể dính kèm prompt xử lý sự kiện kết quả mới)
    const openAIDrawer = useCallback((extraPrompt?: string) => {
        if (extraPrompt) {
            setPendingAiPrompt(extraPrompt);
        }
        setAiDrawerOpen(true);
        setAiUnreadCount(0);
    }, []);

    // Scroll to bottom kư có tin nhắn mới (phòng khi drawer chưa mở)
    // (maintained by AIChat.tsx internally)

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

                    {/* Button Các Đề Xuất thay cho ICD đề xuất cũ */}
                    {(icdCodes.length > 0 || aiLabTests) && (
                        <Tooltip title="Xem các đề xuất từ AI (ICD, Xét nghiệm)">
                            <Badge count={icdCodes.length} size="small" offset={[-2, 2]} dot={icdCodes.length === 0 && !!aiLabTests}>
                                <Button
                                    icon={<RobotOutlined />}
                                    onClick={() => setIcdDrawerOpen(true)}
                                    className="h-10 border-indigo-200 text-indigo-600 hover:bg-indigo-50 font-medium"
                                >
                                    Các Đề Xuất
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

    /* ── Suggestions (ICD & Lab Tests) Drawer ──────────────────────────────────── */
    const SuggestionsDrawer = () => {
        const hasExternal = icdCodes.some(c => c.in_system === false);
        const mainCodes = icdCodes.filter(c => c.type === 'main').sort((a, b) => b.confidence - a.confidence);
        const subCodes = icdCodes.filter(c => c.type === 'sub').sort((a, b) => b.confidence - a.confidence);
        const labTests = aiLabTests;

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
                            ? 'border-indigo-200 bg-indigo-50/50'
                            : 'border-gray-200 bg-gray-50/50'
                        }`}
                >
                    <div className="flex items-center justify-between mb-1.5">
                        <div className="flex items-center gap-1.5 flex-wrap">
                            <Tag
                                color={isMain ? 'indigo' : 'default'}
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
                title={<div className="flex items-center gap-2 font-bold text-sm"><RobotOutlined className="text-indigo-500" /> Các Đề Xuất (AI)</div>}
                placement="right"
                width={500}
                open={icdDrawerOpen}
                onClose={() => setIcdDrawerOpen(false)}
                styles={{ body: { padding: '0 16px', display: 'flex', flexDirection: 'column' } }}
            >
                <Tabs
                    defaultActiveKey="icd"
                    className="h-full [&>.ant-tabs-content-holder]:overflow-y-auto [&>.ant-tabs-content-holder]:pb-6"
                    items={[
                        {
                            key: 'icd',
                            label: <span><BarcodeOutlined /> ICD Đề Xuất</span>,
                            children: icdCodes.length === 0 ? (
                                <div className="text-center py-10 text-gray-400 text-sm">
                                    Chưa có mã ICD-10 đề xuất.
                                </div>
                            ) : (
                                <div className="space-y-3 pt-3">
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
                                            <div className="text-[11px] font-bold text-indigo-600 tracking-wider mb-2 uppercase">
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
                            )
                        },
                        {
                            key: 'lab',
                            label: <span><ExperimentOutlined /> Đề Xuất Xét Nghiệm</span>,
                            children: !labTests ? (
                                <div className="text-center py-10 text-gray-400 text-sm">
                                    Chưa có đề xuất xét nghiệm.
                                </div>
                            ) : (
                                <div className="pt-3">
                                    <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed shadow-sm">
                                        {labTests}
                                    </div>
                                </div>
                            )
                        }
                    ]}
                />
            </Drawer>
        );
    };

    return (
        <Form form={form} layout="vertical" onFinish={handleSave} className="h-full flex flex-col overflow-hidden min-h-0">
            <PatientHeader />
            <TriageDrawer />
            <SuggestionsDrawer />

            {/* ── AI Drawer ──────────────────────────────────── */}
            <Drawer
                title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <RobotOutlined style={{ color: '#6366f1', fontSize: 18 }} />
                        <span style={{ fontWeight: 700, fontSize: 15 }}>Trợ Lý Lâm Sàng AI</span>
                    </div>
                }
                placement="right"
                width={500}
                open={aiDrawerOpen}
                onClose={() => setAiDrawerOpen(false)}
                styles={{ body: { padding: '12px 16px', display: 'flex', flexDirection: 'column', height: '100%' } }}
                destroyOnClose={false}
            >
                <AIChat
                    visitId={visitId}
                    initialContext={aiContext}
                    autoAnalyze={true}
                    pendingPrompt={pendingAiPrompt}
                    onPromptProcessed={() => setPendingAiPrompt(null)}
                />
            </Drawer>

            {/* ── Floating AI toggle button ───────────────────────── */}
            <Tooltip title="Mở Trợ Lý AI" placement="left">
                <button
                    type="button"
                    onClick={() => openAIDrawer()}
                    style={{
                        position: 'fixed',
                        bottom: 100,
                        right: 16,
                        zIndex: 1000,
                        width: 52,
                        height: 52,
                        borderRadius: '50%',
                        background: aiDrawerOpen
                            ? 'linear-gradient(135deg, #818cf8 0%, #6366f1 100%)'
                            : 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                        border: 'none',
                        boxShadow: '0 4px 20px rgba(99,102,241,0.5)',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: '#fff',
                        fontSize: 22,
                        transition: 'all 0.2s ease',
                        transform: aiDrawerOpen ? 'scale(1.1)' : 'scale(1)',
                    }}
                >
                    {aiUnreadCount > 0 && !aiDrawerOpen && (
                        <span style={{
                            position: 'absolute', top: -4, right: -4,
                            background: '#ef4444', color: '#fff', fontSize: 11,
                            fontWeight: 700, borderRadius: '50%', width: 20, height: 20,
                            display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}>{aiUnreadCount}</span>
                    )}
                    <RobotOutlined />
                </button>
            </Tooltip>

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
                                                    <Col span={6}>
                                                        <Form.Item shouldUpdate={(prev, cur) => prev.weight !== cur.weight || prev.height !== cur.height} className="mb-0">
                                                            {() => {
                                                                const w = form.getFieldValue('weight');
                                                                const h = form.getFieldValue('height');
                                                                let calculatedBmi = '--';
                                                                if (w && h) {
                                                                    const hm = h / 100;
                                                                    calculatedBmi = (w / (hm * hm)).toFixed(1);
                                                                }
                                                                return (
                                                                    <Form.Item label="BMI" className="mb-0">
                                                                        <Input value={calculatedBmi} readOnly className="w-full bg-gray-100 font-medium" />
                                                                    </Form.Item>
                                                                );
                                                            }}
                                                        </Form.Item>
                                                    </Col>
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
                                children: <KetQuaTab 
                                    visitId={visitId} 
                                    onGoToDiagnosis={() => { setActiveTab('4'); try { localStorage.setItem(`${DRAFT_KEY}-tab`, '4'); } catch { /* ignore */ } }} 
                                    onNewResult={(prompt) => openAIDrawer(prompt)}
                                    onDataLoaded={(lab, img) => { setLisData(lab); setRisData(img); }} 
                                />,
                            },
                            {
                                key: '4',
                                label: <div className="px-4 py-1 text-gray-500 flex items-center gap-2"><MedicineBoxOutlined /> 4. Chẩn đoán & Kê đơn</div>,
                                children: <DiagnosisAndPrescriptionTab
                                    visitId={visitId}
                                    doctorId={user?.staff_profile?.id ?? ''}

                                    initialDiagnosis={record?.final_diagnosis ?? ''}
                                    initialTreatmentPlan={record?.treatment_plan ?? ''}
                                />
                            }
                        ]}
                    />
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
                            try {
                                const values = await form.validateFields();
                                const recordId = await saveData(values, true);
                                if (recordId) {
                                    await emrApi.finalize(recordId);
                                    // Đóng AI Drawer và xóa lịch sử chat của visit này
                                    setAiDrawerOpen(false);
                                    try { localStorage.removeItem(`ai_chat_history_${visitId}`); } catch { /* ignore */ }
                                    // Báo ngay cho QueueSidebar xóa bệnh nhân khỏi danh sách
                                    try {
                                        const ch = new BroadcastChannel('his_clinical_events');
                                        ch.postMessage({ type: 'VISIT_COMPLETED', visitId });
                                        ch.close();
                                    } catch { /* BroadcastChannel không khả dụng trên một số env */ }
                                    message.success('Hoàn tất khám bệnh thành công!');
                                    router.push('/dashboard/clinical');
                                } else {
                                    message.error('Không thể lưu hồ sơ trước khi hoàn tất');
                                }
                            } catch (e) {
                                console.log('Validation error:', e);
                            }
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
