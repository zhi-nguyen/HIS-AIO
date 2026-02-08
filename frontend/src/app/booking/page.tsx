'use client';

import { useState } from 'react';
import {
    Form,
    Input,
    Select,
    DatePicker,
    Button,
    Typography,
    Card,
    message,
    Result,
} from 'antd';
import {
    CalendarOutlined,
    UserOutlined,
    PhoneOutlined,
    MedicineBoxOutlined,
    ArrowLeftOutlined,
} from '@ant-design/icons';
import Link from 'next/link';

const { Title, Text } = Typography;
const { TextArea } = Input;

/**
 * Booking Page - Trang đặt lịch khám
 */

const departments = [
    { value: 'internal', label: 'Nội khoa' },
    { value: 'surgery', label: 'Ngoại khoa' },
    { value: 'pediatrics', label: 'Nhi khoa' },
    { value: 'obstetrics', label: 'Sản phụ khoa' },
    { value: 'cardiology', label: 'Tim mạch' },
    { value: 'dermatology', label: 'Da liễu' },
    { value: 'orthopedics', label: 'Chấn thương chỉnh hình' },
    { value: 'neurology', label: 'Thần kinh' },
    { value: 'ophthalmology', label: 'Mắt' },
    { value: 'ent', label: 'Tai mũi họng' },
];

export default function BookingPage() {
    const [form] = Form.useForm();
    const [loading, setLoading] = useState(false);
    const [success, setSuccess] = useState(false);

    const handleSubmit = async (values: Record<string, unknown>) => {
        setLoading(true);
        try {
            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 1500));
            console.log('Booking data:', values);
            setSuccess(true);
            message.success('Đặt lịch thành công!');
        } catch (error) {
            message.error('Có lỗi xảy ra. Vui lòng thử lại.');
        } finally {
            setLoading(false);
        }
    };

    if (success) {
        return (
            <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
                <Result
                    status="success"
                    title="Đặt lịch thành công!"
                    subTitle="Chúng tôi sẽ liên hệ với bạn qua số điện thoại đã đăng ký để xác nhận lịch hẹn."
                    extra={[
                        <Link key="home" href="/">
                            <Button type="primary">Về trang chủ</Button>
                        </Link>,
                        <Button key="new" onClick={() => { setSuccess(false); form.resetFields(); }}>
                            Đặt lịch mới
                        </Button>,
                    ]}
                />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-blue-50 to-cyan-50">
            {/* Header */}
            <header className="bg-white shadow-sm">
                <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-4">
                    <Link href="/" className="text-gray-600 hover:text-blue-600">
                        <ArrowLeftOutlined className="text-xl" />
                    </Link>
                    <div className="flex items-center gap-3">
                        <MedicineBoxOutlined className="text-2xl text-blue-600" />
                        <span className="font-bold text-gray-800">Bệnh Viện Đa Khoa ABC</span>
                    </div>
                </div>
            </header>

            {/* Form */}
            <div className="max-w-2xl mx-auto px-4 py-12">
                <Card className="shadow-xl rounded-2xl">
                    <div className="text-center mb-8">
                        <CalendarOutlined className="text-5xl text-blue-500 mb-4" />
                        <Title level={2} className="!mb-2">Đặt Lịch Khám</Title>
                        <Text type="secondary">Vui lòng điền thông tin để chúng tôi liên hệ xác nhận</Text>
                    </div>

                    <Form form={form} layout="vertical" onFinish={handleSubmit}>
                        <div className="grid md:grid-cols-2 gap-4">
                            <Form.Item
                                name="fullName"
                                label="Họ và tên"
                                rules={[{ required: true, message: 'Vui lòng nhập họ tên' }]}
                            >
                                <Input prefix={<UserOutlined />} placeholder="Nguyễn Văn A" size="large" />
                            </Form.Item>

                            <Form.Item
                                name="phone"
                                label="Số điện thoại"
                                rules={[{ required: true, message: 'Vui lòng nhập SĐT' }]}
                            >
                                <Input prefix={<PhoneOutlined />} placeholder="0901234567" size="large" />
                            </Form.Item>
                        </div>

                        <div className="grid md:grid-cols-2 gap-4">
                            <Form.Item
                                name="department"
                                label="Chuyên khoa"
                                rules={[{ required: true, message: 'Vui lòng chọn chuyên khoa' }]}
                            >
                                <Select options={departments} placeholder="Chọn chuyên khoa" size="large" />
                            </Form.Item>

                            <Form.Item
                                name="preferredDate"
                                label="Ngày mong muốn"
                                rules={[{ required: true, message: 'Vui lòng chọn ngày' }]}
                            >
                                <DatePicker
                                    className="w-full"
                                    size="large"
                                    placeholder="Chọn ngày"
                                    format="DD/MM/YYYY"
                                />
                            </Form.Item>
                        </div>

                        <Form.Item name="symptoms" label="Triệu chứng / Lý do khám">
                            <TextArea rows={4} placeholder="Mô tả triệu chứng hoặc lý do bạn muốn khám..." />
                        </Form.Item>

                        <Form.Item>
                            <Button
                                type="primary"
                                htmlType="submit"
                                loading={loading}
                                block
                                size="large"
                                className="h-12 text-lg"
                            >
                                <CalendarOutlined className="mr-2" />
                                Xác nhận đặt lịch
                            </Button>
                        </Form.Item>
                    </Form>

                    <div className="text-center mt-4">
                        <Text type="secondary">
                            Hoặc gọi hotline: <a href="tel:19001234" className="text-blue-600 font-semibold">1900 1234</a>
                        </Text>
                    </div>
                </Card>
            </div>
        </div>
    );
}
