'use client';

import React, { useState, useCallback, useMemo, useRef } from 'react';
import {
    Modal,
    Card,
    Space,
    Descriptions,
    Input,
    InputNumber,
    Button,
    Spin,
    Alert,
    Tag,
    Select,
    Progress,
    Typography,
    App,
    Tooltip,
    Badge,
} from 'antd';
import {
    CheckOutlined,
    MedicineBoxOutlined,
    HeartOutlined,
    ThunderboltOutlined,
    EditOutlined,
    InfoCircleOutlined,
    DownOutlined,
    UpOutlined,
} from '@ant-design/icons';
import { visitApi } from '@/lib/services';
import type { Visit, Department } from '@/types';

const { Text } = Typography;
const { TextArea } = Input;

// ============================================================================
// Cấu hình Triage Code → màu sắc + label
// ============================================================================
const triageCodeConfig: Record<string, { color: string; bg: string; label: string }> = {
    CODE_BLUE: { color: '#1677ff', bg: '#e6f4ff', label: 'Hồi sức cấp cứu (BLUE)' },
    CODE_RED: { color: '#ff4d4f', bg: '#fff1f0', label: 'Cấp cứu (RED)' },
    CODE_YELLOW: { color: '#faad14', bg: '#fffbe6', label: 'Ưu tiên (YELLOW)' },
    CODE_GREEN: { color: '#52c41a', bg: '#f6ffed', label: 'Bình thường (GREEN)' },
};

// ============================================================================
// Types
// ============================================================================
interface MatchedDepartment {
    code: string;
    name: string;
    specialties: string;
    score: string;
}

interface VitalSignsForm {
    heart_rate?: number;
    bp_systolic?: number;
    bp_diastolic?: number;
    respiratory_rate?: number;
    temperature?: number;
    spo2?: number;
    weight?: number;
    height?: number;
}

interface TriageModalProps {
    visit: Visit | null;
    open: boolean;
    departments: Department[];
    onClose: () => void;
    onSuccess: () => void;
}

// ============================================================================
// Sub-components (Memoized)
// ============================================================================

interface VitalSignsCardProps {
    vitalSigns: VitalSignsForm;
    painScale?: number;
    consciousness: string;
    loading: boolean;
    onUpdateVitalSign: (key: keyof VitalSignsForm, value: number | null) => void;
    onUpdatePainScale: (value: number | null) => void;
    onUpdateConsciousness: (value: string) => void;
}

