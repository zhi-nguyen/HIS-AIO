'use client';

import { useState, useCallback } from 'react';
import {
    Modal,
    Card,
    Space,
    Descriptions,
    Input,
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
    RobotOutlined,
    CheckOutlined,
    MedicineBoxOutlined,
} from '@ant-design/icons';
import { visitApi } from '@/lib/services';
import type { Visit, Department } from '@/types';

const { Text } = Typography;
const { TextArea } = Input;

const triageCodeConfig: Record<string, { color: string; bg: string; label: string }> = {
    CODE_BLUE: { color: '#1677ff', bg: '#e6f4ff', label: 'Hồi sức cấp cứu (BLUE)' },
    CODE_RED: { color: '#ff4d4f', bg: '#fff1f0', label: 'Cấp cứu (RED)' },
    CODE_YELLOW: { color: '#faad14', bg: '#fffbe6', label: 'Ưu tiên (YELLOW)' },
    CODE_GREEN: { color: '#52c41a', bg: '#f6ffed', label: 'Bình thường (GREEN)' },
};

interface MatchedDepartment {
    code: string;
    name: string;
    specialties: string;
    score: string;
}

interface TriageModalProps {
    visit: Visit | null;
    open: boolean;
    departments: Department[];
    onClose: () => void;
    onSuccess: () => void;
}

