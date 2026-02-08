'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Card, Input, Button, Space, Typography, Avatar, Spin, Tooltip } from 'antd';
import {
    SendOutlined,
    RobotOutlined,
    UserOutlined,
    CloseOutlined,
    CopyOutlined,
    CheckOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';

const { Text } = Typography;

/**
 * AI Chat Component với SSE Streaming
 * Hỗ trợ AI trò chuyện trong quá trình khám
 */

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
}

interface AIChatProps {
    visitId: string;
    patientContext?: string;
    onClose?: () => void;
}

export default function AIChat({ visitId, patientContext, onClose }: AIChatProps) {
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: 'Xin chào! Tôi là trợ lý AI. Tôi có thể giúp bạn:\n- Phân tích triệu chứng\n- Đề xuất chẩn đoán phân biệt\n- Tra cứu thông tin y khoa\n- Kiểm tra tương tác thuốc\n\nHãy hỏi bất cứ điều gì bạn cần!',
            timestamp: new Date(),
        },
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [copied, setCopied] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    // Auto scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Copy message to clipboard
    const handleCopy = useCallback((text: string, id: string) => {
        navigator.clipboard.writeText(text);
        setCopied(id);
        setTimeout(() => setCopied(null), 2000);
    }, []);

    // Send message with SSE streaming
    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: input,
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        // Create assistant message placeholder
        const assistantId = (Date.now() + 1).toString();
        setMessages(prev => [
            ...prev,
            {
                id: assistantId,
                role: 'assistant',
                content: '',
                timestamp: new Date(),
                isStreaming: true,
            },
        ]);

        try {
            // Abort previous request if any
            abortControllerRef.current?.abort();
            abortControllerRef.current = new AbortController();

            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
            const token = localStorage.getItem('access_token');

            const response = await fetch(`${baseUrl}/chat/stream/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
                body: JSON.stringify({
                    visit_id: visitId,
                    message: input,
                    context: patientContext,
                }),
                signal: abortControllerRef.current.signal,
            });

            if (!response.ok) throw new Error('API error');

            const reader = response.body?.getReader();
            const decoder = new TextDecoder();

            if (reader) {
                let fullContent = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.text) {
                                    fullContent += data.text;
                                    setMessages(prev =>
                                        prev.map(m =>
                                            m.id === assistantId ? { ...m, content: fullContent } : m
                                        )
                                    );
                                }
                            } catch {
                                // Non-JSON line, could be raw text
                                const text = line.slice(6);
                                if (text && text !== '[DONE]') {
                                    fullContent += text;
                                    setMessages(prev =>
                                        prev.map(m =>
                                            m.id === assistantId ? { ...m, content: fullContent } : m
                                        )
                                    );
                                }
                            }
                        }
                    }
                }

                // Mark streaming as complete
                setMessages(prev =>
                    prev.map(m =>
                        m.id === assistantId ? { ...m, isStreaming: false } : m
                    )
                );
            }
        } catch (error) {
            if ((error as Error).name === 'AbortError') return;

            console.error('Chat error:', error);
            setMessages(prev =>
                prev.map(m =>
                    m.id === (Date.now() + 1).toString()
                        ? { ...m, content: 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau.', isStreaming: false }
                        : m
                )
            );
        } finally {
            setLoading(false);
        }
    };

    // Handle enter key
    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    // Stop streaming
    const handleStop = () => {
        abortControllerRef.current?.abort();
        setLoading(false);
    };

    return (
        <Card
            title={
                <Space>
                    <RobotOutlined className="text-blue-500" />
                    <span>Trợ lý AI</span>
                </Space>
            }
            extra={
                <Space>
                    {loading && (
                        <Button size="small" danger onClick={handleStop}>
                            Dừng
                        </Button>
                    )}
                    {onClose && <Button type="text" icon={<CloseOutlined />} onClick={onClose} />}
                </Space>
            }
            className="h-full flex flex-col"
            styles={{ body: { flex: 1, display: 'flex', flexDirection: 'column', padding: '12px' } }}
        >
            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-3 mb-3 max-h-[400px]">
                {messages.map((msg) => (
                    <div
                        key={msg.id}
                        className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                    >
                        <Avatar
                            icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                            className={msg.role === 'user' ? 'bg-blue-500' : 'bg-green-500'}
                            size="small"
                        />
                        <div
                            className={`max-w-[80%] p-2 rounded-lg relative group ${msg.role === 'user'
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-gray-100 text-gray-800'
                                }`}
                        >
                            {msg.role === 'assistant' ? (
                                <div className="prose prose-sm max-w-none">
                                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                                    {msg.isStreaming && <span className="animate-pulse">▊</span>}
                                </div>
                            ) : (
                                <Text className="text-white">{msg.content}</Text>
                            )}

                            {/* Copy button */}
                            {msg.role === 'assistant' && msg.content && !msg.isStreaming && (
                                <Tooltip title={copied === msg.id ? 'Đã sao chép!' : 'Sao chép'}>
                                    <Button
                                        type="text"
                                        size="small"
                                        icon={copied === msg.id ? <CheckOutlined /> : <CopyOutlined />}
                                        className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity"
                                        onClick={() => handleCopy(msg.content, msg.id)}
                                    />
                                </Tooltip>
                            )}
                        </div>
                    </div>
                ))}
                {loading && messages[messages.length - 1]?.content === '' && (
                    <div className="flex gap-2">
                        <Avatar icon={<RobotOutlined />} className="bg-green-500" size="small" />
                        <div className="bg-gray-100 p-2 rounded-lg">
                            <Spin size="small" />
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <Space.Compact className="w-full">
                <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Nhập câu hỏi... (Enter để gửi)"
                    disabled={loading}
                />
                <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    loading={loading}
                />
            </Space.Compact>
        </Card>
    );
}
