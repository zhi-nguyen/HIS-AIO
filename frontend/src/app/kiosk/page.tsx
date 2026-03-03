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
    Result,
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
            <div className="text-3xl font-bold text-cyan-400 tracking-wider font-mono">
                {currentTime.toLocaleTimeString('vi-VN')}
            </div>
            <div className="text-blue-300 text-xs">
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
    const handleIdentify = async (overrideScanData?: any) => {
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
    };

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

        console.log('--- KHÁCH HÀNG QUÉT QR TẠI KIOSK ---');
        console.log('Dữ liệu thô quét được:', decodedText);
        console.log('Thông tin phân tích:', parsed);

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
        <div className="min-h-screen bg-gradient-to-br from-blue-900 via-indigo-900 to-purple-900 flex flex-col">
            {/* ── Header ── */}
            <header className="flex items-center justify-between px-8 py-5 bg-black/20 backdrop-blur-sm border-b border-white/10">
                <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/30">
                        <MedicineBoxOutlined className="text-2xl text-white" />
                    </div>
                    <div>
                        <Title level={3} className="!text-white !mb-0 tracking-tight">
                            Bệnh Viện Đa Khoa ABC
                        </Title>
                        <Text className="text-blue-300 text-sm">
                            Kiosk Tự Phục Vụ — Đăng Ký Khám Bệnh
                        </Text>
                    </div>
                </div>
                {/* Clock Isolated */}
                <KioskClock />
            </header>

            {/* ── Steps Indicator ── */}
            <div className="px-8 py-4 max-w-3xl mx-auto w-full">
                <Steps
                    current={currentStep}
                    items={[
                        { title: <span className="text-white">Quét mã</span>, icon: <ScanOutlined className="text-cyan-400" /> },
                        { title: <span className="text-white">Xác nhận</span>, icon: <CheckCircleOutlined className="text-cyan-400" /> },
                        { title: <span className="text-white">Hoàn thành</span>, icon: <IdcardOutlined className="text-cyan-400" /> },
                    ]}
                    className="kiosk-steps"
                />
            </div>

            {/* ── Main Content ── */}
            <main className="flex-1 flex items-center justify-center px-8 pb-8">
                <div className="w-full max-w-2xl">

                    {/* ════════ STEP 0: Quét mã ════════ */}
                    {currentStep === 0 && (
                        <Card
                            className="rounded-3xl shadow-2xl border-0"
                            style={{
                                background: 'rgba(255,255,255,0.08)',
                                backdropFilter: 'blur(20px)',
                                border: '1px solid rgba(255,255,255,0.15)',
                            }}
                            styles={{ body: { padding: '48px' } }}
                        >
                            <div className="text-center mb-8">
                                <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-cyan-400 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-500/30">
                                    <ScanOutlined className="text-4xl text-white" />
                                </div>
                                <Title level={2} className="!text-white !mb-2">
                                    Quét mã CCCD hoặc BHYT
                                </Title>
                                <Paragraph className="text-blue-300 text-base !mb-0">
                                    Đặt thẻ CCCD hoặc thẻ BHYT lên máy quét, hoặc nhập mã số bên dưới
                                </Paragraph>
                            </div>

                            <div className="space-y-6">
                                <Input
                                    ref={scanInputRef}
                                    value={scanData}
                                    onChange={e => { setScanData(e.target.value); setError(null); }}
                                    onPressEnter={handleIdentify}
                                    placeholder="Nhập mã CCCD (12 số) hoặc mã BHYT (10/15 ký tự)..."
                                    size="large"
                                    prefix={<IdcardOutlined className="text-blue-400" />}
                                    className="!bg-white/10 !border-white/20 !text-white placeholder:!text-blue-300/50"
                                    style={{ height: 56, fontSize: 18, borderRadius: 16 }}
                                    maxLength={15}
                                    autoFocus
                                />

                                {error && (
                                    <Alert
                                        type="error"
                                        title={error}
                                        showIcon
                                        icon={<WarningOutlined />}
                                        className="!rounded-xl"
                                    />
                                )}

                                <div className="grid grid-cols-2 gap-4">
                                    <Button
                                        type="default"
                                        size="large"
                                        block
                                        onClick={() => setShowScanner(true)}
                                        icon={<QrcodeOutlined />}
                                        style={{
                                            height: 56,
                                            fontSize: 16,
                                            borderRadius: 16,
                                            background: 'rgba(255,255,255,0.1)',
                                            borderColor: 'rgba(255,255,255,0.2)',
                                            color: '#fff',
                                            fontWeight: 500,
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
                                            height: 56,
                                            fontSize: 18,
                                            borderRadius: 16,
                                            background: 'linear-gradient(135deg, #00b4d8, #0077b6)',
                                            border: 'none',
                                            fontWeight: 600,
                                        }}
                                    >
                                        Tra cứu
                                    </Button>
                                </div>
                            </div>

                            {/* Mock data hints */}
                            <div className="mt-8 p-4 rounded-xl bg-white/5 border border-white/10">
                                <Text className="text-blue-300/70 text-xs block mb-2">
                                    💡 Mã mẫu để thử nghiệm:
                                </Text>
                                <div className="flex flex-wrap gap-2">
                                    {['092200012345', '079085001234', '0000000123', 'TE1790000000123'].map(code => (
                                        <Tag
                                            key={code}
                                            className="cursor-pointer !bg-white/10 !border-white/20 !text-blue-200 hover:!bg-white/20 transition-colors"
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
                            className="rounded-3xl shadow-2xl border-0"
                            style={{
                                background: 'rgba(255,255,255,0.08)',
                                backdropFilter: 'blur(20px)',
                                border: '1px solid rgba(255,255,255,0.15)',
                            }}
                            styles={{ body: { padding: '40px' } }}
                        >
                            {/* ── Active Visit Warning ── */}
                            {identifyResult.has_active_visit && (
                                <Alert
                                    type="warning"
                                    showIcon
                                    icon={<WarningOutlined />}
                                    title="Bạn đang có lượt khám chưa hoàn thành"
                                    description={`Mã lượt khám: ${identifyResult.active_visit_code}. Bạn vẫn có thể đăng ký mới nếu cần.`}
                                    className="!rounded-xl mb-6"
                                />
                            )}

                            {/* ── Patient Info ── */}
                            <div className="flex items-start gap-4 mb-6">
                                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-400 to-green-500 flex items-center justify-center shadow-lg shadow-emerald-500/30 flex-shrink-0">
                                    <UserOutlined className="text-2xl text-white" />
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-3 mb-1">
                                        <Title level={3} className="!text-white !mb-0">
                                            {identifyResult.patient.full_name}
                                        </Title>
                                        {identifyResult.patient.is_new_patient && (
                                            <Tag color="green" className="!rounded-full">BN mới</Tag>
                                        )}
                                    </div>
                                    <Text className="text-blue-300">
                                        Mã BN: {identifyResult.patient.patient_code}
                                    </Text>
                                </div>
                            </div>

                            <Descriptions
                                column={2}
                                size="small"
                                className="mb-6 kiosk-descriptions"
                                labelStyle={{ color: 'rgba(147,197,253,0.8)', fontWeight: 500 }}
                                contentStyle={{ color: '#fff' }}
                            >
                                <Descriptions.Item label="Ngày sinh">
                                    {identifyResult.patient.date_of_birth || '—'}
                                </Descriptions.Item>
                                <Descriptions.Item label="Giới tính">
                                    {identifyResult.patient.gender === 'M' ? 'Nam' : identifyResult.patient.gender === 'F' ? 'Nữ' : 'Khác'}
                                </Descriptions.Item>
                            </Descriptions>

                            {/* ── Insurance Info ── */}
                            {identifyResult.insurance_info && (
                                <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20 mb-6">
                                    <div className="flex items-center gap-2 mb-3">
                                        <SafetyCertificateOutlined className="text-emerald-400 text-lg" />
                                        <Text className="text-emerald-300 font-semibold">Thông tin BHYT</Text>
                                    </div>
                                    <Descriptions
                                        column={2}
                                        size="small"
                                        className="kiosk-descriptions"
                                        labelStyle={{ color: 'rgba(110,231,183,0.7)', fontSize: 12 }}
                                        contentStyle={{ color: '#d1fae5', fontSize: 13 }}
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

                            {/* ── Chief Complaint Input ── */}
                            <div className="mb-6">
                                <div className="flex items-center gap-2 mb-3">
                                    <FileTextOutlined className="text-cyan-400" />
                                    <Text className="text-white font-semibold text-base">
                                        Lý do khám <span className="text-red-400">*</span>
                                    </Text>
                                </div>
                                <TextArea
                                    value={chiefComplaint}
                                    onChange={e => { setChiefComplaint(e.target.value); setError(null); }}
                                    placeholder="Mô tả triệu chứng hoặc lý do bạn muốn khám hôm nay... (VD: Đau đầu, chóng mặt 2 ngày)"
                                    rows={3}
                                    maxLength={1000}
                                    showCount
                                    className="!bg-white/10 !border-white/20 !text-white placeholder:!text-blue-300/50 !rounded-xl"
                                    style={{ fontSize: 16 }}
                                />
                            </div>

                            {error && (
                                <Alert
                                    type="error"
                                    title={error}
                                    showIcon
                                    icon={<WarningOutlined />}
                                    className="!rounded-xl mb-6"
                                />
                            )}

                            {/* ── Action Buttons ── */}
                            <div className="flex gap-4">
                                <Button
                                    size="large"
                                    onClick={handleReset}
                                    icon={<ReloadOutlined />}
                                    style={{
                                        height: 52,
                                        borderRadius: 14,
                                        background: 'rgba(255,255,255,0.1)',
                                        border: '1px solid rgba(255,255,255,0.2)',
                                        color: '#fff',
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
                                        height: 52,
                                        fontSize: 17,
                                        borderRadius: 14,
                                        background: identifyResult.has_active_visit
                                            ? 'linear-gradient(135deg, #f59e0b, #d97706)'
                                            : 'linear-gradient(135deg, #10b981, #059669)',
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
                            className="rounded-3xl shadow-2xl border-0"
                            style={{
                                background: 'rgba(255,255,255,0.08)',
                                backdropFilter: 'blur(20px)',
                                border: '1px solid rgba(255,255,255,0.15)',
                            }}
                            styles={{ body: { padding: '48px', textAlign: 'center' } }}
                        >
                            {/* Confetti-like success icon */}
                            <div className="mb-4">
                                <div className="w-20 h-20 mx-auto rounded-full bg-gradient-to-br from-emerald-400 to-green-500 flex items-center justify-center shadow-lg shadow-emerald-500/40 animate-bounce">
                                    <CheckCircleOutlined className="text-4xl text-white" />
                                </div>
                            </div>

                            <Title level={2} className="!text-emerald-400 !mb-2">
                                Đăng ký thành công!
                            </Title>

                            <Paragraph className="text-blue-300 text-base !mb-8">
                                Vui lòng chờ gọi số trên màn hình
                            </Paragraph>

                            {/* ── Queue Number (BIG display) ── */}
                            <div className="mb-8 p-8 rounded-2xl bg-white/10 border border-cyan-400/30">
                                <Text className="text-blue-300 text-sm block mb-2">SỐ THỨ TỰ CỦA BẠN</Text>
                                <div
                                    className="font-bold tracking-wider"
                                    style={{
                                        fontSize: 80,
                                        lineHeight: 1,
                                        background: 'linear-gradient(135deg, #22d3ee, #06b6d4, #0891b2)',
                                        WebkitBackgroundClip: 'text',
                                        WebkitTextFillColor: 'transparent',
                                    }}
                                >
                                    {registerResult.daily_sequence}
                                </div>
                                <Text className="text-blue-400 text-xs mt-2 block">
                                    {registerResult.queue_number}
                                </Text>
                            </div>

                            {/* ── Info cards ── */}
                            <div className="grid grid-cols-2 gap-4 mb-8">
                                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                    <ClockCircleOutlined className="text-2xl text-amber-400 mb-2" />
                                    <div className="text-white text-2xl font-bold">
                                        ~{registerResult.estimated_wait_minutes} phút
                                    </div>
                                    <Text className="text-blue-300 text-xs">Thời gian chờ ước tính</Text>
                                </div>
                                <div className="p-4 rounded-xl bg-white/5 border border-white/10">
                                    <FileTextOutlined className="text-2xl text-cyan-400 mb-2" />
                                    <div className="text-white text-sm font-medium truncate px-2">
                                        {registerResult.visit_code}
                                    </div>
                                    <Text className="text-blue-300 text-xs">Mã lượt khám</Text>
                                </div>
                            </div>

                            {/* ── Instructions ── */}
                            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 mb-8 text-left">
                                <Text className="text-amber-300 font-semibold block mb-2">📋 Hướng dẫn tiếp theo:</Text>
                                <ol className="text-amber-100/80 text-sm space-y-1 pl-4 list-decimal">
                                    <li>Ngồi chờ tại khu vực phòng khám</li>
                                    <li>Chú ý màn hình hiển thị và loa gọi số</li>
                                    <li>Khi được gọi, đến phòng đo sinh hiệu</li>
                                    <li>Sau đó chờ bác sĩ khám</li>
                                </ol>
                            </div>

                            {/* ── Auto-reset countdown ── */}
                            <div className="mb-4">
                                <Text className="text-blue-400/70 text-xs">
                                    Tự động quay về màn hình chính sau {countdown} giây
                                </Text>
                            </div>

                            <Button
                                size="large"
                                onClick={handleReset}
                                icon={<ReloadOutlined />}
                                style={{
                                    height: 48,
                                    borderRadius: 14,
                                    background: 'rgba(255,255,255,0.1)',
                                    border: '1px solid rgba(255,255,255,0.2)',
                                    color: '#fff',
                                    fontWeight: 500,
                                }}
                            >
                                Đăng ký bệnh nhân khác
                            </Button>
                        </Card>
                    )}
                </div>
            </main>

            {/* ── Footer ── */}
            <footer className="text-center py-4 text-blue-400/50 text-xs border-t border-white/5">
                Vui lòng giữ gìn thiết bị • Hotline hỗ trợ: <span className="text-cyan-400">1900 1234</span>
            </footer>

            <ScannerModal
                open={showScanner}
                onCancel={() => setShowScanner(false)}
                onScanSuccess={handleQrScanSuccess}
            />

            {/* ── Custom Styles ── */}
            <style jsx global>{`
                /* Steps indicator on dark background */
                .kiosk-steps .ant-steps-item-title {
                    color: rgba(255,255,255,0.7) !important;
                }
                .kiosk-steps .ant-steps-item-finish .ant-steps-item-title {
                    color: #22d3ee !important;
                }
                .kiosk-steps .ant-steps-item-process .ant-steps-item-title {
                    color: #fff !important;
                }
                .kiosk-steps .ant-steps-item-tail::after {
                    background-color: rgba(255,255,255,0.15) !important;
                }
                .kiosk-steps .ant-steps-item-finish .ant-steps-item-tail::after {
                    background-color: #22d3ee !important;
                }
                .kiosk-steps .ant-steps-item-icon {
                    background: rgba(255,255,255,0.1) !important;
                    border-color: rgba(255,255,255,0.2) !important;
                }
                .kiosk-steps .ant-steps-item-finish .ant-steps-item-icon,
                .kiosk-steps .ant-steps-item-process .ant-steps-item-icon {
                    background: linear-gradient(135deg, #06b6d4, #0891b2) !important;
                    border-color: #22d3ee !important;
                }

                /* Descriptions on dark bg */
                .kiosk-descriptions .ant-descriptions-item-label {
                    background: transparent !important;
                    border: none !important;
                }
                .kiosk-descriptions .ant-descriptions-item-content {
                    border: none !important;
                }
                .kiosk-descriptions .ant-descriptions-view {
                    border: none !important;
                }
                .kiosk-descriptions .ant-descriptions-row {
                    border: none !important;
                }

                /* Input styles for dark bg */
                .ant-input-affix-wrapper:has(input[class*="text-white"]) {
                    background: rgba(255,255,255,0.1) !important;
                    border-color: rgba(255,255,255,0.2) !important;
                }
                .ant-input-affix-wrapper:has(input[class*="text-white"]):hover,
                .ant-input-affix-wrapper:has(input[class*="text-white"]):focus-within {
                    border-color: #22d3ee !important;
                    box-shadow: 0 0 0 2px rgba(34,211,238,0.2) !important;
                }

                /* TextArea on dark bg */
                .ant-input-textarea textarea.ant-input {
                    background: rgba(255,255,255,0.1) !important;
                    border-color: rgba(255,255,255,0.2) !important;
                    color: #fff !important;
                }
                .ant-input-textarea textarea.ant-input:hover,
                .ant-input-textarea textarea.ant-input:focus {
                    border-color: #22d3ee !important;
                    box-shadow: 0 0 0 2px rgba(34,211,238,0.2) !important;
                }
                .ant-input-textarea .ant-input-data-count {
                    color: rgba(147,197,253,0.5) !important;
                }

                /* Bounce animation */
                @keyframes bounce {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-10px); }
                }
                .animate-bounce {
                    animation: bounce 1s ease-in-out 3;
                }
            `}</style>
        </div>
    );
}
