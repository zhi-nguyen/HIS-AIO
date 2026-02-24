'use client';

import { useState, useEffect, useCallback } from 'react';
import {
    Card,
    Form,
    Input,
    Button,
    Space,
    Tag,
    Typography,
    Descriptions,
    Divider,
    Alert,
    Spin,
    InputNumber,
    Row,
    Col,
    Tabs,
    App,
} from 'antd';
import {
    SaveOutlined,
    HeartOutlined,
    FileTextOutlined,
    MedicineBoxOutlined,
    ExperimentOutlined,
    CheckCircleOutlined,
    ArrowLeftOutlined,
} from '@ant-design/icons';
import { visitApi, emrApi, aiApi } from '@/lib/services';
import type { Visit, Patient } from '@/types';
import { useRouter, useParams } from 'next/navigation';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { TextArea } = Input;

/**
 * Clinical Examination Page
 * Giao diện khám bệnh chính
 */

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

export default function ClinicalExamPage() {
    const { message } = App.useApp();
    const router = useRouter();
    const params = useParams();
    const visitId = params.visitId as string;

    const [visit, setVisit] = useState<Visit | null>(null);
    const [record, setRecord] = useState<ClinicalRecord | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [aiLoading, setAiLoading] = useState(false);
    const [vitalsAssessment, setVitalsAssessment] = useState<Record<string, unknown> | null>(null);

    const [form] = Form.useForm();

    // Fetch visit and clinical record
    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const visitData = await visitApi.getById(visitId);
            setVisit(visitData);

            // Try to get existing clinical record
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

    // Save clinical record
    const handleSave = async (values: Record<string, unknown>) => {
        setSaving(true);
        try {
            const vitalSigns: VitalSigns = {
                temperature: values.temperature as number,
                systolic_bp: values.systolic_bp as number,
                diastolic_bp: values.diastolic_bp as number,
                heart_rate: values.heart_rate as number,
                respiratory_rate: values.respiratory_rate as number,
                spo2: values.spo2 as number,
                weight: values.weight as number,
                height: values.height as number,
            };

            const data = {
                chief_complaint: values.chief_complaint as string,
                history_of_present_illness: values.history_of_present_illness as string,
                physical_exam: values.physical_exam as string,
                final_diagnosis: values.final_diagnosis as string,
                treatment_plan: values.treatment_plan as string,
                vital_signs: vitalSigns,
            };

            if (record) {
                await emrApi.update(record.id, data);
                message.success('Đã lưu hồ sơ');
            } else {
                const newRecord = await emrApi.create({
                    visit: visitId,
                    chief_complaint: data.chief_complaint,
                    vital_signs: vitalSigns,
                });
                setRecord(newRecord);
                message.success('Đã tạo hồ sơ bệnh án');
            }
        } catch (error) {
            console.error('Error saving:', error);
            message.error('Không thể lưu hồ sơ');
        } finally {
            setSaving(false);
        }
    };

    // Assess vitals with AI
    const handleAssessVitals = async () => {
        const values = form.getFieldsValue();
        const vitalSigns: VitalSigns = {
            temperature: values.temperature,
            systolic_bp: values.systolic_bp,
            diastolic_bp: values.diastolic_bp,
            heart_rate: values.heart_rate,
            respiratory_rate: values.respiratory_rate,
            spo2: values.spo2,
        };

        // Check if any values provided
        if (!Object.values(vitalSigns).some(v => v !== undefined)) {
            message.warning('Vui lòng nhập ít nhất một chỉ số sinh hiệu');
            return;
        }

        setAiLoading(true);
        try {
            const result = await aiApi.vitalsAssess(vitalSigns);
            setVitalsAssessment(result);
            message.success('Đã đánh giá sinh hiệu');
        } catch (error) {
            console.error('Error assessing vitals:', error);
            message.error('Không thể đánh giá sinh hiệu');
        } finally {
            setAiLoading(false);
        }
    };

    // Finalize examination
    const handleFinalize = async () => {
        if (!record) {
            message.warning('Vui lòng lưu hồ sơ trước');
            return;
        }

        try {
            await emrApi.update(record.id, { is_finalized: true });
            await visitApi.update(visitId, { status: 'COMPLETED' });
            message.success('Đã hoàn thành khám');
            router.push('/dashboard/clinical');
        } catch (error) {
            console.error('Error finalizing:', error);
            message.error('Không thể hoàn tất khám');
        }
    };

    const patient = typeof visit?.patient === 'object' ? visit.patient as Patient : null;

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[400px]">
                <Spin size="large" />
                <div className="mt-2">Đang tải...</div>
            </div>
        );
    }

    return (
        <div className="space-y-4">
            {/* Header */}
            <div className="flex justify-between items-center">
                <Space>
                    <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/dashboard/clinical')}>
                        Quay lại
                    </Button>
                    <div>
                        <Title level={3} className="!mb-0">Khám bệnh</Title>
                        <Text type="secondary">Mã khám: {visit?.visit_code}</Text>
                    </div>
                </Space>
                <Space>
                    <Button icon={<SaveOutlined />} loading={saving} onClick={() => form.submit()}>
                        Lưu
                    </Button>
                    <Button
                        type="primary"
                        icon={<CheckCircleOutlined />}
                        onClick={handleFinalize}
                        disabled={!record}
                    >
                        Hoàn thành khám
                    </Button>
                </Space>
            </div>

            {/* Patient Info */}
            {patient && (
                <Card size="small">
                    <Descriptions size="small" column={4}>
                        <Descriptions.Item label="Họ tên">
                            <Text strong>{patient.full_name || `${patient.last_name} ${patient.first_name}`}</Text>
                        </Descriptions.Item>
                        <Descriptions.Item label="Mã BN">{patient.patient_code}</Descriptions.Item>
                        <Descriptions.Item label="Ngày sinh">
                            {patient.date_of_birth ? dayjs(patient.date_of_birth).format('DD/MM/YYYY') : '-'}
                        </Descriptions.Item>
                        <Descriptions.Item label="Giới tính">
                            {patient.gender === 'M' ? 'Nam' : patient.gender === 'F' ? 'Nữ' : 'Khác'}
                        </Descriptions.Item>
                    </Descriptions>
                </Card>
            )}

            {/* Main Form */}
            <Form form={form} layout="vertical" onFinish={handleSave}>
                <Tabs
                    defaultActiveKey="exam"
                    items={[
                        {
                            key: 'exam',
                            label: <><FileTextOutlined /> Khám bệnh</>,
                            children: (
                                <Card>
                                    <Form.Item
                                        name="chief_complaint"
                                        label="Lý do vào viện / Triệu chứng chính"
                                        rules={[{ required: true, message: 'Vui lòng nhập' }]}
                                    >
                                        <TextArea rows={3} placeholder="Mô tả triệu chứng chính của bệnh nhân..." />
                                    </Form.Item>

                                    <Form.Item name="history_of_present_illness" label="Bệnh sử">
                                        <TextArea rows={4} placeholder="Diễn biến bệnh từ khi khởi phát..." />
                                    </Form.Item>

                                    <Form.Item name="physical_exam" label="Khám lâm sàng">
                                        <TextArea rows={4} placeholder="Kết quả khám thực thể..." />
                                    </Form.Item>

                                    <Divider />

                                    <Form.Item name="final_diagnosis" label="Chẩn đoán">
                                        <TextArea rows={2} placeholder="Chẩn đoán bệnh..." />
                                    </Form.Item>

                                    <Form.Item name="treatment_plan" label="Phương pháp điều trị">
                                        <TextArea rows={3} placeholder="Kế hoạch điều trị..." />
                                    </Form.Item>
                                </Card>
                            ),
                        },
                        {
                            key: 'vitals',
                            label: <><HeartOutlined /> Sinh hiệu</>,
                            children: (
                                <Card
                                    extra={
                                        <Button
                                            type="primary"
                                            icon={<MedicineBoxOutlined />}
                                            onClick={handleAssessVitals}
                                            loading={aiLoading}
                                        >
                                            Đánh giá AI
                                        </Button>
                                    }
                                >
                                    <Row gutter={16}>
                                        <Col span={6}>
                                            <Form.Item name="temperature" label="Nhiệt độ (°C)">
                                                <InputNumber min={35} max={42} step={0.1} className="w-full" />
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item name="heart_rate" label="Mạch (bpm)">
                                                <InputNumber min={30} max={200} className="w-full" />
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item name="systolic_bp" label="HA Tâm thu (mmHg)">
                                                <InputNumber min={60} max={250} className="w-full" />
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item name="diastolic_bp" label="HA Tâm trương (mmHg)">
                                                <InputNumber min={40} max={150} className="w-full" />
                                            </Form.Item>
                                        </Col>
                                    </Row>
                                    <Row gutter={16}>
                                        <Col span={6}>
                                            <Form.Item name="respiratory_rate" label="Nhịp thở (/phút)">
                                                <InputNumber min={8} max={40} className="w-full" />
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item name="spo2" label="SpO2 (%)">
                                                <InputNumber min={70} max={100} className="w-full" />
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item name="weight" label="Cân nặng (kg)">
                                                <InputNumber min={1} max={300} step={0.1} className="w-full" />
                                            </Form.Item>
                                        </Col>
                                        <Col span={6}>
                                            <Form.Item name="height" label="Chiều cao (cm)">
                                                <InputNumber min={30} max={250} className="w-full" />
                                            </Form.Item>
                                        </Col>
                                    </Row>

                                    {vitalsAssessment && (
                                        <Alert
                                            message="Kết quả đánh giá sinh hiệu"
                                            description={
                                                <pre className="text-sm mt-2">
                                                    {JSON.stringify(vitalsAssessment, null, 2)}
                                                </pre>
                                            }
                                            type="info"
                                            showIcon
                                            icon={<MedicineBoxOutlined />}
                                            className="mt-4"
                                        />
                                    )}
                                </Card>
                            ),
                        },
                        {
                            key: 'orders',
                            label: <><ExperimentOutlined /> Chỉ định CLS</>,
                            children: (
                                <Card>
                                    <div className="text-center py-8 text-gray-500">
                                        <ExperimentOutlined className="text-4xl mb-2" />
                                        <div>Chỉ định xét nghiệm và CĐHA sẽ được triển khai ở Phase 4</div>
                                    </div>
                                </Card>
                            ),
                        },
                        {
                            key: 'prescription',
                            label: <><MedicineBoxOutlined /> Kê đơn</>,
                            children: (
                                <Card>
                                    <div className="text-center py-8 text-gray-500">
                                        <MedicineBoxOutlined className="text-4xl mb-2" />
                                        <div>Kê đơn thuốc sẽ được triển khai ở Phase 5</div>
                                    </div>
                                </Card>
                            ),
                        },
                    ]}
                />
            </Form>

            {/* AI Suggestions */}
            {record?.ai_suggestion_json && (
                <Card title={<><MedicineBoxOutlined /> Gợi ý từ AI</>} size="small">
                    <pre className="text-sm bg-gray-50 p-3 rounded">
                        {JSON.stringify(record.ai_suggestion_json, null, 2)}
                    </pre>
                </Card>
            )}
        </div>
    );
}
