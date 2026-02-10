'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Card, Input, Button, Space, Typography, Avatar, Spin, Tooltip } from 'antd';
const { TextArea } = Input;
import {
    SendOutlined,
    RobotOutlined,
    UserOutlined,
    CloseOutlined,
    CopyOutlined,
    CheckOutlined,
    DownOutlined,
    RightOutlined,
    LoadingOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';

const { Text } = Typography;

/**
 * AI Chat Component với SSE Streaming
 * Hỗ trợ AI trò chuyện trong quá trình khám
 * 
 * Features:
 * - Lưu lịch sử chat vào localStorage theo visitId (TTL 1 giờ)
 * - Hiển thị quá trình "thinking" của AI phía trên câu trả lời
 */

// ==========================================
// Chat History Persistence (localStorage)
// ==========================================
const CHAT_STORAGE_PREFIX = 'ai_chat_history_';
const CHAT_TTL_MS = 60 * 60 * 1000; // 1 giờ

interface StoredChat {
    messages: StoredMessage[];
    lastMessageAt: number;
}

interface StoredMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    thinking?: string;
    timestamp: string;
}

function saveChatToStorage(key: string, messages: Message[]) {
    if (typeof window === 'undefined') return;
    try {
        const data: StoredChat = {
            messages: messages.map(m => ({
                id: m.id,
                role: m.role,
                content: m.content,
                thinking: m.thinking,
                timestamp: m.timestamp.toISOString(),
            })),
            lastMessageAt: Date.now(),
        };
        localStorage.setItem(key, JSON.stringify(data));
    } catch {
        // localStorage full hoặc không khả dụng
    }
}

function loadChatFromStorage(key: string): Message[] | null {
    if (typeof window === 'undefined') return null;
    try {
        const raw = localStorage.getItem(key);
        if (!raw) return null;

        const data: StoredChat = JSON.parse(raw);
        const elapsed = Date.now() - data.lastMessageAt;

        if (elapsed > CHAT_TTL_MS) {
            localStorage.removeItem(key);
            return null;
        }

        return data.messages.map(m => ({
            id: m.id,
            role: m.role,
            content: m.content,
            thinking: m.thinking,
            timestamp: new Date(m.timestamp),
        }));
    } catch {
        localStorage.removeItem(key);
        return null;
    }
}

// ==========================================
// Thinking Section Component
// ==========================================

/** Lọc bỏ phần JSON routing, chỉ giữ từ "**Bước 1" trở đi */
function cleanThinkingContent(raw: string): string {
    const match = raw.match(/\*\*Bước 1/);
    if (match && match.index !== undefined) {
        return raw.slice(match.index).trim();
    }
    const cleaned = raw.replace(/```[\s\S]*?```/g, '').trim();
    return cleaned || raw;
}

function ThinkingSection({ thinking, isStreaming }: { thinking: string; isStreaming: boolean }) {
    const [expanded, setExpanded] = useState(false);
    const displayThinking = thinking ? cleanThinkingContent(thinking) : '';

    if (!displayThinking && !isStreaming) return null;

    if (isStreaming) {
        return (
            <div
                style={{
                    backgroundColor: '#fffbe6',
                    border: '1px solid #ffe58f',
                    borderRadius: '8px',
                    padding: '8px 12px',
                    marginBottom: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '13px',
                    color: '#d48806',
                }}
            >
                <LoadingOutlined spin style={{ fontSize: '14px' }} />
                <span style={{ fontWeight: 500 }}>Đang tư duy</span>
                <span className="animate-pulse">● ● ●</span>
            </div>
        );
    }

    if (!displayThinking) return null;

    return (
        <div style={{ marginBottom: '8px' }}>
            <button
                onClick={() => setExpanded(!expanded)}
                style={{
                    background: '#fffbe6',
                    border: '1px solid #ffe58f',
                    borderRadius: expanded ? '8px 8px 0 0' : '8px',
                    padding: '8px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    fontSize: '13px',
                    color: '#d48806',
                    cursor: 'pointer',
                    width: '100%',
                    fontWeight: 500,
                }}
            >
                {expanded ? <DownOutlined style={{ fontSize: '10px' }} /> : <RightOutlined style={{ fontSize: '10px' }} />}
                <span>Hiện quá trình tư duy</span>
            </button>
            {expanded && (
                <div
                    style={{
                        backgroundColor: '#fffef5',
                        border: '1px solid #ffe58f',
                        borderTop: 'none',
                        borderRadius: '0 0 8px 8px',
                        padding: '8px 12px',
                        fontSize: '12px',
                        color: '#8c6d1f',
                        maxHeight: '200px',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap',
                        lineHeight: '1.5',
                    }}
                >
                    {displayThinking}
                </div>
            )}
        </div>
    );
}

