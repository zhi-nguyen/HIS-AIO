'use client';

import React, { useState, useEffect, useRef, useCallback, memo } from 'react';
import {
    Button,
    Input,
    Typography,
    Card,
    Steps,
    Tag,
    Descriptions,
    Spin,
    Alert,
} from 'antd';
import {
    ScanOutlined,
    IdcardOutlined,
    CheckCircleOutlined,
    MedicineBoxOutlined,
    ClockCircleOutlined,
    UserOutlined,
    SafetyCertificateOutlined,
    WarningOutlined,
    ReloadOutlined,
    FileTextOutlined,
    QrcodeOutlined,
} from '@ant-design/icons';
import ScannerModal from '@/components/ScannerModal';
import { parseCccdQrData } from '@/utils/cccd';
import { kioskApi } from '@/lib/services';
import { useScannerListener } from '@/hooks/useScannerListener';
import type {
    KioskSelfServiceIdentifyResponse,
    KioskSelfServiceRegisterResponse,
} from '@/types';
import axios from 'axios';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

// ======================================================================
// CONSTANTS
// ======================================================================
const AUTO_RESET_SECONDS = 30;

// ======================================================================
// HELPERS
// ======================================================================
function isCCCD(raw: string): boolean {
    return /^\d{12}$/.test(raw.trim());
}

function isBHYT(raw: string): boolean {
    const trimmed = raw.trim();
    return /^[A-Z]{2}\d{8,13}$/.test(trimmed) || /^\d{10,15}$/.test(trimmed);
}

// ======================================================================
// Memoized Clock Component
// ======================================================================
const KioskClock = memo(() => {
    const [currentTime, setCurrentTime] = useState(new Date());

    useEffect(() => {
        const tick = setInterval(() => setCurrentTime(new Date()), 1000);
        return () => clearInterval(tick);
    }, []);

    return (
        <div className="text-right">
            <div style={{ fontSize: 28, fontWeight: 700, color: '#0077b6', fontVariantNumeric: 'tabular-nums', lineHeight: 1.2 }}>
                {currentTime.toLocaleTimeString('vi-VN')}
            </div>
            <div style={{ color: '#475569', fontSize: 13 }}>
                {currentTime.toLocaleDateString('vi-VN', {
                    weekday: 'long',
                    day: 'numeric',
                    month: 'long',
                    year: 'numeric',
                })}
            </div>
        </div>
    );
});
KioskClock.displayName = 'KioskClock';

