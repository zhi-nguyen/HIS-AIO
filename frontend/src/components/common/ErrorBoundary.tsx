'use client';

import { Component, ReactNode } from 'react';
import { Result, Button, Typography } from 'antd';
import { ReloadOutlined, HomeOutlined } from '@ant-design/icons';

const { Paragraph, Text } = Typography;

/**
 * Error Boundary Component
 * Bắt lỗi React và hiển thị UI thân thiện
 */

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error?: Error;
    errorInfo?: string;
}

export default class ErrorBoundary extends Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({
            errorInfo: errorInfo.componentStack || undefined,
        });

        // Log to error tracking service (e.g., Sentry)
        // if (typeof window !== 'undefined' && window.Sentry) {
        //     window.Sentry.captureException(error);
        // }
    }

    handleReload = () => {
        window.location.reload();
    };

    handleGoHome = () => {
        window.location.href = '/dashboard';
    };

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) {
                return this.props.fallback;
            }

            return (
                <Result
                    status="error"
                    title="Đã xảy ra lỗi"
                    subTitle="Xin lỗi, đã có lỗi xảy ra trong ứng dụng. Vui lòng thử lại hoặc liên hệ hỗ trợ."
                    extra={[
                        <Button
                            key="reload"
                            type="primary"
                            icon={<ReloadOutlined />}
                            onClick={this.handleReload}
                        >
                            Tải lại trang
                        </Button>,
                        <Button
                            key="home"
                            icon={<HomeOutlined />}
                            onClick={this.handleGoHome}
                        >
                            Về trang chủ
                        </Button>,
                    ]}
                >
                    {process.env.NODE_ENV === 'development' && this.state.error && (
                        <div className="mt-4 p-4 bg-gray-100 rounded text-left overflow-auto max-h-64">
                            <Paragraph>
                                <Text strong className="text-red-500">
                                    {this.state.error.name}: {this.state.error.message}
                                </Text>
                            </Paragraph>
                            {this.state.errorInfo && (
                                <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                                    {this.state.errorInfo}
                                </pre>
                            )}
                        </div>
                    )}
                </Result>
            );
        }

        return this.props.children;
    }
}
