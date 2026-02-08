'use client';

import { useState } from 'react';
import {
    Card,
    Form,
    Input,
    Select,
    InputNumber,
    Button,
    Typography,
    Space,
    Divider,
    Alert,
    message,
    Spin,
} from 'antd';
import {
    AlertOutlined,
    HeartOutlined,
    ThunderboltOutlined,
} from '@ant-design/icons';
import { aiApi } from '@/lib/services';

const { Title, Text } = Typography;
const { TextArea } = Input;

/**
 * Triage Assessment Form
 * Form đánh giá phân loại bệnh nhân với AI
 */

interface TriageResult {
    triage_level: number;
    triage_color: string;
    triage_name: string;
    reasoning: string;
    recommendations: string[];
}

interface TriageFormProps {
    visitId: string;
    patientName?: string;
    onComplete?: (result: TriageResult) => void;
}

const triageColors: Record<number, { color: string; bg: string; name: string }> = {
    1: { color: '#ff4d4f', bg: '#fff1f0', name: 'Cấp cứu' },
    2: { color: '#fa8c16', bg: '#fff7e6', name: 'Khẩn cấp' },
    3: { color: '#fadb14', bg: '#fffbe6', name: 'Ưu tiên' },
    4: { color: '#52c41a', bg: '#f6ffed', name: 'Thường' },
    5: { color: '#1890ff', bg: '#e6f7ff', name: 'Không cấp' },
};

export default function TriageForm({ visitId, patientName, onComplete }: TriageFormProps) {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<TriageResult | null>(null);

    const handleSubmit = async (values: Record<string, unknown>) => {
        setLoading(true);
        try {
            const response = await aiApi.triageAssess({
                visit_id: visitId,
                chief_complaint: values.chief_complaint as string,
                vital_signs: {
                    heart_rate: values.heart_rate as number,
                    blood_pressure_systolic: values.bp_systolic as number,
                    blood_pressure_diastolic: values.bp_diastolic as number,
                    respiratory_rate: values.respiratory_rate as number,
                    temperature: values.temperature as number,
                    spo2: values.spo2 as number,
                },
                pain_scale: values.pain_scale as number,
                consciousness: values.consciousness as string,
                onset: values.onset as string,
            });

            setResult(response);
            message.success('Đánh giá hoàn tất');
            onComplete?.(response);
        } catch (error) {
            console.error('Triage error:', error);
            message.error('Không thể đánh giá. Vui lòng thử lại.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <Card className="max-w-2xl mx-auto">
            <Title level={4}>
                <Space>
                    <AlertOutlined className="text-red-500" />
                    Đánh giá phân loại (Triage)
                </Space>
            </Title>
            {patientName && <Text type="secondary">Bệnh nhân: {patientName}</Text>}

            <Divider />

            <Form form={form} layout="vertical" onFinish={handleSubmit}>
                {/* Chief Complaint */}
                <Form.Item
                    name="chief_complaint"
                    label="Lý do đến khám / Triệu chứng chính"
                    rules={[{ required: true, message: 'Vui lòng nhập triệu chứng' }]}
                >
                    <TextArea rows={3} placeholder="Mô tả triệu chứng chính của bệnh nhân..." />
                </Form.Item>

                {/* Vital Signs */}
                <Title level={5}>
                    <HeartOutlined className="text-pink-500 mr-2" />
                    Sinh hiệu
                </Title>
                <div className="grid grid-cols-3 gap-4">
                    <Form.Item name="heart_rate" label="Mạch (bpm)">
                        <InputNumber className="w-full" min={0} max={300} placeholder="72" />
                    </Form.Item>
                    <Form.Item label="Huyết áp (mmHg)">
                        <Space.Compact className="w-full">
                            <Form.Item name="bp_systolic" noStyle>
                                <InputNumber placeholder="120" min={0} max={300} />
                            </Form.Item>
                            <span className="px-2 py-1 bg-gray-100">/</span>
                            <Form.Item name="bp_diastolic" noStyle>
                                <InputNumber placeholder="80" min={0} max={200} />
                            </Form.Item>
                        </Space.Compact>
                    </Form.Item>
                    <Form.Item name="respiratory_rate" label="Nhịp thở (/phút)">
                        <InputNumber className="w-full" min={0} max={60} placeholder="16" />
                    </Form.Item>
                    <Form.Item name="temperature" label="Nhiệt độ (°C)">
                        <InputNumber className="w-full" min={30} max={45} step={0.1} placeholder="37.0" />
                    </Form.Item>
                    <Form.Item name="spo2" label="SpO2 (%)">
                        <InputNumber className="w-full" min={0} max={100} placeholder="98" />
                    </Form.Item>
                    <Form.Item name="pain_scale" label="Đau (0-10)">
                        <InputNumber className="w-full" min={0} max={10} placeholder="0" />
                    </Form.Item>
                </div>

                {/* Clinical Status */}
                <Title level={5}>
                    <ThunderboltOutlined className="text-yellow-500 mr-2" />
                    Trạng thái lâm sàng
                </Title>
                <div className="grid grid-cols-2 gap-4">
                    <Form.Item name="consciousness" label="Ý thức">
                        <Select placeholder="Chọn trạng thái">
                            <Select.Option value="alert">Tỉnh táo (Alert)</Select.Option>
                            <Select.Option value="verbal">Đáp ứng lời nói (Verbal)</Select.Option>
                            <Select.Option value="pain">Đáp ứng đau (Pain)</Select.Option>
                            <Select.Option value="unresponsive">Không đáp ứng (Unresponsive)</Select.Option>
                        </Select>
                    </Form.Item>
                    <Form.Item name="onset" label="Thời gian khởi phát">
                        <Select placeholder="Chọn thời gian">
                            <Select.Option value="minutes">Vài phút trước</Select.Option>
                            <Select.Option value="hours">Vài giờ trước</Select.Option>
                            <Select.Option value="today">Hôm nay</Select.Option>
                            <Select.Option value="days">Vài ngày trước</Select.Option>
                            <Select.Option value="weeks">Hơn 1 tuần</Select.Option>
                        </Select>
                    </Form.Item>
                </div>

                <Form.Item className="mt-4">
                    <Button type="primary" htmlType="submit" loading={loading} block size="large">
                        Đánh giá với AI
                    </Button>
                </Form.Item>
            </Form>

            {/* Result */}
            {loading && (
                <div className="text-center py-4">
                    <Spin tip="Đang phân tích..." />
                </div>
            )}

            {result && (
                <Alert
                    type={result.triage_level <= 2 ? 'error' : result.triage_level === 3 ? 'warning' : 'success'}
                    showIcon
                    message={
                        <Space>
                            <span
                                className="inline-block w-4 h-4 rounded-full"
                                style={{ backgroundColor: triageColors[result.triage_level]?.color }}
                            />
                            <Text strong>
                                Mức {result.triage_level}: {triageColors[result.triage_level]?.name}
                            </Text>
                        </Space>
                    }
                    description={
                        <div className="mt-2 space-y-2">
                            <div>
                                <Text strong>Lý do: </Text>
                                <Text>{result.reasoning}</Text>
                            </div>
                            {result.recommendations?.length > 0 && (
                                <div>
                                    <Text strong>Khuyến nghị:</Text>
                                    <ul className="list-disc ml-5 mt-1">
                                        {result.recommendations.map((r, i) => (
                                            <li key={i}><Text>{r}</Text></li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    }
                />
            )}
        </Card>
    );
}
