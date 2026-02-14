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
} from 'antd';
import {
    RobotOutlined,
    CheckOutlined,
} from '@ant-design/icons';
import { visitApi } from '@/lib/services';
import type { Visit, Department } from '@/types';

const { Text } = Typography;
const { TextArea } = Input;

const triageCodeConfig: Record<string, { color: string; bg: string; label: string }> = {
    CODE_RED: { color: '#ff4d4f', bg: '#fff1f0', label: 'Cấp cứu (RED)' },
    CODE_YELLOW: { color: '#faad14', bg: '#fffbe6', label: 'Ưu tiên (YELLOW)' },
    CODE_GREEN: { color: '#52c41a', bg: '#f6ffed', label: 'Bình thường (GREEN)' },
};

interface TriageModalProps {
    visit: Visit | null;
    open: boolean;
    departments: Department[];
    onClose: () => void;
    onSuccess: () => void;
}

/**
 * TriageModal — Component riêng cho phân luồng AI
 * Tách ra khỏi ReceptionPage để tránh re-render Table khi gõ ký tự.
 */
export default function TriageModal({ visit, open, departments, onClose, onSuccess }: TriageModalProps) {
    const { message } = App.useApp();

    const [chiefComplaint, setChiefComplaint] = useState('');
    const [triageLoading, setTriageLoading] = useState(false);
    const [triageResult, setTriageResult] = useState<{
        ai_response: string;
        triage_code: string;
        recommended_department_name: string | null;
        triage_confidence: number;
    } | null>(null);
    const [selectedDeptId, setSelectedDeptId] = useState<string | null>(null);
    const [confirmLoading, setConfirmLoading] = useState(false);

    // Reset state khi mở modal
    const handleAfterOpenChange = useCallback((isOpen: boolean) => {
        if (isOpen) {
            setChiefComplaint('');
            setTriageResult(null);
            setSelectedDeptId(null);
        }
    }, []);

    // Gọi AI phân luồng
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
            });
            // Auto-select recommended department
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

    // Xác nhận triage
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

    // Lấy tên bệnh nhân
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

    return (
        <Modal
            title={
                <Space>
                    <RobotOutlined className="text-orange-500" />
                    <span>Phân luồng AI — {visit?.visit_code}</span>
                </Space>
            }
            open={open}
            onCancel={onClose}
            afterOpenChange={handleAfterOpenChange}
            footer={null}
            width={700}
            destroyOnClose
        >
            {visit && (
                <div className="space-y-4 mt-4">
                    {/* Thông tin bệnh nhân */}
                    <Card size="small" className="bg-gray-50">
                        <Descriptions size="small" column={2}>
                            <Descriptions.Item label="Bệnh nhân">{getPatientName()}</Descriptions.Item>
                            <Descriptions.Item label="Mã khám">{visit.visit_code}</Descriptions.Item>
                        </Descriptions>
                    </Card>

                    {/* Bước 1: Nhập triệu chứng */}
                    <div>
                        <Text strong>Triệu chứng / Lý do khám:</Text>
                        <TextArea
                            rows={3}
                            placeholder="Nhập triệu chứng chính, ví dụ: Đau ngực trái, khó thở, buồn nôn..."
                            value={chiefComplaint}
                            onChange={(e) => setChiefComplaint(e.target.value)}
                            disabled={triageLoading}
                            className="mt-2"
                        />
                        <Button
                            type="primary"
                            icon={<RobotOutlined />}
                            loading={triageLoading}
                            onClick={handleRunTriage}
                            className="mt-3"
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

                    {/* Bước 2: Kết quả AI */}
                    {triageResult && !triageLoading && (
                        <div className="space-y-3">
                            <Alert
                                type={
                                    triageResult.triage_code === 'CODE_RED' ? 'error'
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
                                        <Text strong>
                                            {triageCodeConfig[triageResult.triage_code]?.label || triageResult.triage_code}
                                        </Text>
                                    </Space>
                                }
                                description={
                                    <div className="mt-2 space-y-2">
                                        <div>
                                            <Text strong>Khoa đề xuất: </Text>
                                            <Tag color="blue">{triageResult.recommended_department_name || 'Không xác định'}</Tag>
                                        </div>
                                        <div>
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
                                title={<Text type="secondary"><RobotOutlined /> Phân tích AI</Text>}
                                className="bg-blue-50"
                                styles={{ body: { maxHeight: 200, overflow: 'auto' } }}
                            >
                                <div style={{ whiteSpace: 'pre-wrap', fontSize: 13 }}>
                                    {triageResult.ai_response}
                                </div>
                            </Card>

                            {/* Bước 3: Chọn khoa và xác nhận */}
                            <Card size="small" title="Xác nhận khoa hướng đến">
                                <Space direction="vertical" className="w-full">
                                    <Select
                                        placeholder="Chọn hoặc sửa khoa hướng đến..."
                                        value={selectedDeptId}
                                        onChange={(val) => setSelectedDeptId(val)}
                                        className="w-full"
                                        size="large"
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
                                        size="large"
                                        disabled={!selectedDeptId}
                                        style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
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
