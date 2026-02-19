'use client';

import { useState, useCallback, useRef } from 'react';
import {
    Card,
    Input,
    Button,
    Typography,
    Space,
    Steps,
    Result,
    Alert,
    App,
    Spin,
    Divider,
} from 'antd';
import {
    QrcodeOutlined,
    EditOutlined,
    CheckCircleOutlined,
    IdcardOutlined,
    LoadingOutlined,
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

/**
 * Kiosk Tự Phục Vụ — Bệnh nhân đăng ký khám
 * 
 * Luồng:
 * 1. Quét QR CCCD/BHYT (hoặc nhập tay fallback)
 * 2. Nhập lý do khám
 * 3. Xác nhận → Nhận số thứ tự
 * 
 * Bảo vệ 3 Lớp (UI side):
 * - Lớp 1: Ưu tiên quét QR, hạn chế nhập tay
 * - Lớp 2: Kiểm tra lượt khám active trước khi đăng ký
 * - Lớp 3: Cooldown sau submit (chống spam)
 */

interface KioskResult {
    queue_number: string;
    visit_code: string;
    message: string;
}

interface TriageFormProps {
    onComplete?: (result: KioskResult) => void;
}

export default function TriageForm({ onComplete }: TriageFormProps) {
    const { message: messageApi } = App.useApp();

    // --- Wizard step ---
    const [currentStep, setCurrentStep] = useState(0);

    // --- Step 1: Xác thực danh tính ---
    const identityCodeRef = useRef('');
    const [identityMethod, setIdentityMethod] = useState<'qr' | 'manual'>('qr');
    const [scanLoading, setScanLoading] = useState(false);
    const [patientFound, setPatientFound] = useState<{
        name: string;
        patient_id: string;
        dob?: string;
        gender?: string;
    } | null>(null);
    const [identityError, setIdentityError] = useState('');

    // --- Step 2: Lý do khám (uncontrolled — chỉ đọc khi submit) ---
    const chiefComplaintRef = useRef('');
    const [hasComplaint, setHasComplaint] = useState(false);

    // --- Step 3: Kết quả ---
    const [submitLoading, setSubmitLoading] = useState(false);
    const [kioskResult, setKioskResult] = useState<KioskResult | null>(null);
    const [cooldown, setCooldown] = useState(false);

    // ========================================================================
    // Step 1: Quét / Nhập CCCD/BHYT
    // ========================================================================
    const handleScanQR = useCallback(() => {
        // Placeholder: Trong thực tế, sẽ kết nối đầu đọc QR/chip CCCD
        setScanLoading(true);
        messageApi.info('Vui lòng đưa CCCD/BHYT vào đầu đọc...');

        // Simulate QR scan (sẽ thay bằng WebSocket/hardware API)
        setTimeout(() => {
            setScanLoading(false);
            messageApi.warning('Chức năng quét QR sẽ được kết nối với phần cứng. Vui lòng nhập tay.');
            setIdentityMethod('manual');
        }, 2000);
    }, [messageApi]);

    const handleLookupIdentity = async () => {
        if (!identityCodeRef.current.trim()) {
            messageApi.warning('Vui lòng nhập số CCCD hoặc mã BHYT');
            return;
        }

        setIdentityError('');
        setScanLoading(true);

        try {
            // TODO: Gọi API tìm bệnh nhân + kiểm tra lượt khám active (Lớp 2)
            // const result = await patientApi.lookupByIdentity(identityCode);
            // Lớp 2: Backend sẽ reject nếu đã có lượt khám active hôm nay

            // Mock response — sẽ thay bằng API call thật
            await new Promise(resolve => setTimeout(resolve, 1000));

            // Simulate: tìm thấy bệnh nhân
            setPatientFound({
                name: 'Nguyễn Văn A',
                patient_id: 'mock-patient-id',
                dob: '1990-01-15',
                gender: 'Nam',
            });
            setCurrentStep(1);
            messageApi.success('Đã xác thực danh tính thành công!');
        } catch (err: unknown) {
            const error = err as { response?: { data?: { message?: string } } };
            const errorMsg = error?.response?.data?.message || 'Không thể tra cứu. Vui lòng thử lại.';
            setIdentityError(errorMsg);
            messageApi.error(errorMsg);
        } finally {
            setScanLoading(false);
        }
    };

    // ========================================================================
    // Step 2 → 3: Submit đăng ký khám
    // ========================================================================
    const handleSubmitRegistration = async () => {
        if (!chiefComplaintRef.current.trim()) {
            messageApi.warning('Vui lòng nhập lý do khám');
            return;
        }
        if (!patientFound) return;

        // Lớp 3: Cooldown chống spam
        if (cooldown) {
            messageApi.warning('Vui lòng đợi trước khi đăng ký lại');
            return;
        }

        setSubmitLoading(true);
        try {
            // TODO: Gọi API đăng ký khám
            // const result = await visitApi.kioskRegister({
            //     patient_id: patientFound.patient_id,
            //     chief_complaint: chiefComplaint,
            // });

            // Mock response
            await new Promise(resolve => setTimeout(resolve, 1500));

            const result: KioskResult = {
                queue_number: 'A-042',
                visit_code: 'V20260216-ABC123',
                message: 'Đăng ký thành công! Vui lòng chờ gọi số để đo sinh hiệu.',
            };

            setKioskResult(result);
            setCurrentStep(2);
            onComplete?.(result);

            // Lớp 3: Enable cooldown 5s
            setCooldown(true);
            setTimeout(() => setCooldown(false), 5000);
        } catch (err: unknown) {
            const error = err as { response?: { data?: { message?: string } } };
            const errorMsg = error?.response?.data?.message || 'Không thể đăng ký. Vui lòng thử lại.';
            messageApi.error(errorMsg);
        } finally {
            setSubmitLoading(false);
        }
    };

    // --- Reset toàn bộ ---
    const handleReset = () => {
        setCurrentStep(0);
        identityCodeRef.current = '';
        setIdentityMethod('qr');
        setPatientFound(null);
        setIdentityError('');
        chiefComplaintRef.current = '';
        setHasComplaint(false);
        setKioskResult(null);
    };

    // ========================================================================
    // RENDER
    // ========================================================================
    return (
        <Card
            className="max-w-2xl mx-auto"
            style={{
                borderRadius: 16,
                boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
            }}
        >
            <Title level={3} style={{ textAlign: 'center', marginBottom: 8 }}>
                <IdcardOutlined style={{ color: '#1677ff', marginRight: 8 }} />
                Đăng Ký Khám Bệnh
            </Title>
            <Paragraph type="secondary" style={{ textAlign: 'center', marginBottom: 24 }}>
                Kiosk tự phục vụ — Quét CCCD/BHYT để bắt đầu
            </Paragraph>

            {/* Progress Steps */}
            <Steps
                current={currentStep}
                style={{ marginBottom: 32 }}
                items={[
                    { title: 'Xác thực', description: 'Quét CCCD/BHYT' },
                    { title: 'Lý do khám', description: 'Mô tả triệu chứng' },
                    { title: 'Hoàn tất', description: 'Nhận số thứ tự' },
                ]}
            />

            {/* ============ STEP 1: Xác thực danh tính ============ */}
            {currentStep === 0 && (
                <div>
                    {/* Quét QR (ưu tiên — Lớp 1 Hardware) */}
                    <Card
                        size="small"
                        style={{
                            textAlign: 'center',
                            border: identityMethod === 'qr' ? '2px solid #1677ff' : '1px solid #f0f0f0',
                            borderRadius: 12,
                            marginBottom: 16,
                            padding: '24px 16px',
                            cursor: 'pointer',
                            background: identityMethod === 'qr' ? '#e6f4ff' : '#fafafa',
                        }}
                        onClick={() => setIdentityMethod('qr')}
                    >
                        <QrcodeOutlined style={{ fontSize: 48, color: '#1677ff' }} />
                        <Title level={5} style={{ marginTop: 8, marginBottom: 4 }}>
                            Quét mã QR trên CCCD/BHYT
                        </Title>
                        <Text type="secondary">Nhanh chóng, chính xác 100%</Text>
                        {identityMethod === 'qr' && (
                            <div style={{ marginTop: 16 }}>
                                <Button
                                    type="primary"
                                    size="large"
                                    icon={scanLoading ? <LoadingOutlined /> : <QrcodeOutlined />}
                                    onClick={(e) => { e.stopPropagation(); handleScanQR(); }}
                                    loading={scanLoading}
                                    style={{ height: 56, fontSize: 18, paddingInline: 40 }}
                                >
                                    {scanLoading ? 'Đang quét...' : 'Bắt đầu quét'}
                                </Button>
                            </div>
                        )}
                    </Card>

                    <Divider>hoặc</Divider>

                    {/* Nhập tay (fallback) */}
                    <Card
                        size="small"
                        style={{
                            border: identityMethod === 'manual' ? '2px solid #1677ff' : '1px solid #f0f0f0',
                            borderRadius: 12,
                            cursor: 'pointer',
                            background: identityMethod === 'manual' ? '#e6f4ff' : '#fafafa',
                        }}
                        onClick={() => setIdentityMethod('manual')}
                    >
                        <Space size={8} align="center" style={{ marginBottom: 12 }}>
                            <EditOutlined style={{ color: '#8c8c8c' }} />
                            <Text strong>Nhập tay số CCCD / Mã BHYT</Text>
                            <Text type="secondary" style={{ fontSize: 12 }}>(Nếu không quét được)</Text>
                        </Space>

                        {identityMethod === 'manual' && (
                            <div>
                                <Input
                                    size="large"
                                    placeholder="Nhập 12 số CCCD hoặc mã BHYT..."
                                    defaultValue=""
                                    onChange={e => { identityCodeRef.current = e.target.value; }}
                                    maxLength={15}
                                    style={{ fontSize: 18, height: 56, marginBottom: 12 }}
                                    onPressEnter={handleLookupIdentity}
                                />
                                <Button
                                    type="primary"
                                    size="large"
                                    block
                                    onClick={handleLookupIdentity}
                                    loading={scanLoading}
                                    style={{ height: 52, fontSize: 16 }}
                                >
                                    Tra cứu
                                </Button>
                            </div>
                        )}
                    </Card>

                    {identityError && (
                        <Alert
                            type="error"
                            showIcon
                            message={identityError}
                            style={{ marginTop: 16, borderRadius: 8 }}
                        />
                    )}
                </div>
            )}

            {/* ============ STEP 2: Nhập lý do khám ============ */}
            {currentStep === 1 && patientFound && (
                <div>
                    {/* Thông tin bệnh nhân đã xác thực */}
                    <Alert
                        type="success"
                        showIcon
                        icon={<CheckCircleOutlined />}
                        message={
                            <Text strong>Xin chào, {patientFound.name}</Text>
                        }
                        description={
                            <Space>
                                {patientFound.dob && <Text type="secondary">Sinh: {patientFound.dob}</Text>}
                                {patientFound.gender && <Text type="secondary">| {patientFound.gender}</Text>}
                            </Space>
                        }
                        style={{ marginBottom: 20, borderRadius: 8 }}
                    />

                    <Title level={5}>Vui lòng mô tả triệu chứng / lý do khám:</Title>
                    <TextArea
                        rows={5}
                        placeholder="Ví dụ: Đau đầu kéo dài 3 ngày, kèm buồn nôn, sốt nhẹ..."
                        defaultValue=""
                        onChange={e => {
                            chiefComplaintRef.current = e.target.value;
                            setHasComplaint(!!e.target.value.trim());
                        }}
                        style={{ fontSize: 16, marginBottom: 16, borderRadius: 8 }}
                        maxLength={1000}
                        showCount
                    />

                    <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                        <Button size="large" onClick={() => setCurrentStep(0)}>
                            ← Quay lại
                        </Button>
                        <Button
                            type="primary"
                            size="large"
                            onClick={handleSubmitRegistration}
                            loading={submitLoading}
                            disabled={!hasComplaint || cooldown}
                            style={{ height: 52, fontSize: 16, paddingInline: 40 }}
                        >
                            {submitLoading ? 'Đang đăng ký...' : 'Xác nhận đăng ký'}
                        </Button>
                    </Space>
                </div>
            )}

            {/* ============ STEP 3: Kết quả — Số thứ tự ============ */}
            {currentStep === 2 && kioskResult && (
                <Result
                    status="success"
                    icon={
                        <div style={{
                            width: 120,
                            height: 120,
                            borderRadius: '50%',
                            background: 'linear-gradient(135deg, #1677ff, #36cfc9)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            margin: '0 auto',
                        }}>
                            <Text style={{ fontSize: 36, fontWeight: 700, color: '#fff' }}>
                                {kioskResult.queue_number}
                            </Text>
                        </div>
                    }
                    title={
                        <span style={{ fontSize: 24 }}>
                            Số thứ tự của bạn: <strong>{kioskResult.queue_number}</strong>
                        </span>
                    }
                    subTitle={
                        <div>
                            <p>{kioskResult.message}</p>
                            <p style={{ color: '#faad14', fontWeight: 600, marginTop: 8 }}>
                                ⚠️ Vui lòng chờ gọi số để được đo sinh hiệu
                            </p>
                            <Text type="secondary">Mã khám: {kioskResult.visit_code}</Text>
                        </div>
                    }
                    extra={
                        <Button
                            size="large"
                            type="primary"
                            onClick={handleReset}
                            disabled={cooldown}
                            style={{ height: 52, fontSize: 16, paddingInline: 40 }}
                        >
                            Đăng ký người tiếp theo
                        </Button>
                    }
                />
            )}
        </Card>
    );
}
