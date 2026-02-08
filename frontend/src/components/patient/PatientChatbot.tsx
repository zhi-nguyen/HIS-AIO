'use client';

import { useState, useRef, useEffect } from 'react';
import { Button, Input, Typography, Avatar, Spin, Tag } from 'antd';
import {
    SendOutlined,
    RobotOutlined,
    UserOutlined,
    CloseOutlined,
    MessageOutlined,
    AlertOutlined,
    WarningOutlined,
    CalendarOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';

const { Text } = Typography;

/**
 * Patient Chatbot Component
 * AI Chatbot công khai cho bệnh nhân hỏi đáp
 */

// Urgency level configuration
const urgencyConfig: Record<string, { icon: React.ReactNode; color: string; bg: string; label: string }> = {
    URGENT_HIGH: { icon: <AlertOutlined />, color: '#ff4d4f', bg: '#fff1f0', label: 'Cần cấp cứu ngay' },
    URGENT_MODERATE: { icon: <WarningOutlined />, color: '#fa8c16', bg: '#fff7e6', label: 'Cần khám sớm trong ngày' },
    URGENT_LOW: { icon: <CalendarOutlined />, color: '#52c41a', bg: '#f6ffed', label: 'Có thể đặt lịch hẹn' },
};

// Component to render urgency badge
function UrgencyBadge({ content }: { content: string }) {
    const urgencyMatch = content.match(/\[URGENT_(HIGH|MODERATE|LOW)\]/);
    if (!urgencyMatch) return null;

    const level = `URGENT_${urgencyMatch[1]}` as keyof typeof urgencyConfig;
    const config = urgencyConfig[level];
    if (!config) return null;

    return (
        <div
            className="flex items-center gap-2 p-2 rounded-lg mb-2 font-medium"
            style={{ backgroundColor: config.bg, color: config.color, border: `1px solid ${config.color}` }}
        >
            {config.icon}
            <span>{config.label}</span>
        </div>
    );
}

// Clean urgency tags from content
function cleanUrgencyTags(content: string): string {
    return content.replace(/\[URGENT_(HIGH|MODERATE|LOW)\]/g, '').trim();
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
}

interface PatientChatbotProps {
    apiEndpoint?: string;
}

export default function PatientChatbot({ apiEndpoint = '/chat/stream/' }: PatientChatbotProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>([
        {
            id: '1',
            role: 'assistant',
            content: 'Xin chào! Tôi là trợ lý AI của Bệnh viện. Tôi có thể giúp bạn:\n\n• Tìm hiểu về dịch vụ y tế\n• Hướng dẫn đặt lịch khám\n• Giải đáp thắc mắc sức khỏe cơ bản\n• Cung cấp thông tin liên hệ\n\nBạn cần hỗ trợ gì ạ?',
            timestamp: new Date(),
        },
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [isComposing, setIsComposing] = useState(false); // For Vietnamese IME
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

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

        const assistantId = (Date.now() + 1).toString();
        setMessages(prev => [
            ...prev,
            { id: assistantId, role: 'assistant', content: '', timestamp: new Date(), isStreaming: true },
        ]);

        try {
            abortControllerRef.current?.abort();
            abortControllerRef.current = new AbortController();

            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

            const response = await fetch(`${baseUrl}${apiEndpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: input }),
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

                                // Backend format:
                                // {"type": "result_json", "content": {"message": "...", "final_response": "..."}}
                                // {"type": "token", "content": "text"} 
                                // {"type": "done", "full_response": "..."}
                                // {"type": "status", "message": "..."} - Status (ignore)

                                if (data.type === 'result_json' && data.content) {
                                    // Extract message from nested content object
                                    const text = data.content.message || data.content.final_response || '';
                                    if (text) {
                                        fullContent = text;
                                        setMessages(prev =>
                                            prev.map(m => m.id === assistantId ? { ...m, content: fullContent } : m)
                                        );
                                    }
                                } else if (data.type === 'token' && typeof data.content === 'string') {
                                    fullContent += data.content;
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId ? { ...m, content: fullContent } : m)
                                    );
                                } else if (data.type === 'done' && data.full_response) {
                                    fullContent = data.full_response;
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId ? { ...m, content: fullContent } : m)
                                    );
                                }
                                // Ignore status messages (type: "status")
                            } catch {
                                // Handle plain text (non-JSON)
                                const text = line.slice(6);
                                if (text && text !== '[DONE]') {
                                    fullContent += text;
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId ? { ...m, content: fullContent } : m)
                                    );
                                }
                            }
                        }
                    }
                }
                setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, isStreaming: false } : m));
            }
        } catch (error) {
            if ((error as Error).name === 'AbortError') return;
            console.error('Chat error:', error);
            setMessages(prev =>
                prev.map(m =>
                    m.id === assistantId
                        ? { ...m, content: 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau hoặc gọi hotline: 1900-xxxx', isStreaming: false }
                        : m
                )
            );
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <>
            {/* Floating Button */}
            {!isOpen && (
                <button
                    onClick={() => setIsOpen(true)}
                    className="fixed bottom-6 right-6 w-16 h-16 bg-gradient-to-r from-blue-500 to-blue-600 rounded-full shadow-2xl flex items-center justify-center text-white text-2xl hover:scale-110 transition-transform z-50 animate-bounce"
                >
                    <MessageOutlined />
                </button>
            )}

            {/* Chat Window */}
            {isOpen && (
                <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-white rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden border border-gray-200">
                    {/* Header */}
                    <div className="bg-gradient-to-r from-blue-500 to-blue-600 p-4 flex items-center justify-between text-white">
                        <div className="flex items-center gap-3">
                            <Avatar icon={<RobotOutlined />} className="bg-white/20" />
                            <div>
                                <Text strong className="text-white block">Trợ lý AI</Text>
                                <Text className="text-white/70 text-xs">Hỗ trợ 24/7</Text>
                            </div>
                        </div>
                        <Button
                            type="text"
                            icon={<CloseOutlined className="text-white" />}
                            onClick={() => setIsOpen(false)}
                        />
                    </div>

                    {/* Messages */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-50">
                        {messages.map((msg) => {
                            // Skip rendering empty assistant messages (show loading spinner instead)
                            if (msg.role === 'assistant' && !msg.content && msg.isStreaming) {
                                return null;
                            }

                            return (
                                <div
                                    key={msg.id}
                                    className={`flex gap-2 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                                >
                                    <Avatar
                                        icon={msg.role === 'user' ? <UserOutlined /> : <RobotOutlined />}
                                        size="small"
                                        className={msg.role === 'user' ? 'bg-blue-500' : 'bg-green-500'}
                                    />
                                    <div
                                        className={`max-w-[80%] p-3 rounded-2xl ${msg.role === 'user'
                                            ? 'bg-blue-500 text-white rounded-br-none'
                                            : 'bg-white text-gray-800 rounded-bl-none shadow-sm'
                                            }`}
                                    >
                                        {msg.role === 'assistant' ? (
                                            <div className="prose prose-sm max-w-none text-sm">
                                                <UrgencyBadge content={msg.content} />
                                                <ReactMarkdown>{cleanUrgencyTags(msg.content)}</ReactMarkdown>
                                                {msg.isStreaming && msg.content && <span className="animate-pulse">▊</span>}
                                            </div>
                                        ) : (
                                            <span className="text-sm">{msg.content}</span>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                        {loading && messages[messages.length - 1]?.content === '' && (
                            <div className="flex gap-2">
                                <Avatar icon={<RobotOutlined />} className="bg-green-500" size="small" />
                                <div className="bg-white p-3 rounded-2xl shadow-sm">
                                    <Spin size="small" />
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>

                    {/* Input */}
                    <div className="p-3 border-t bg-white">
                        <div className="flex gap-2">
                            <Input
                                value={input}
                                onChange={(e) => setInput(e.target.value)}
                                onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey && !isComposing) {
                                        e.preventDefault();
                                        handleSend();
                                    }
                                }}
                                onCompositionStart={() => setIsComposing(true)}
                                onCompositionEnd={() => setIsComposing(false)}
                                placeholder="Nhập câu hỏi của bạn..."
                                disabled={loading}
                                className="rounded-full"
                                style={{ fontFamily: '"Segoe UI", "Roboto", "Helvetica Neue", Arial, "Noto Sans", sans-serif' }}
                            />
                            <Button
                                type="primary"
                                shape="circle"
                                icon={<SendOutlined />}
                                onClick={handleSend}
                                loading={loading}
                            />
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