const VitalSignsCard = React.memo(({
    vitalSigns,
    painScale,
    consciousness,
    loading,
    onUpdateVitalSign,
    onUpdatePainScale,
    onUpdateConsciousness
}: VitalSignsCardProps) => {
    return (
        <Card
            size="small"
            style={{ marginTop: 12 }}
            title={
                <Space size={4}>
                    <HeartOutlined style={{ color: '#eb2f96' }} />
                    <Text strong style={{ fontSize: 14 }}>Chỉ số sinh hiệu</Text>
                    <Tag style={{ marginLeft: 4, fontSize: 11 }}>Tùy chọn</Tag>
                </Space>
            }
            styles={{
                header: { padding: '8px 12px', minHeight: 'auto' },
                body: { padding: '12px' },
            }}
        >
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px 16px' }}>
                {/* Mạch */}
                <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>Mạch (bpm)</Text>
                    <InputNumber
                        className="w-full"
                        min={0} max={300}
                        value={vitalSigns.heart_rate}
                        onChange={v => onUpdateVitalSign('heart_rate', v)}
                        disabled={loading}
                    />
                </div>
                {/* Huyết áp tâm thu */}
                <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>HA tâm thu (mmHg)</Text>
                    <InputNumber
                        className="w-full"
                        min={0} max={300}
                        value={vitalSigns.bp_systolic}
                        onChange={v => onUpdateVitalSign('bp_systolic', v)}
                        disabled={loading}
                    />
                </div>
                {/* Huyết áp tâm trương */}
                <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>HA tâm trương (mmHg)</Text>
                    <InputNumber
                        className="w-full"
                        min={0} max={200}
                        value={vitalSigns.bp_diastolic}
                        onChange={v => onUpdateVitalSign('bp_diastolic', v)}
                        disabled={loading}
                    />
                </div>
                {/* Nhịp thở */}
                <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>Nhịp thở (/phút)</Text>
                    <InputNumber
                        className="w-full"
                        min={0} max={60}
                        value={vitalSigns.respiratory_rate}
                        onChange={v => onUpdateVitalSign('respiratory_rate', v)}
                        disabled={loading}
                    />
                </div>
                {/* Nhiệt độ */}
                <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>Nhiệt độ (°C)</Text>
                    <InputNumber
                        className="w-full"
                        min={30} max={45} step={0.1}
                        value={vitalSigns.temperature}
                        onChange={v => onUpdateVitalSign('temperature', v)}
                        disabled={loading}
                    />
                </div>
                {/* SpO2 */}
                <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>SpO2 (%)</Text>
                    <InputNumber
                        className="w-full"
                        min={0} max={100}
                        value={vitalSigns.spo2}
                        onChange={v => onUpdateVitalSign('spo2', v)}
                        disabled={loading}
                    />
                </div>
                {/* Cân nặng */}
                <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>Cân nặng (kg)</Text>
                    <InputNumber
                        className="w-full"
                        min={0} max={300} step={0.1}
                        value={vitalSigns.weight}
                        onChange={v => onUpdateVitalSign('weight', v)}
                        disabled={loading}
                    />
                </div>
                {/* Chiều cao */}
                <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>Chiều cao (cm)</Text>
                    <InputNumber
                        className="w-full"
                        min={0} max={250}
                        value={vitalSigns.height}
                        onChange={v => onUpdateVitalSign('height', v)}
                        disabled={loading}
                    />
                </div>
                {/* Thang đau */}
                <div>
                    <Text type="secondary" style={{ fontSize: 12 }}>Thang đau (0-10)</Text>
                    <InputNumber
                        className="w-full"
                        min={0} max={10}
                        value={painScale}
                        onChange={v => onUpdatePainScale(v)}
                        disabled={loading}
                    />
                </div>
            </div>

            {/* Ý thức (AVPU) */}
            <div style={{ marginTop: 10 }}>
                <Space size={8} align="center">
                    <ThunderboltOutlined style={{ color: '#faad14' }} />
                    <Text type="secondary" style={{ fontSize: 12 }}>Ý thức (AVPU)</Text>
                </Space>
                <Select
                    className="w-full"
                    placeholder="Chọn trạng thái ý thức"
                    value={consciousness || undefined}
                    onChange={onUpdateConsciousness}
                    disabled={loading}
                    allowClear
                    style={{ marginTop: 4 }}
                    options={[
                        { value: 'alert', label: 'Tỉnh táo (Alert)' },
                        { value: 'verbal', label: 'Đáp ứng lời nói (Verbal)' },
                        { value: 'pain', label: 'Đáp ứng đau (Pain)' },
                        { value: 'unresponsive', label: 'Không đáp ứng (Unresponsive)' },
                    ]}
                />
            </div>
        </Card>
    );
});
VitalSignsCard.displayName = 'VitalSignsCard';