// ======================================================================
// KIOSK PAGE
// ======================================================================
export default function KioskPage() {
    // --- State ---
    const [currentStep, setCurrentStep] = useState(0);
    const [scanData, setScanData] = useState('');
    const [chiefComplaint, setChiefComplaint] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showScanner, setShowScanner] = useState(false);

    // API results
    const [identifyResult, setIdentifyResult] = useState<KioskSelfServiceIdentifyResponse | null>(null);
    const [registerResult, setRegisterResult] = useState<KioskSelfServiceRegisterResponse | null>(null);

    // Auto-reset timer
    const [countdown, setCountdown] = useState(AUTO_RESET_SECONDS);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    // Input ref for auto-focus
    const scanInputRef = useRef<any>(null);

    // --- Auto-focus on step 0 ---
    useEffect(() => {
        if (currentStep === 0 && scanInputRef.current) {
            setTimeout(() => scanInputRef.current?.focus(), 300);
        }
    }, [currentStep]);

    // --- Reset ---
    const handleReset = useCallback(() => {
        setCurrentStep(0);
        setScanData('');
        setChiefComplaint('');
        setError(null);
        setIdentifyResult(null);
        setRegisterResult(null);
        setLoading(false);
        if (timerRef.current) clearInterval(timerRef.current);
    }, []);

    // --- Auto-reset countdown (step 2 only) ---
    useEffect(() => {
        if (currentStep === 2) {
            setCountdown(AUTO_RESET_SECONDS);
            timerRef.current = setInterval(() => {
                setCountdown(prev => {
                    if (prev <= 1) {
                        handleReset();
                        return AUTO_RESET_SECONDS;
                    }
                    return prev - 1;
                });
            }, 1000);
        }
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [currentStep, handleReset]);

    // --- Step 1: Identify ---
    const handleIdentify = useCallback(async (overrideScanData?: any) => {
        const dataToScan = typeof overrideScanData === 'string' ? overrideScanData : scanData.trim();
        if (!dataToScan) return;

        setError(null);
        setLoading(true);

        try {
            const result = await kioskApi.identify(dataToScan);
            setIdentifyResult(result);
            setCurrentStep(1);
        } catch (err) {
            if (axios.isAxiosError(err)) {
                const data = err.response?.data;
                if (err.response?.status === 429) {
                    setError('Hệ thống đang bận. Vui lòng chờ 1 phút rồi thử lại.');
                } else if (data?.error) {
                    const msg = typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
                    setError(msg);
                } else {
                    setError('Không thể kết nối đến hệ thống. Vui lòng thử lại.');
                }
            } else {
                setError('Đã xảy ra lỗi. Vui lòng thử lại.');
            }
        } finally {
            setLoading(false);
        }
    }, [scanData]);

    // --- Scanner Integration ---
    const processScanData = useCallback((data: string) => {
        if (currentStep !== 0) return; // Automatically identifying only works on step 0
        if (!data) return;

        let extractedData = data.trim();

        // Check if it looks like a full QR code (contains |)
        if (extractedData.includes('|')) {
            const parsed = parseCccdQrData(extractedData);
            if (parsed && parsed.cccd) {
                extractedData = parsed.cccd;
            } else {
                // If parseCccdQrData fails (maybe format changed slightly or missing fields)
                // but we know the first part is often the CCCD, or we can fallback to regex.
                const firstPart = extractedData.split('|')[0].trim();
                if (isCCCD(firstPart)) {
                    extractedData = firstPart;
                } else {
                    const cccdMatch = extractedData.match(/\d{12}/);
                    if (cccdMatch) {
                        extractedData = cccdMatch[0];
                    } else {
                        setError('Mã QR không hợp lệ hoặc không phải CCCD');
                        return;
                    }
                }
            }
        } else {
            // Maybe it's a raw string that just has the CCCD embedded without pipes.
            // Very fast inputs might drop pipes or send them differently.
            // Try to extract 12 consecutive digits (CCCD format) or basic BHYT format.
            const cccdMatch = extractedData.match(/\d{12}/);
            if (cccdMatch) {
                extractedData = cccdMatch[0];
            } else if (!isBHYT(extractedData) && !isCCCD(extractedData)) {
                // MIGHT be a partial read or different encoding, but we strict check for now
                setError(`Mã quét không hợp lệ: ${extractedData.substring(0, 30)}${extractedData.length > 30 ? '...' : ''}`);
                return;
            }
        }

        setScanData(extractedData);
        handleIdentify(extractedData);
    }, [currentStep, handleIdentify]);

    useEffect(() => {
        const handleScanEvent = (e: Event) => processScanData((e as CustomEvent).detail as string);
        window.addEventListener('HIS_SCANNED_DATA', handleScanEvent);
        return () => window.removeEventListener('HIS_SCANNED_DATA', handleScanEvent);
    }, [processScanData]);

    useScannerListener({
        onScan: processScanData,
    });

    // --- Step 2: Register ---
    const handleRegister = async () => {
        if (!identifyResult || !chiefComplaint.trim()) return;
        setError(null);
        setLoading(true);

        try {
            const result = await kioskApi.register(
                identifyResult.patient.id,
                chiefComplaint.trim()
            );
            setRegisterResult(result);
            setCurrentStep(2);
        } catch (err) {
            if (axios.isAxiosError(err)) {
                const data = err.response?.data;
                if (err.response?.status === 409) {
                    setError(`Bạn đang có lượt khám chưa hoàn thành (Mã: ${data?.active_visit_code || 'N/A'}). Vui lòng kiểm tra lại.`);
                } else if (err.response?.status === 429) {
                    setError('Hệ thống đang bận. Vui lòng chờ 1 phút rồi thử lại.');
                } else if (data?.error) {
                    const msg = typeof data.error === 'string' ? data.error : JSON.stringify(data.error);
                    setError(msg);
                } else {
                    setError('Không thể kết nối đến hệ thống. Vui lòng thử lại.');
                }
            } else {
                setError('Đã xảy ra lỗi. Vui lòng thử lại.');
            }
        } finally {
            setLoading(false);
        }
    };

    // --- QR Scanner Handler ---
    const handleQrScanSuccess = useCallback((decodedText: string) => {
        setShowScanner(false);
        const parsed = parseCccdQrData(decodedText);

        if (!parsed) {
            setError('Mã QR không hợp lệ hoặc không phải CCCD');
            return;
        }

        setScanData(parsed.cccd);
        handleIdentify(parsed.cccd);
    }, [handleIdentify]);

    // ======================================================================
    // RENDER
    // ======================================================================
    return (
        <div style={{
            minHeight: '100vh',
            background: 'linear-gradient(135deg, #dbeafe 0%, #f0f9ff 45%, #e0e7ff 100%)',
            display: 'flex',
            flexDirection: 'column',
            fontFamily: "'Roboto', sans-serif",
        }}>
            {/* ── Header ── */}
            <header style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '16px 32px',
                background: 'rgba(255,255,255,0.85)',
                backdropFilter: 'blur(12px)',
                borderBottom: '1px solid rgba(148,163,184,0.2)',
                boxShadow: '0 1px 8px rgba(0,0,0,0.06)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div style={{
                        width: 52, height: 52,
                        borderRadius: 14,
                        background: '#0077b6',
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        boxShadow: '0 4px 12px rgba(0,119,182,0.3)',
                    }}>
                        <MedicineBoxOutlined style={{ fontSize: 26, color: '#fff' }} />
                    </div>
                    <div>
                        <div style={{ fontSize: 22, fontWeight: 700, color: '#1e3a5f', lineHeight: 1.2 }}>
                            Bệnh Viện Đa Khoa ABC
                        </div>
                        <div style={{ fontSize: 14, color: '#475569', marginTop: 2 }}>
                            Kiosk Tự Phục Vụ — Đăng Ký Khám Bệnh
                        </div>
                    </div>
                </div>
                <KioskClock />
            </header>

            {/* ── Steps Indicator ── */}
            <div style={{ padding: '20px 32px 8px', maxWidth: 720, margin: '0 auto', width: '100%' }}>
                <Steps
                    current={currentStep}
                    items={[
                        {
                            title: <span style={{ fontWeight: 600 }}>Quét mã</span>,
                            icon: <ScanOutlined style={{ color: currentStep >= 0 ? '#0077b6' : '#94a3b8' }} />,
                        },
                        {
                            title: <span style={{ fontWeight: 600 }}>Xác nhận</span>,
                            icon: <CheckCircleOutlined style={{ color: currentStep >= 1 ? '#0077b6' : '#94a3b8' }} />,
                        },
                        {
                            title: <span style={{ fontWeight: 600 }}>Hoàn thành</span>,
                            icon: <IdcardOutlined style={{ color: currentStep >= 2 ? '#0077b6' : '#94a3b8' }} />,
                        },
                    ]}
                    className="kiosk-steps"
                />
            </div>

            {/* ── Main Content ── */}
            <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '16px 32px 32px' }}>
                <div style={{ width: '100%', maxWidth: 640 }}>

                    {/* ════════ STEP 0: Quét mã ════════ */}
                    {currentStep === 0 && (
                        <Card
                            style={{
                                background: 'rgba(255,255,255,0.92)',
                                border: '1px solid rgba(148,163,184,0.3)',
                                borderRadius: 24,
                                boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
                            }}
                            styles={{ body: { padding: 40 } }}
                        >
                            {/* Icon + heading */}
                            <div style={{ textAlign: 'center', marginBottom: 32 }}>
                                <div style={{
                                    width: 80, height: 80,
                                    borderRadius: 20,
                                    background: '#0077b6',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    margin: '0 auto 16px',
                                    boxShadow: '0 6px 20px rgba(0,119,182,0.3)',
                                }}>
                                    <ScanOutlined style={{ fontSize: 38, color: '#fff' }} />
                                </div>
                                <Title level={2} style={{ color: '#1e3a5f', marginBottom: 8, fontSize: 28 }}>
                                    Quét mã CCCD hoặc BHYT
                                </Title>
                                <Paragraph style={{ color: '#475569', fontSize: 17, marginBottom: 0 }}>
                                    Đặt thẻ CCCD hoặc thẻ BHYT lên máy quét, hoặc nhập mã số bên dưới
                                </Paragraph>
                            </div>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                                {/* Input */}
                                <div className="kiosk-input-field">
                                    <Input
                                        ref={scanInputRef}
                                        value={scanData}
                                        onChange={e => { setScanData(e.target.value); setError(null); }}
                                        onPressEnter={handleIdentify}
                                        placeholder="Nhập mã CCCD (12 số) hoặc mã BHYT..."
                                        size="large"
                                        prefix={<IdcardOutlined />}
                                        style={{ height: 58, fontSize: 18, borderRadius: 14 }}
                                        maxLength={15}
                                        autoFocus
                                    />
                                </div>

                                {error && (
                                    <Alert
                                        type="error"
                                        message={error}
                                        showIcon
                                        icon={<WarningOutlined />}
                                        style={{ borderRadius: 12, fontSize: 16 }}
                                    />
                                )}

                                {/* Action buttons */}
                                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                                    <Button
                                        size="large"
                                        block
                                        onClick={() => setShowScanner(true)}
                                        icon={<QrcodeOutlined />}
                                        style={{
                                            height: 64,
                                            fontSize: 16,
                                            borderRadius: 14,
                                            borderColor: '#94a3b8',
                                            color: '#1e3a5f',
                                            fontWeight: 500,
                                            background: '#fff',
                                        }}
                                    >
                                        Quét QR Camera
                                    </Button>
                                    <Button
                                        type="primary"
                                        size="large"
                                        block
                                        loading={loading}
                                        onClick={handleIdentify}
                                        disabled={!scanData.trim()}
                                        icon={<ScanOutlined />}
                                        style={{
                                            height: 64,
                                            fontSize: 18,
                                            borderRadius: 14,
                                            background: '#0077b6',
                                            border: 'none',
                                            fontWeight: 600,
                                        }}
                                    >
                                        Tra cứu
                                    </Button>
                                </div>
                            </div>

                            {/* Mock data hints */}
                            <div style={{
                                marginTop: 28,
                                padding: 16,
                                borderRadius: 14,
                                background: '#f0f9ff',
                                border: '1px solid #bae6fd',
                            }}>
                                <Text style={{ color: '#0369a1', fontSize: 13, display: 'block', marginBottom: 8 }}>
                                    💡 Mã mẫu để thử nghiệm:
                                </Text>
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                                    {['092200012345', '079085001234', '0000000123', 'TE1790000000123'].map(code => (
                                        <Tag
                                            key={code}
                                            style={{
                                                cursor: 'pointer',
                                                background: '#fff',
                                                borderColor: '#7dd3fc',
                                                color: '#0369a1',
                                                fontSize: 13,
                                                padding: '2px 10px',
                                                borderRadius: 8,
                                            }}
                                            onClick={() => { setScanData(code); setError(null); }}
                                        >
                                            {code}
                                        </Tag>
                                    ))}
                                </div>
                            </div>
                        </Card>
                    )}

                    {/* ════════ STEP 1: Xác nhận thông tin ════════ */}
                    {currentStep === 1 && identifyResult && (
                        <Card
                            style={{
                                background: 'rgba(255,255,255,0.92)',
                                border: '1px solid rgba(148,163,184,0.3)',
                                borderRadius: 24,
                                boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
                            }}
                            styles={{ body: { padding: 36 } }}
                        >
                            {/* Active Visit Warning */}
                            {identifyResult.has_active_visit && (
                                <Alert
                                    type="warning"
                                    showIcon
                                    icon={<WarningOutlined />}
                                    message="Bạn đang có lượt khám chưa hoàn thành"
                                    description={`Mã lượt khám: ${identifyResult.active_visit_code}. Bạn vẫn có thể đăng ký mới nếu cần.`}
                                    style={{ borderRadius: 12, marginBottom: 20, fontSize: 16 }}
                                />
                            )}

                            {/* Patient Info */}
                            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 16, marginBottom: 20 }}>
                                <div style={{
                                    width: 56, height: 56,
                                    borderRadius: 16,
                                    background: '#10b981',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    flexShrink: 0,
                                    boxShadow: '0 4px 12px rgba(16,185,129,0.3)',
                                }}>
                                    <UserOutlined style={{ fontSize: 24, color: '#fff' }} />
                                </div>
                                <div style={{ flex: 1 }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
                                        <span style={{ fontSize: 22, fontWeight: 700, color: '#1e3a5f' }}>
                                            {identifyResult.patient.full_name}
                                        </span>
                                        {identifyResult.patient.is_new_patient && (
                                            <Tag color="green" style={{ borderRadius: 20 }}>BN mới</Tag>
                                        )}
                                    </div>
                                    <Text style={{ color: '#475569', fontSize: 15 }}>
                                        Mã BN: <strong>{identifyResult.patient.patient_code}</strong>
                                    </Text>
                                </div>
                            </div>

                            <Descriptions
                                column={2}
                                size="small"
                                className="kiosk-descriptions"
                                style={{ marginBottom: 20 }}
                            >
                                <Descriptions.Item label="Ngày sinh">
                                    <span style={{ fontSize: 15, fontWeight: 600 }}>{identifyResult.patient.date_of_birth || '—'}</span>
                                </Descriptions.Item>
                                <Descriptions.Item label="Giới tính">
                                    <span style={{ fontSize: 15, fontWeight: 600 }}>
                                        {identifyResult.patient.gender === 'M' ? 'Nam' : identifyResult.patient.gender === 'F' ? 'Nữ' : 'Khác'}
                                    </span>
                                </Descriptions.Item>
                            </Descriptions>

                            {/* Insurance Info */}
                            {identifyResult.insurance_info && (
                                <div style={{
                                    padding: 16,
                                    borderRadius: 14,
                                    background: '#f0fdf4',
                                    border: '1px solid #86efac',
                                    marginBottom: 20,
                                }}>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                                        <SafetyCertificateOutlined style={{ color: '#16a34a', fontSize: 18 }} />
                                        <Text style={{ color: '#166534', fontWeight: 600, fontSize: 15 }}>Thông tin BHYT</Text>
                                    </div>
                                    <Descriptions
                                        column={2}
                                        size="small"
                                        className="kiosk-descriptions"
                                    >
                                        <Descriptions.Item label="Mã BHYT">
                                            {identifyResult.insurance_info.insurance_code}
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Mức hưởng">
                                            <Tag color="green">{identifyResult.insurance_info.benefit_rate}%</Tag>
                                        </Descriptions.Item>
                                        <Descriptions.Item label="Nơi ĐK KCB" span={2}>
                                            {identifyResult.insurance_info.registered_hospital_name}
                                        </Descriptions.Item>
                                    </Descriptions>
                                </div>
                            )}

                            {/* Chief Complaint Input */}
                            <div style={{ marginBottom: 20 }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                                    <FileTextOutlined style={{ color: '#0077b6', fontSize: 18 }} />
                                    <Text style={{ color: '#1e3a5f', fontWeight: 600, fontSize: 17 }}>
                                        Lý do khám <span style={{ color: '#dc2626' }}>*</span>
                                    </Text>
                                </div>
                                <div className="kiosk-textarea">
                                    <TextArea
                                        value={chiefComplaint}
                                        onChange={e => { setChiefComplaint(e.target.value); setError(null); }}
                                        placeholder="Mô tả triệu chứng hoặc lý do bạn muốn khám hôm nay... (VD: Đau đầu, chóng mặt 2 ngày)"
                                        rows={3}
                                        maxLength={1000}
                                        showCount
                                        style={{ fontSize: 16, borderRadius: 14, borderColor: '#94a3b8', color: '#1e3a5f' }}
                                    />
                                </div>
                            </div>

                            {error && (
                                <Alert
                                    type="error"
                                    message={error}
                                    showIcon
                                    style={{ borderRadius: 12, marginBottom: 20, fontSize: 15 }}
                                />
                            )}

                            {/* Action Buttons */}
                            <div style={{ display: 'flex', gap: 12 }}>
                                <Button
                                    size="large"
                                    onClick={handleReset}
                                    icon={<ReloadOutlined />}
                                    style={{
                                        height: 60,
                                        borderRadius: 14,
                                        borderColor: '#94a3b8',
                                        color: '#475569',
                                        fontWeight: 500,
                                        fontSize: 16,
                                        minWidth: 120,
                                    }}
                                >
                                    Quay lại
                                </Button>
                                <Button
                                    type="primary"
                                    size="large"
                                    block
                                    loading={loading}
                                    onClick={handleRegister}
                                    disabled={!chiefComplaint.trim() || chiefComplaint.trim().length < 3}
                                    icon={<CheckCircleOutlined />}
                                    style={{
                                        height: 60,
                                        fontSize: 18,
                                        borderRadius: 14,
                                        background: identifyResult.has_active_visit ? '#d97706' : '#059669',
                                        border: 'none',
                                        fontWeight: 600,
                                    }}
                                >
                                    {identifyResult.has_active_visit ? 'Đăng ký lượt mới' : 'Xác nhận đăng ký'}
                                </Button>
                            </div>
                        </Card>
                    )}

                    {/* ════════ STEP 2: Hoàn thành ════════ */}
                    {currentStep === 2 && registerResult && (
                        <Card
                            style={{
                                background: 'rgba(255,255,255,0.92)',
                                border: '1px solid rgba(148,163,184,0.3)',
                                borderRadius: 24,
                                boxShadow: '0 8px 32px rgba(0,0,0,0.08)',
                            }}
                            styles={{ body: { padding: 40, textAlign: 'center' } }}
                        >
                            {/* Success icon — pop animation, no bounce */}
                            <div style={{ marginBottom: 16 }}>
                                <div
                                    className="kiosk-success-pop"
                                    style={{
                                        width: 88, height: 88,
                                        borderRadius: '50%',
                                        background: '#059669',
                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                        margin: '0 auto',
                                        boxShadow: '0 6px 24px rgba(5,150,105,0.35)',
                                    }}
                                >
                                    <CheckCircleOutlined style={{ fontSize: 44, color: '#fff' }} />
                                </div>
                            </div>

                            <Title level={2} style={{ color: '#059669', marginBottom: 8, fontSize: 30 }}>
                                Đăng ký thành công!
                            </Title>

                            <Paragraph style={{ color: '#475569', fontSize: 17, marginBottom: 28 }}>
                                Vui lòng chờ gọi số trên màn hình
                            </Paragraph>

                            {/* Queue Number — large display */}
                            <div style={{
                                marginBottom: 24,
                                padding: '24px 32px',
                                borderRadius: 20,
                                background: '#f0f9ff',
                                border: '2px solid #7dd3fc',
                            }}>
                                <Text style={{ color: '#0369a1', fontSize: 14, display: 'block', marginBottom: 6, fontWeight: 500, letterSpacing: 2 }}>
                                    SỐ THỨ TỰ CỦA BẠN
                                </Text>
                                <div style={{
                                    fontSize: 88,
                                    lineHeight: 1,
                                    fontWeight: 900,
                                    color: '#0077b6',
                                    fontVariantNumeric: 'tabular-nums',
                                }}>
                                    {registerResult.daily_sequence}
                                </div>
                                <Text style={{ color: '#0369a1', fontSize: 14, marginTop: 4, display: 'block' }}>
                                    {registerResult.queue_number}
                                </Text>
                            </div>

                            {/* Info cards */}
                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 24 }}>
                                <div style={{
                                    padding: 16,
                                    borderRadius: 14,
                                    background: '#fffbeb',
                                    border: '1px solid #fde68a',
                                }}>
                                    <ClockCircleOutlined style={{ fontSize: 24, color: '#d97706', display: 'block', marginBottom: 6 }} />
                                    <div style={{ fontSize: 24, fontWeight: 700, color: '#1e3a5f' }}>
                                        ~{registerResult.estimated_wait_minutes} phút
                                    </div>
                                    <Text style={{ color: '#78716c', fontSize: 13 }}>Thời gian chờ ước tính</Text>
                                </div>
                                <div style={{
                                    padding: 16,
                                    borderRadius: 14,
                                    background: '#f0f9ff',
                                    border: '1px solid #bae6fd',
                                }}>
                                    <FileTextOutlined style={{ fontSize: 24, color: '#0077b6', display: 'block', marginBottom: 6 }} />
                                    <div style={{ fontSize: 14, fontWeight: 600, color: '#1e3a5f', wordBreak: 'break-all' }}>
                                        {registerResult.visit_code}
                                    </div>
                                    <Text style={{ color: '#78716c', fontSize: 13 }}>Mã lượt khám</Text>
                                </div>
                            </div>

                            {/* Instructions */}
                            <div style={{
                                padding: 20,
                                borderRadius: 14,
                                background: '#fffde7',
                                border: '1px solid #fde68a',
                                marginBottom: 24,
                                textAlign: 'left',
                            }}>
                                <Text style={{ color: '#92400e', fontWeight: 700, display: 'block', marginBottom: 10, fontSize: 16 }}>
                                    📋 Hướng dẫn tiếp theo:
                                </Text>
                                <ol style={{ color: '#78350f', fontSize: 15, lineHeight: 2, paddingLeft: 20, margin: 0 }}>
                                    <li>Ngồi chờ tại khu vực phòng khám</li>
                                    <li>Chú ý màn hình hiển thị và loa gọi số</li>
                                    <li>Khi được gọi, đến phòng đo sinh hiệu</li>
                                    <li>Sau đó chờ bác sĩ khám</li>
                                </ol>
                            </div>

                            {/* Countdown */}
                            <div style={{ marginBottom: 16 }}>
                                <Text style={{ color: '#64748b', fontSize: 14 }}>
                                    Tự động quay về màn hình chính sau <strong>{countdown}</strong> giây
                                </Text>
                            </div>

                            <Button
                                size="large"
                                onClick={handleReset}
                                icon={<ReloadOutlined />}
                                style={{
                                    height: 56,
                                    borderRadius: 14,
                                    borderColor: '#94a3b8',
                                    color: '#1e3a5f',
                                    fontWeight: 500,
                                    fontSize: 16,
                                    paddingInline: 28,
                                }}
                            >
                                Đăng ký bệnh nhân khác
                            </Button>
                        </Card>
                    )}
                </div>
            </main>

            {/* ── Footer ── */}
            <footer style={{
                textAlign: 'center',
                padding: '12px 32px',
                color: '#64748b',
                fontSize: 13,
                borderTop: '1px solid rgba(148,163,184,0.2)',
                background: 'rgba(255,255,255,0.6)',
            }}>
                Vui lòng giữ gìn thiết bị • Hotline hỗ trợ:{' '}
                <span style={{ color: '#0077b6', fontWeight: 600 }}>1900 1234</span>
            </footer>

            <ScannerModal
                open={showScanner}
                onCancel={() => setShowScanner(false)}
                onScanSuccess={handleQrScanSuccess}
            />
        </div>
    );
}