// ==========================================
// Interfaces
// ==========================================
interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    thinking?: string;
    timestamp: Date;
    isStreaming?: boolean;
    isThinking?: boolean;
}

interface AIChatProps {
    visitId: string;
    patientContext?: string;
    onClose?: () => void;
}

export default function AIChat({ visitId, patientContext, onClose }: AIChatProps) {
    const storageKey = `${CHAT_STORAGE_PREFIX}${visitId}`;

    const WELCOME_MESSAGE: Message = {
        id: '1',
        role: 'assistant',
        content: 'Xin chào! Tôi là trợ lý AI. Tôi có thể giúp bạn:\n- Phân tích triệu chứng\n- Đề xuất chẩn đoán phân biệt\n- Tra cứu thông tin y khoa\n- Kiểm tra tương tác thuốc\n\nHãy hỏi bất cứ điều gì bạn cần!',
        timestamp: new Date(),
    };

    const [messages, setMessages] = useState<Message[]>(() => {
        const stored = loadChatFromStorage(storageKey);
        return stored && stored.length > 0 ? stored : [WELCOME_MESSAGE];
    });
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [copied, setCopied] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);

    // Auto scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Lưu messages vào localStorage khi thay đổi (bỏ qua khi đang streaming)
    useEffect(() => {
        const hasStreaming = messages.some(m => m.isStreaming);
        if (!hasStreaming) {
            saveChatToStorage(storageKey, messages);
        }
    }, [messages, storageKey]);

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
                isThinking: true,
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
                let thinkingContent = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value, { stream: true });
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));

                                if (data.type === 'thinking' && typeof data.content === 'string') {
                                    // Phase 1: Tích lũy thinking content
                                    thinkingContent += data.content;
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId
                                            ? { ...m, thinking: thinkingContent, isThinking: true }
                                            : m
                                        )
                                    );
                                } else if (data.type === 'result_json' && data.content) {
                                    const text = data.content.message || data.content.final_response || '';
                                    if (text) {
                                        fullContent = text;
                                        setMessages(prev =>
                                            prev.map(m => m.id === assistantId
                                                ? { ...m, content: fullContent, isThinking: false }
                                                : m
                                            )
                                        );
                                    }
                                } else if (data.text) {
                                    // Legacy format
                                    fullContent += data.text;
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId
                                            ? { ...m, content: fullContent, isThinking: false }
                                            : m
                                        )
                                    );
                                }
                            } catch {
                                // Non-JSON line, could be raw text
                                const text = line.slice(6);
                                if (text && text !== '[DONE]') {
                                    fullContent += text;
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId
                                            ? { ...m, content: fullContent, isThinking: false }
                                            : m
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
                        m.id === assistantId
                            ? { ...m, isStreaming: false, isThinking: false, thinking: thinkingContent || undefined }
                            : m
                    )
                );
            }
        } catch (error) {
            if ((error as Error).name === 'AbortError') return;

            console.error('Chat error:', error);
            setMessages(prev =>
                prev.map(m =>
                    m.id === assistantId
                        ? { ...m, content: 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau.', isStreaming: false, isThinking: false }
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
                            className={`max-w-[85%] p-3 rounded-lg relative group text-base ${msg.role === 'user'
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-800 border border-gray-200'
                                }`}
                        >
                            {msg.role === 'assistant' ? (
                                <div className="prose prose-base max-w-none">
                                    {/* Thinking section phía trên câu trả lời */}
                                    <ThinkingSection
                                        thinking={msg.thinking || ''}
                                        isStreaming={!!msg.isThinking}
                                    />
                                    {msg.content && (
                                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                                    )}
                                    {msg.isStreaming && msg.content && <span className="animate-pulse">▊</span>}
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
                {loading && messages[messages.length - 1]?.content === '' && !messages[messages.length - 1]?.isThinking && (
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
            <div className="w-full flex gap-2 items-end">
                <TextArea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            handleSend();
                        }
                    }}
                    placeholder="Nhập câu hỏi... (Enter để gửi)"
                    disabled={loading}
                    autoSize={{ minRows: 1, maxRows: 4 }}
                    className="text-base"
                />
                <Button
                    type="primary"
                    icon={<SendOutlined />}
                    onClick={handleSend}
                    loading={loading}
                    className="flex-shrink-0 bg-blue-600 hover:bg-blue-700 h-9"
                />
            </div>
        </Card>
    );
}