// ============================================================================
// Component chính
// ============================================================================
export default function TriageModal({ visit, open, departments, onClose, onSuccess }: TriageModalProps) {
    const { message } = App.useApp();

    // --- Form state ---
    const chiefComplaintRef = useRef('');
    const [hasComplaint, setHasComplaint] = useState(false);
    const [vitalSigns, setVitalSigns] = useState<VitalSignsForm>({});
    const [painScale, setPainScale] = useState<number | undefined>(undefined);
    const [consciousness, setConsciousness] = useState<string>('');

    // --- AI result state ---
    const [triageLoading, setTriageLoading] = useState(false);
    const [triageResult, setTriageResult] = useState<{
        ai_response: string;
        triage_code: string;
        recommended_department_name: string | null;
        triage_confidence: number;
        matched_departments: MatchedDepartment[];
        key_factors: string[];
    } | null>(null);
    const [selectedDeptId, setSelectedDeptId] = useState<string | null>(null);
    const [confirmLoading, setConfirmLoading] = useState(false);
    const [showFullAnalysis, setShowFullAnalysis] = useState(false);

    // Reset state khi mở modal — nếu visit đã có data từ AI, restore lại
    const handleAfterOpenChange = useCallback((isOpen: boolean) => {
        if (isOpen && visit) {
            // Luôn set chief complaint từ visit (Kiosk hoặc đã nhập trước)
            chiefComplaintRef.current = visit.chief_complaint || '';
            setHasComplaint(!!visit.chief_complaint);
            setShowFullAnalysis(false);
            setConfirmLoading(false);

            // Nếu visit đã qua AI (status TRIAGE), restore tất cả state đã lưu
            if (visit.status === 'TRIAGE' && visit.triage_code) {
                // Restore vital signs
                if (visit.vital_signs && typeof visit.vital_signs === 'object') {
                    const vs = visit.vital_signs as Record<string, unknown>;
                    setVitalSigns({
                        heart_rate: vs.heart_rate as number | undefined,
                        bp_systolic: vs.bp_systolic as number | undefined,
                        bp_diastolic: vs.bp_diastolic as number | undefined,
                        respiratory_rate: vs.respiratory_rate as number | undefined,
                        temperature: vs.temperature as number | undefined,
                        spo2: vs.spo2 as number | undefined,
                        weight: vs.weight as number | undefined,
                        height: vs.height as number | undefined,
                    });
                    setPainScale(vs.pain_scale as number | undefined);
                    setConsciousness((vs.consciousness as string) || '');
                } else {
                    setVitalSigns({});
                    setPainScale(undefined);
                    setConsciousness('');
                }

                // Restore AI result (từ dữ liệu đã lưu trên Visit)
                setTriageResult({
                    ai_response: visit.triage_ai_response || '',
                    triage_code: visit.triage_code,
                    recommended_department_name:
                        visit.recommended_department_detail?.name || null,
                    triage_confidence: visit.triage_confidence || 0,
                    matched_departments: visit.triage_matched_departments || [],
                    key_factors: visit.triage_key_factors || [],
                });

                // Pre-select khoa AI đề xuất
                if (visit.recommended_department_detail) {
                    setSelectedDeptId(visit.recommended_department_detail.id);
                } else if (typeof visit.recommended_department === 'string') {
                    setSelectedDeptId(visit.recommended_department);
                } else {
                    setSelectedDeptId(null);
                }
            } else {
                // Visit mới (CHECK_IN) — reset tất cả
                setVitalSigns({});
                setPainScale(undefined);
                setConsciousness('');
                setTriageResult(null);
                setSelectedDeptId(null);
            }
        }
    }, [visit]);

    // --- Helper: cập nhật 1 field sinh hiệu (Memoized) ---
    const updateVitalSign = useCallback((key: keyof VitalSignsForm, value: number | null) => {
        setVitalSigns(prev => ({ ...prev, [key]: value ?? undefined }));
    }, []);

    const updatePainScale = useCallback((value: number | null) => {
        setPainScale(value ?? undefined);
    }, []);

    const updateConsciousness = useCallback((value: string) => {
        setConsciousness(value);
    }, []);

    // ========================================================================
    // Gọi AI phân luồng
    // ========================================================================
    const handleRunTriage = async () => {
        if (!visit) return;

        // Validate: cần ít nhất lý do khám
        if (!chiefComplaintRef.current.trim()) {
            message.warning('Vui lòng nhập lý do khám');
            return;
        }

        setTriageLoading(true);
        try {
            const result = await visitApi.triage(visit.id, {
                chief_complaint: chiefComplaintRef.current,
                vital_signs: vitalSigns,
                pain_scale: painScale,
                consciousness: consciousness || undefined,
            });
            setTriageResult({
                ai_response: result.ai_response,
                triage_code: result.triage_code || 'CODE_GREEN',
                recommended_department_name: result.recommended_department_name,
                triage_confidence: result.triage_confidence || 70,
                matched_departments: result.matched_departments || [],
                key_factors: result.key_factors || [],
            });
            if (result.recommended_department) {
                setSelectedDeptId(result.recommended_department);
            } else if (result.recommended_department_name) {
                const match = departments.find(
                    d => d.name.toLowerCase() === result.recommended_department_name?.toLowerCase()
                );
                if (match) setSelectedDeptId(match.id);
            }
            message.success('AI đã hoàn tất phân luồng!');
            // Refresh bảng visits ở parent để nút "Chốt khoa" hiện đúng
            onSuccess();
        } catch (error) {
            console.error('Triage error:', error);
            message.error('Không thể gọi AI phân luồng');
        } finally {
            setTriageLoading(false);
        }
    };

    // ========================================================================
    // Xác nhận phân luồng
    // ========================================================================
    const handleConfirmTriage = async () => {
        if (!visit || !selectedDeptId) {
            message.warning('Vui lòng chọn khoa hướng đến');
            return;
        }
        setConfirmLoading(true);
        try {
            // Lọc vital signs: chỉ gửi field có giá trị thật
            const cleanVitalSigns: Record<string, number> = {};
            for (const [key, val] of Object.entries(vitalSigns)) {
                if (val !== undefined && val !== null) {
                    cleanVitalSigns[key] = val;
                }
            }
            // Thêm painScale + consciousness nếu có
            if (painScale !== undefined) cleanVitalSigns.pain_scale = painScale;
            if (consciousness) (cleanVitalSigns as Record<string, unknown>).consciousness = consciousness;

            const hasVitals = Object.keys(cleanVitalSigns).length > 0;

            // Xác định triage_method: có kết quả AI → 'AI', ngược lại → 'MANUAL'
            const triageMethod = triageResult ? 'AI' as const : 'MANUAL' as const;

            await visitApi.confirmTriage(visit.id, {
                department_id: selectedDeptId,
                triage_method: triageMethod,
                triage_code: triageResult?.triage_code,
                chief_complaint: chiefComplaintRef.current || undefined,
                vital_signs: hasVitals ? cleanVitalSigns : undefined,
                triage_confidence: triageResult?.triage_confidence,
                triage_ai_response: triageResult?.ai_response,
            });
            message.success('Đã xác nhận phân luồng thành công!');
            onClose();
            onSuccess();
        } catch (error) {
            console.error('Confirm triage error:', error);
            message.error('Không thể xác nhận phân luồng');
        } finally {
            setConfirmLoading(false);
        }
    };

    // --- Chọn khoa từ danh sách AI đề xuất ---
    const handleSelectMatchedDept = (deptCode: string, deptName: string) => {
        const match = departments.find(d => d.code === deptCode);
        if (match) {
            setSelectedDeptId(match.id);
            message.info(`Đã chọn: ${deptName}`);
        }
    };

    // --- Lấy tên bệnh nhân ---
    const getPatientName = useCallback(() => {
        if (!visit) return '';
        if (visit.patient_detail) {
            return visit.patient_detail.full_name || `${visit.patient_detail.last_name} ${visit.patient_detail.first_name}`;
        }
        if (typeof visit.patient === 'object') {
            return visit.patient.full_name || `${visit.patient.last_name} ${visit.patient.first_name}`;
        }
        return String(visit.patient);
    }, [visit]);

    const hasMatchedDepts = triageResult && triageResult.matched_departments.length > 0;

    // ========================================================================
    // RENDER
    // ========================================================================
    return (
        <Modal
            title={
                <Space>
                    <MedicineBoxOutlined className="text-orange-500" />
                    <span style={{ fontSize: 16 }}>Phân luồng — {visit?.visit_code}</span>
                </Space>
            }
            open={open}
            onCancel={onClose}
            afterOpenChange={handleAfterOpenChange}
            footer={null}
            width={1100}
            destroyOnHidden
        >
            {visit && (
                <div style={{ display: 'flex', gap: 16, marginTop: 16 }}>
                    {/* ========== CỘT TRÁI: Sinh hiệu + Lý do khám + Kết quả AI ========== */}
                    <div style={{ flex: 1, minWidth: 0, maxHeight: '75vh', overflowY: 'auto', paddingRight: 4 }}>
                        {/* --- Thông tin bệnh nhân --- */}
                        <Card size="small" className="bg-gray-50">
                            <Descriptions size="small" column={2} style={{ fontSize: 14 }}>
                                <Descriptions.Item label="Bệnh nhân">{getPatientName()}</Descriptions.Item>
                                <Descriptions.Item label="Mã khám">{visit.visit_code}</Descriptions.Item>
                            </Descriptions>
                        </Card>

                        {/* --- SINH HIỆU (Y tá nhập) --- */}
                        <VitalSignsCard
                            vitalSigns={vitalSigns}
                            painScale={painScale}
                            consciousness={consciousness}
                            loading={triageLoading}
                            onUpdateVitalSign={updateVitalSign}
                            onUpdatePainScale={updatePainScale}
                            onUpdateConsciousness={updateConsciousness}
                        />

                        {/* --- LÝ DO KHÁM (Editable — y tá có thể sửa) --- */}
                        <div style={{ marginTop: 12 }}>
                            <Space size={4} align="center">
                                <EditOutlined style={{ color: '#1677ff' }} />
                                <Text strong style={{ fontSize: 14 }}>Lý do khám</Text>
                                {visit.chief_complaint && (
                                    <Tag color="cyan" style={{ marginLeft: 4, fontSize: 11 }}>
                                        Đã nhập từ Kiosk
                                    </Tag>
                                )}
                            </Space>
                            <TextArea
                                rows={2}
                                placeholder="Nhập hoặc chỉnh sửa lý do khám, triệu chứng chính..."
                                defaultValue={visit.chief_complaint || ''}
                                key={visit.id}
                                onChange={(e) => {
                                    chiefComplaintRef.current = e.target.value;
                                    setHasComplaint(!!e.target.value.trim());
                                }}
                                disabled={triageLoading}
                                style={{ marginTop: 6, fontSize: 14 }}
                            />
                        </div>

                        {/* --- NÚT GỌI AI --- */}
                        <Button
                            type="primary"
                            icon={<MedicineBoxOutlined />}
                            loading={triageLoading}
                            onClick={handleRunTriage}
                            style={{ marginTop: 12 }}
                            block
                            size="large"
                            disabled={!hasComplaint}
                        >
                            {triageLoading ? 'AI đang phân tích...' : 'AI Phân luồng'}
                        </Button>

                        {/* Loading */}
                        {triageLoading && (
                            <div className="text-center py-4">
                                <Spin size="large" />
                                <div className="mt-2 text-gray-500">AI đang phân tích sinh hiệu + triệu chứng...</div>
                            </div>
                        )}

                        {/* --- KẾT QUẢ AI --- */}
                        {triageResult && !triageLoading && (
                            <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 12 }}>
                                <Alert
                                    type={
                                        triageResult.triage_code === 'CODE_RED' || triageResult.triage_code === 'CODE_BLUE'
                                            ? 'error'
                                            : triageResult.triage_code === 'CODE_YELLOW' ? 'warning'
                                                : 'success'
                                    }
                                    showIcon
                                    title={
                                        <Space>
                                            <span
                                                className="inline-block w-4 h-4 rounded-full"
                                                style={{
                                                    backgroundColor: triageCodeConfig[triageResult.triage_code]?.color || '#52c41a',
                                                }}
                                            />
                                            <Text strong style={{ fontSize: 15 }}>
                                                {triageCodeConfig[triageResult.triage_code]?.label || triageResult.triage_code}
                                            </Text>
                                        </Space>
                                    }
                                    description={
                                        <div style={{ marginTop: 8, display: 'flex', flexDirection: 'column', gap: 6 }}>
                                            <div style={{ fontSize: 14 }}>
                                                <Text strong>Khoa đề xuất: </Text>
                                                <Tag color="blue">{triageResult.recommended_department_name || 'Không xác định'}</Tag>
                                            </div>
                                            <div style={{ fontSize: 14 }}>
                                                <Text strong>Độ tin cậy: </Text>
                                                <Progress
                                                    percent={triageResult.triage_confidence}
                                                    size="small"
                                                    style={{ maxWidth: 200, display: 'inline-flex' }}
                                                    status={triageResult.triage_confidence >= 80 ? 'success' : 'normal'}
                                                />
                                            </div>
                                        </div>
                                    }
                                />

                                {/* 🔍 Key Factors (Cơ sở phân luồng - ngắn gọn) */}
                                {triageResult.key_factors.length > 0 && (
                                    <div
                                        style={{
                                            padding: '10px 14px',
                                            borderRadius: 8,
                                            background: '#f6f8fa',
                                            border: '1px solid #e8e8e8',
                                        }}
                                    >
                                        <Space size={6} align="center" style={{ marginBottom: 6 }}>
                                            <InfoCircleOutlined style={{ color: '#1677ff', fontSize: 15 }} />
                                            <Text strong style={{ fontSize: 14, color: '#1677ff' }}>
                                                Cơ sở phân luồng
                                            </Text>
                                        </Space>
                                        <ul style={{
                                            margin: '4px 0 0 0',
                                            paddingLeft: 18,
                                            listStyle: 'disc',
                                            fontSize: 14,
                                            lineHeight: 1.7,
                                            color: '#333',
                                        }}>
                                            {triageResult.key_factors.map((factor, idx) => (
                                                <li key={idx} style={{
                                                    fontWeight: factor.startsWith('⚠') ? 600 : 400,
                                                    color: factor.startsWith('⚠') ? '#d4380d' : '#333',
                                                }}>
                                                    {factor}
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}

                                {/* Toggle: Xem phân tích đầy đủ */}
                                <div
                                    onClick={() => setShowFullAnalysis(!showFullAnalysis)}
                                    style={{
                                        cursor: 'pointer',
                                        display: 'flex',
                                        alignItems: 'center',
                                        gap: 6,
                                        padding: '6px 0',
                                        fontSize: 13,
                                        color: '#8c8c8c',
                                        userSelect: 'none',
                                    }}
                                >
                                    {showFullAnalysis ? <UpOutlined style={{ fontSize: 11 }} /> : <DownOutlined style={{ fontSize: 11 }} />}
                                    <span>{showFullAnalysis ? 'Ẩn phân tích đầy đủ' : 'Xem phân tích đầy đủ'}</span>
                                </div>

                                {/* AI Full Reasoning (ẩn/hiện) */}
                                {showFullAnalysis && (
                                    <Card
                                        size="small"
                                        title={<Text type="secondary" style={{ fontSize: 13 }}><MedicineBoxOutlined /> Phân luồng</Text>}
                                        className="bg-blue-50"
                                        styles={{ body: { maxHeight: 200, overflow: 'auto' } }}
                                    >
                                        <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, color: '#555' }}>
                                            {triageResult.ai_response}
                                        </div>
                                    </Card>
                                )}
                            </div>
                        )}
                    </div>

                    {/* ========== CỘT PHẢI: Chốt khoa (luôn hiện) ========== */}
                    <div style={{
                        width: 340,
                        flexShrink: 0,
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 12,
                        maxHeight: '75vh',
                        overflowY: 'auto',
                    }}>
                        {/* --- SECTION 1: Khoa AI đề xuất (chỉ sau khi AI chạy) --- */}
                        {hasMatchedDepts && (
                            <Card
                                size="small"
                                title={
                                    <Space size={4}>
                                        <MedicineBoxOutlined style={{ color: '#722ed1' }} />
                                        <Text strong style={{ fontSize: 14 }}>Khoa AI đề xuất</Text>
                                        <Tag color="purple" style={{ marginLeft: 4, fontSize: 13 }}>
                                            {triageResult!.matched_departments.length} kết quả
                                        </Tag>
                                    </Space>
                                }
                                styles={{
                                    header: { padding: '8px 12px', minHeight: 'auto' },
                                    body: { padding: '8px 12px' },
                                }}
                            >
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                                    {triageResult!.matched_departments.map((dept, idx) => {
                                        const isSelected = departments.find(
                                            d => d.code === dept.code && d.id === selectedDeptId
                                        );
                                        const scoreNum = parseFloat(dept.score);
                                        const scorePercent = !isNaN(scoreNum) ? Math.round(scoreNum * 100) : null;

                                        return (
                                            <Tooltip key={dept.code} title="Nhấn để chọn khoa này">
                                                <div
                                                    onClick={() => handleSelectMatchedDept(dept.code, dept.name)}
                                                    style={{
                                                        padding: '8px 10px',
                                                        borderRadius: 8,
                                                        border: isSelected
                                                            ? '2px solid #722ed1'
                                                            : '1px solid #f0f0f0',
                                                        background: isSelected ? '#f9f0ff' : '#fafafa',
                                                        cursor: 'pointer',
                                                        transition: 'all 0.2s',
                                                        display: 'flex',
                                                        alignItems: 'flex-start',
                                                        gap: 8,
                                                    }}
                                                    onMouseEnter={(e) => {
                                                        if (!isSelected) {
                                                            e.currentTarget.style.borderColor = '#722ed1';
                                                            e.currentTarget.style.background = '#faf5ff';
                                                        }
                                                    }}
                                                    onMouseLeave={(e) => {
                                                        if (!isSelected) {
                                                            e.currentTarget.style.borderColor = '#f0f0f0';
                                                            e.currentTarget.style.background = '#fafafa';
                                                        }
                                                    }}
                                                >
                                                    {/* Rank */}
                                                    <Badge
                                                        count={idx + 1}
                                                        style={{
                                                            backgroundColor: idx === 0 ? '#722ed1' : '#d9d9d9',
                                                            fontSize: 14,
                                                            minWidth: 18,
                                                            height: 18,
                                                            lineHeight: '18px',
                                                            marginTop: 2,
                                                        }}
                                                    />

                                                    {/* Info */}
                                                    <div style={{ flex: 1, minWidth: 0 }}>
                                                        <div style={{
                                                            fontWeight: 600,
                                                            fontSize: 14,
                                                            lineHeight: 1.3,
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'space-between',
                                                            gap: 4,
                                                        }}>
                                                            <span>
                                                                <Tag
                                                                    color="geekblue"
                                                                    style={{ marginRight: 4, fontSize: 11, padding: '0 4px' }}
                                                                >
                                                                    {dept.code}
                                                                </Tag>
                                                                {dept.name}
                                                            </span>
                                                            {scorePercent !== null && (
                                                                <span style={{
                                                                    fontSize: 13,
                                                                    fontWeight: 700,
                                                                    color: '#888',
                                                                    whiteSpace: 'nowrap',
                                                                }}>
                                                                    {scorePercent}%
                                                                </span>
                                                            )}
                                                        </div>
                                                        <div
                                                            style={{
                                                                fontSize: 13,
                                                                color: '#888',
                                                                marginTop: 3,
                                                                lineHeight: 1.3,
                                                                display: '-webkit-box',
                                                                WebkitLineClamp: 2,
                                                                WebkitBoxOrient: 'vertical',
                                                                overflow: 'hidden',
                                                            }}
                                                        >
                                                            {dept.specialties}
                                                        </div>
                                                    </div>
                                                </div>
                                            </Tooltip>
                                        );
                                    })}
                                </div>
                            </Card>
                        )}

                        {/* --- SECTION 2: Chốt khoa + Xác nhận (luôn hiện) --- */}
                        <Card
                            size="small"
                            title={
                                <Text strong style={{ fontSize: 14 }}>
                                    <MedicineBoxOutlined style={{ marginRight: 6 }} />
                                    Chốt khoa hướng đến
                                </Text>
                            }
                            styles={{
                                header: { padding: '8px 12px', minHeight: 'auto' },
                                body: { padding: '10px 12px' },
                            }}
                            style={{ border: '2px solid #52c41a' }}
                        >
                            <Space direction="vertical" className="w-full" size={10}>
                                <div>
                                    <Text type="secondary" style={{ fontSize: 12, marginBottom: 4, display: 'block' }}>
                                        {triageResult
                                            ? 'Khoa đã được AI đề xuất, bạn có thể thay đổi:'
                                            : 'Chọn khoa trực tiếp (không cần qua AI):'}
                                    </Text>
                                    <Select
                                        placeholder="Chọn khoa..."
                                        value={selectedDeptId}
                                        onChange={(val) => setSelectedDeptId(val)}
                                        className="w-full"
                                        showSearch
                                        optionFilterProp="label"
                                        size="large"
                                        options={departments.map(d => ({
                                            value: d.id,
                                            label: `${d.code} — ${d.name}`,
                                        }))}
                                    />
                                </div>
                                <Button
                                    type="primary"
                                    icon={<CheckOutlined />}
                                    onClick={handleConfirmTriage}
                                    loading={confirmLoading}
                                    block
                                    disabled={!selectedDeptId}
                                    size="large"
                                    style={{
                                        backgroundColor: '#52c41a',
                                        borderColor: '#52c41a',
                                        fontSize: 16,
                                        height: 52,
                                        fontWeight: 600,
                                    }}
                                >
                                    Xác nhận phân luồng
                                </Button>
                            </Space>
                        </Card>

                        {/* Ghi chú nhỏ */}
                        {!triageResult && (
                            <Text type="secondary" style={{ fontSize: 12, textAlign: 'center', padding: '0 8px' }}>
                                Bạn có thể chốt khoa ngay mà không cần chạy AI, hoặc chạy AI trước để nhận đề xuất.
                            </Text>
                        )}
                    </div>
                </div>
            )}
        </Modal>
    );
}
