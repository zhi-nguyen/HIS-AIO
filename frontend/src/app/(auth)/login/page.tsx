'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Form, Input, Button, Card, Typography, Space } from 'antd';
import { MailOutlined, LockOutlined, MedicineBoxOutlined } from '@ant-design/icons';
import { useAuth } from '@/contexts/AuthContext';

const { Title, Text } = Typography;

interface LoginFormValues {
    email: string;
    password: string;
}

/**
 * Login Page
 * Trang đăng nhập hệ thống HIS
 * Sử dụng email làm username (theo backend)
 */
export default function LoginPage() {
    const router = useRouter();
    const { login, isAuthenticated, isLoading } = useAuth();
    const [form] = Form.useForm();

    // Redirect nếu đã đăng nhập
    useEffect(() => {
        if (isAuthenticated) {
            router.push('/dashboard');
        }
    }, [isAuthenticated, router]);

    const handleSubmit = async (values: LoginFormValues) => {
        const success = await login(values.email, values.password);
        if (success) {
            router.push('/dashboard');
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-blue-100 p-4">
            <Card
                className="w-full max-w-md shadow-xl"
                styles={{
                    body: { padding: '40px 32px' }
                }}
            >
                {/* Logo & Title */}
                <div className="text-center mb-8">
                    <Space orientation="vertical" size="small">
                        <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-500 rounded-full mb-2">
                            <MedicineBoxOutlined className="text-3xl text-white" />
                        </div>
                        <Title level={3} className="!mb-1">
                            HIS - Hospital System
                        </Title>
                        <Text type="secondary">
                            Hệ thống Quản lý Bệnh viện Thông minh
                        </Text>
                    </Space>
                </div>

                {/* Login Form */}
                <Form
                    form={form}
                    name="login"
                    onFinish={handleSubmit}
                    layout="vertical"
                    size="large"
                    requiredMark={false}
                >
                    <Form.Item
                        name="email"
                        rules={[
                            { required: true, message: 'Vui lòng nhập email!' },
                            { type: 'email', message: 'Email không hợp lệ!' }
                        ]}
                    >
                        <Input
                            prefix={<MailOutlined className="text-gray-400" />}
                            placeholder="Email"
                            autoComplete="email"
                        />
                    </Form.Item>

                    <Form.Item
                        name="password"
                        rules={[{ required: true, message: 'Vui lòng nhập mật khẩu!' }]}
                    >
                        <Input.Password
                            prefix={<LockOutlined className="text-gray-400" />}
                            placeholder="Mật khẩu"
                            autoComplete="current-password"
                        />
                    </Form.Item>

                    <Form.Item className="mb-2">
                        <Button
                            type="primary"
                            htmlType="submit"
                            block
                            loading={isLoading}
                            className="h-11"
                        >
                            Đăng nhập
                        </Button>
                    </Form.Item>
                </Form>

                {/* Footer */}
                <div className="text-center mt-6">
                    <Text type="secondary" className="text-xs">
                        © 2024 HIS - Hospital Information System
                    </Text>
                </div>
            </Card>
        </div>
    );
}
