'use client';

import { useState } from 'react';
import { Input, Button, Select, Typography } from 'antd';
import {
    CalendarOutlined,
    UserOutlined,
    PhoneOutlined,
    CheckCircleOutlined,
    CloseOutlined,
    ClockCircleOutlined,
    MedicineBoxOutlined,
} from '@ant-design/icons';

const { Text } = Typography;

/**
 * BookingForm Component
 * 
 * Form đặt lịch khám hiển thị inline trong chat khi Agent gọi tool open_booking_form.
 * Nhận thông tin khoa, ngày, khung giờ gợi ý từ Agent và để bệnh nhân
 * điền thêm thông tin cá nhân (tên, SĐT, lý do khám).
 * 
 * Flow:
 * 1. Agent gọi open_booking_form → SSE event ui_action → render form này
 * 2. Bệnh nhân điền form → Submit
 * 3. POST /api/v1/appointments/book/ → Django tạo Appointment
 * 4. Gọi onSubmitted(bookingRef) để notify Agent
 */

interface BookingFormProps {
    /** Tên khoa cần đặt lịch (từ Agent) */
    department: string;
    /** Ngày đặt lịch YYYY-MM-DD (từ Agent) */
    date: string;
    /** Danh sách khung giờ gợi ý (từ Agent) */
    suggestedTimes: string[];
    /** Ghi chú từ Agent (nếu có) */
    patientNote?: string;
    /** Callback khi đặt lịch thành công */
    onSubmitted: (bookingRef: string) => void;
    /** Callback khi hủy form */
    onCancel: () => void;
}

export default function BookingForm({
    department,
    date,
    suggestedTimes,
    patientNote = '',
    onSubmitted,
    onCancel,
}: BookingFormProps) {
    const [patientName, setPatientName] = useState('');
    const [phone, setPhone] = useState('');
    const [selectedTime, setSelectedTime] = useState<string>(suggestedTimes[0] || '');
    const [reason, setReason] = useState(patientNote);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState('');

    const handleSubmit = async () => {
        // Validate
        if (!patientName.trim()) {
            setError('Vui lòng nhập họ tên');
            return;
        }
        if (!phone.trim() || phone.length < 9) {
            setError('Vui lòng nhập số điện thoại hợp lệ');
            return;
        }
        if (!selectedTime) {
            setError('Vui lòng chọn khung giờ');
            return;
        }

        setError('');
        setSubmitting(true);

        try {
            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
            const response = await fetch(`${baseUrl}/appointments/book/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    patient_name: patientName.trim(),
                    phone: phone.trim(),
                    department,
                    date,
                    time: selectedTime,
                    reason: reason.trim(),
                }),
            });

            const data = await response.json();

            if (data.success) {
                onSubmitted(data.booking_ref);
            } else {
                setError(data.error || 'Đặt lịch thất bại. Vui lòng thử lại.');
            }
        } catch {
            setError('Lỗi kết nối. Vui lòng thử lại sau.');
        } finally {
            setSubmitting(false);
        }
    };

    // Format ngày hiển thị
    const displayDate = (() => {
        try {
            const d = new Date(date + 'T00:00:00');
            return d.toLocaleDateString('vi-VN', { weekday: 'long', day: '2-digit', month: '2-digit', year: 'numeric' });
        } catch {
            return date;
        }
    })();

    return (
        <div
            style={{
                backgroundColor: '#f0f7ff',
                border: '1px solid #91caff',
                borderRadius: '12px',
                padding: '16px',
                marginTop: '8px',
                maxWidth: '100%',
            }}
        >
            {/* Header */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CalendarOutlined style={{ fontSize: '18px', color: '#1677ff' }} />
                    <Text strong style={{ fontSize: '14px', color: '#1677ff' }}>Đặt lịch khám</Text>
                </div>
                <Button
                    type="text"
                    size="small"
                    icon={<CloseOutlined />}
                    onClick={onCancel}
                    style={{ color: '#999' }}
                />
            </div>

            {/* Pre-filled info */}
            <div
                style={{
                    backgroundColor: '#e6f4ff',
                    borderRadius: '8px',
                    padding: '10px 12px',
                    marginBottom: '12px',
                    fontSize: '13px',
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                    <MedicineBoxOutlined style={{ color: '#1677ff' }} />
                    <span><strong>Khoa:</strong> {department}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CalendarOutlined style={{ color: '#1677ff' }} />
                    <span><strong>Ngày:</strong> {displayDate}</span>
                </div>
            </div>

            {/* Form fields */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div>
                    <Text style={{ fontSize: '12px', color: '#666', marginBottom: '4px', display: 'block' }}>
                        Họ và tên <span style={{ color: 'red' }}>*</span>
                    </Text>
                    <Input
                        prefix={<UserOutlined style={{ color: '#bbb' }} />}
                        placeholder="Nguyễn Văn A"
                        value={patientName}
                        onChange={(e) => setPatientName(e.target.value)}
                        size="small"
                        style={{ borderRadius: '6px' }}
                    />
                </div>

                <div>
                    <Text style={{ fontSize: '12px', color: '#666', marginBottom: '4px', display: 'block' }}>
                        Số điện thoại <span style={{ color: 'red' }}>*</span>
                    </Text>
                    <Input
                        prefix={<PhoneOutlined style={{ color: '#bbb' }} />}
                        placeholder="0901234567"
                        value={phone}
                        onChange={(e) => setPhone(e.target.value)}
                        size="small"
                        style={{ borderRadius: '6px' }}
                        maxLength={11}
                    />
                </div>

                <div>
                    <Text style={{ fontSize: '12px', color: '#666', marginBottom: '4px', display: 'block' }}>
                        Khung giờ <span style={{ color: 'red' }}>*</span>
                    </Text>
                    <Select
                        value={selectedTime || undefined}
                        onChange={setSelectedTime}
                        placeholder="Chọn giờ khám"
                        size="small"
                        style={{ width: '100%', borderRadius: '6px' }}
                        suffixIcon={<ClockCircleOutlined />}
                    >
                        {suggestedTimes.map((time) => (
                            <Select.Option key={time} value={time}>
                                {time}
                            </Select.Option>
                        ))}
                    </Select>
                </div>

                <div>
                    <Text style={{ fontSize: '12px', color: '#666', marginBottom: '4px', display: 'block' }}>
                        Lý do khám
                    </Text>
                    <Input.TextArea
                        placeholder="Mô tả triệu chứng hoặc lý do khám..."
                        value={reason}
                        onChange={(e) => setReason(e.target.value)}
                        rows={2}
                        style={{ borderRadius: '6px', fontSize: '13px' }}
                    />
                </div>

                {/* Error message */}
                {error && (
                    <div style={{ color: '#ff4d4f', fontSize: '12px', padding: '4px 0' }}>
                        {error}
                    </div>
                )}

                {/* Actions */}
                <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                    <Button
                        type="primary"
                        size="small"
                        icon={<CheckCircleOutlined />}
                        onClick={handleSubmit}
                        loading={submitting}
                        style={{ flex: 1, borderRadius: '6px', fontWeight: 500 }}
                    >
                        Xác nhận đặt lịch
                    </Button>
                    <Button
                        size="small"
                        onClick={onCancel}
                        style={{ borderRadius: '6px' }}
                    >
                        Hủy
                    </Button>
                </div>
            </div>
        </div>
    );
}