export default function TriageModal({ visit, open, departments, onClose, onSuccess }: TriageModalProps) {
    const { message } = App.useApp();

    const [chiefComplaint, setChiefComplaint] = useState('');
    const [triageLoading, setTriageLoading] = useState(false);
    const [triageResult, setTriageResult] = useState<{
        ai_response: string;
        triage_code: string;
        recommended_department_name: string | null;
        triage_confidence: number;
        matched_departments: MatchedDepartment[];
    } | null>(null);
    const [selectedDeptId, setSelectedDeptId] = useState<string | null>(null);
    const [confirmLoading, setConfirmLoading] = useState(false);

    const handleAfterOpenChange = useCallback((isOpen: boolean) => {
        if (isOpen) {
            setChiefComplaint('');
            setTriageResult(null);
            setSelectedDeptId(null);
        }
    }, []);

    const handleRunTriage = async () => {
        if (!visit || !chiefComplaint.trim()) {
            message.warning('Vui lòng nhập triệu chứng / lý do khám');
            return;
        }
        setTriageLoading(true);
        try {
            const result = await visitApi.triage(visit.id, {
                chief_complaint: chiefComplaint,
            });
            setTriageResult({
                ai_response: result.ai_response,
                triage_code: result.triage_code || 'CODE_GREEN',
                recommended_department_name: result.recommended_department_name,
                triage_confidence: result.triage_confidence || 70,
                matched_departments: result.matched_departments || [],
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
        } catch (error) {
            console.error('Triage error:', error);
            message.error('Không thể gọi AI phân luồng');
        } finally {
            setTriageLoading(false);
        }
    };

    const handleConfirmTriage = async () => {
        if (!visit || !selectedDeptId) {
            message.warning('Vui lòng chọn khoa hướng đến');
            return;
        }
        setConfirmLoading(true);
        try {
            await visitApi.confirmTriage(visit.id, selectedDeptId);
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

    const handleSelectMatchedDept = (deptCode: string, deptName: string) => {
        const match = departments.find(d => d.code === deptCode);
        if (match) {
            setSelectedDeptId(match.id);
            message.info(`Đã chọn: ${deptName}`);
        }
    };

    const getPatientName = () => {
        if (!visit) return '';
        if (visit.patient_detail) {
            return visit.patient_detail.full_name || `${visit.patient_detail.last_name} ${visit.patient_detail.first_name}`;
        }
        if (typeof visit.patient === 'object') {
            return visit.patient.full_name || `${visit.patient.last_name} ${visit.patient.first_name}`;
        }
        return String(visit.patient);
    };

    const hasMatchedDepts = triageResult && triageResult.matched_departments.length > 0;

    return (
        <Modal
            title={
                <Space>
                    <RobotOutlined className="text-orange-500" />
                    <span style={{ fontSize: 16 }}>Phân luồng AI — {visit?.visit_code}</span>
                </Space>
            }
            open={open}
            onCancel={onClose}
            afterOpenChange={handleAfterOpenChange}
            footer={null}
            width={hasMatchedDepts ? 1060 : 750}
            destroyOnClose
        >
            {visit && (
                <div style={{ display: 'flex', gap: 16, marginTop: 16 }}>
                    {/* ========== CỘT TRÁI: Form + Kết quả AI ========== */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                        {/* Thông tin bệnh nhân */}
                        <Card size="small" className="bg-gray-50">
                            <Descriptions size="small" column={2} style={{ fontSize: 14 }}>
                                <Descriptions.Item label="Bệnh nhân">{getPatientName()}</Descriptions.Item>
                                <Descriptions.Item label="Mã khám">{visit.visit_code}</Descriptions.Item>
                            </Descriptions>
                        </Card>

                        {/* Nhập triệu chứng */}
                        <div style={{ marginTop: 12 }}>
                            <Text strong style={{ fontSize: 15 }}>Triệu chứng / Lý do khám:</Text>
                            <TextArea
                                rows={3}
                                placeholder="Nhập triệu chứng chính, ví dụ: Đau ngực trái, khó thở, buồn nôn..."
                                value={chiefComplaint}
                                onChange={(e) => setChiefComplaint(e.target.value)}
                                disabled={triageLoading}
                                style={{ marginTop: 8, fontSize: 14 }}
                            />
                            <Button
                                type="primary"
                                icon={<RobotOutlined />}
                                loading={triageLoading}
                                onClick={handleRunTriage}
                                style={{ marginTop: 12 }}
                                block
                                size="large"
                                disabled={!chiefComplaint.trim()}
                            >
                                {triageLoading ? 'AI đang phân tích...' : 'Gọi AI Phân luồng'}
                            </Button>
                        </div>

                        {/* Loading */}
                        {triageLoading && (
                            <div className="text-center py-4">
                                <Spin size="large" />
                                <div className="mt-2 text-gray-500">AI đang phân tích triệu chứng...</div>
                            </div>
                        )}

                        {/* Kết quả AI — Alert + Phân tích ở cột trái */}
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
                                    message={
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

                                {/* AI Reasoning */}
                                <Card
                                    size="small"
                                    title={<Text type="secondary" style={{ fontSize: 14 }}><RobotOutlined /> Phân tích AI</Text>}
                                    className="bg-blue-50"
                                    styles={{ body: { maxHeight: 200, overflow: 'auto' } }}
                                >
                                    <div style={{ whiteSpace: 'pre-wrap', fontSize: 14 }}>
                                        {triageResult.ai_response}
                                    </div>
                                </Card>
                            </div>
                        )}
                    </div>

                    {/* ========== CỘT PHẢI: Khoa phù hợp + Xác nhận ========== */}
                    {hasMatchedDepts && (
                        <div style={{
                            width: 320,
                            flexShrink: 0,
                            display: 'flex',
                            flexDirection: 'column',
                            gap: 12,
                        }}>
                            {/* Danh sách khoa phù hợp */}
                            <Card
                                size="small"
                                title={
                                    <Space size={4}>
                                        <MedicineBoxOutlined style={{ color: '#1677ff' }} />
                                        <Text strong style={{ fontSize: 14 }}>Khoa phù hợp theo triệu chứng</Text>
                                        <Tag color="blue" style={{ marginLeft: 4, fontSize: 13 }}>
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
                                                            ? '2px solid #1677ff'
                                                            : '1px solid #f0f0f0',
                                                        background: isSelected ? '#e6f4ff' : '#fafafa',
                                                        cursor: 'pointer',
                                                        transition: 'all 0.2s',
                                                        display: 'flex',
                                                        alignItems: 'flex-start',
                                                        gap: 8,
                                                    }}
                                                    onMouseEnter={(e) => {
                                                        if (!isSelected) {
                                                            e.currentTarget.style.borderColor = '#1677ff';
                                                            e.currentTarget.style.background = '#f0f7ff';
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
                                                            backgroundColor: idx === 0 ? '#1677ff' : '#d9d9d9',
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

                            {/* Xác nhận khoa — ở cột phải, dưới danh sách */}
                            <Card
                                size="small"
                                title={<Text strong style={{ fontSize: 14 }}>Xác nhận khoa hướng đến</Text>}
                                styles={{
                                    header: { padding: '8px 12px', minHeight: 'auto' },
                                    body: { padding: '8px 12px' },
                                }}
                                style={{ border: '2px solid #1677ff' }}
                            >
                                <Space direction="vertical" className="w-full" size={8}>
                                    <Select
                                        placeholder="Chọn khoa..."
                                        value={selectedDeptId}
                                        onChange={(val) => setSelectedDeptId(val)}
                                        className="w-full"
                                        showSearch
                                        optionFilterProp="label"
                                        options={departments.map(d => ({
                                            value: d.id,
                                            label: `${d.code} — ${d.name}`,
                                        }))}
                                    />
                                    <Button
                                        type="primary"
                                        icon={<CheckOutlined />}
                                        onClick={handleConfirmTriage}
                                        loading={confirmLoading}
                                        block
                                        disabled={!selectedDeptId}
                                        style={{ backgroundColor: '#52c41a', borderColor: '#52c41a', fontSize: 20, height: 70 }}
                                    >
                                        Xác nhận phân luồng
                                    </Button>
                                </Space>
                            </Card>
                        </div>
                    )}
                </div>
            )}
        </Modal>
    );
}
