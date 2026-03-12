'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import { Input, Button, Space, Typography, Avatar, Spin, Tooltip } from 'antd';
const { TextArea } = Input;
import {
    SendOutlined,
    MedicineBoxOutlined,
    UserOutlined,
    StopOutlined,
    CopyOutlined,
    CheckOutlined,
    DownOutlined,
    RightOutlined,
    LoadingOutlined,
    ClearOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';

const { Text } = Typography;

/**
 * AI Chat Component với SSE Streaming — dùng bên trong Drawer toggle
 *
 * Features:
 * - Lưu lịch sử chat vào localStorage theo visitId (TTL 8 giờ)
 * - Auto-phân tích khi mở lần đầu (autoAnalyze + initialContext)
 * - Hiển thị quá trình "thinking" của AI
 */

// ==========================================
// Chat History Persistence (localStorage)
// ==========================================
const CHAT_STORAGE_PREFIX = 'ai_chat_history_';
const CHAT_TTL_MS = 8 * 60 * 60 * 1000; // 8 giờ

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

// ==========================================
// Interfaces
// ==========================================
interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    isStreaming?: boolean;
}

export interface AIChatProps {
    visitId: string;
    /** Context tổng hợp từ clinical page (bệnh sử, XN, CĐHA...) */
    initialContext?: string;
    /** Nếu true và chưa có lịch sử chat: tự gửi initialContext khi mở */
    autoAnalyze?: boolean;
    patientContext?: string;
}

export default function AIChat({ visitId, initialContext, autoAnalyze, patientContext }: AIChatProps) {
    const storageKey = `${CHAT_STORAGE_PREFIX}${visitId}`;

    const [messages, setMessages] = useState<Message[]>(() => {
        const stored = loadChatFromStorage(storageKey);
        return stored && stored.length > 0 ? stored : [];
    });
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [copied, setCopied] = useState<string | null>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const autoAnalyzeSentRef = useRef(false);

    // Auto scroll to bottom
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Lưu messages vào localStorage khi thay đổi (bỏ qua khi đang streaming)
    useEffect(() => {
        const hasStreaming = messages.some(m => m.isStreaming);
        if (!hasStreaming && messages.length > 0) {
            saveChatToStorage(storageKey, messages);
        }
    }, [messages, storageKey]);

    // Core send function
    const sendMessage = useCallback(async (text: string) => {
        if (!text.trim() || loading) return;

        const userMessage: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: text,
            timestamp: new Date(),
        };

        setMessages(prev => [...prev, userMessage]);
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
            const token = localStorage.getItem('his_access_token');

            const response = await fetch(`${baseUrl}/chat/stream/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({
                    visit_id: visitId,
                    message: text,
                    context: patientContext || initialContext,
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
                                if (data.type === 'result_json' && data.content) {
                                    const t = data.content.message || data.content.final_response || '';
                                    if (t) {
                                        fullContent = t;
                                        setMessages(prev => prev.map(m => m.id === assistantId
                                            ? { ...m, content: fullContent } : m));
                                    }
                                    
                                    // Phát event cập nhật SuggestionsDrawer
                                    if (data.content.tests || (data.content.icds && data.content.icds.length > 0)) {
                                        const event = new CustomEvent('ai_suggestions_update', {
                                            detail: {
                                                tests: data.content.tests || '',
                                                icds: data.content.icds || [],
                                            }
                                        });
                                        window.dispatchEvent(event);
                                    }
                                } else if (data.text) {
                                    fullContent += data.text;
                                    setMessages(prev => prev.map(m => m.id === assistantId
                                        ? { ...m, content: fullContent } : m));
                                }
                            } catch {
                                const t = line.slice(6);
                                if (t && t !== '[DONE]') {
                                    fullContent += t;
                                    setMessages(prev => prev.map(m => m.id === assistantId
                                        ? { ...m, content: fullContent } : m));
                                }
                            }
                        }
                    }
                }

                setMessages(prev => prev.map(m => m.id === assistantId
                    ? { ...m, isStreaming: false } : m));
            }
        } catch (error) {
            if ((error as Error).name === 'AbortError') return;
            setMessages(prev => prev.map(m => m.id === assistantId
                ? { ...m, content: 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau.', isStreaming: false } : m));
        } finally {
            setLoading(false);
        }
    }, [visitId, patientContext, initialContext, loading]);

    // Auto-analyze khi mount (mở drawer lần đầu chưa có lịch sử)
    useEffect(() => {
        if (!autoAnalyze || autoAnalyzeSentRef.current) return;
        if (messages.length > 0) return; // Đã có lịch sử — không gửi lại
        if (!initialContext) return;
        autoAnalyzeSentRef.current = true;
        sendMessage(initialContext);
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [autoAnalyze, initialContext]);

    const handleSend = () => {
        sendMessage(input);
        setInput('');
    };

    const handleCopy = useCallback((text: string, id: string) => {
        navigator.clipboard.writeText(text);
        setCopied(id);
        setTimeout(() => setCopied(null), 2000);
    }, []);

    const handleStop = () => {
        abortControllerRef.current?.abort();
        setLoading(false);
    };

    const handleClear = () => {
        if (loading) handleStop();
        setMessages([]);
        localStorage.removeItem(storageKey);
        autoAnalyzeSentRef.current = false;
    };

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
            {/* Toolbar */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, paddingBottom: 8, borderBottom: '1px solid #f0f0f0', marginBottom: 8 }}>
                {loading && (
                    <Button size="small" danger icon={<StopOutlined />} onClick={handleStop}>Dừng</Button>
                )}
                <Tooltip title="Xóa lịch sử chat">
                    <Button size="small" icon={<ClearOutlined />} onClick={handleClear} disabled={messages.length === 0 && !loading}>
                        Xóa chat
                    </Button>
                </Tooltip>
            </div>

            {/* Messages */}
            <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 12, paddingRight: 4 }}>
                {messages.length === 0 && !loading && (
                    <div style={{ textAlign: 'center', color: '#9ca3af', fontSize: 13, padding: '40px 16px' }}>
                        <MedicineBoxOutlined style={{ fontSize: 32, color: '#d1d5db', marginBottom: 8, display: 'block' }} />
                        AI sẽ tự phân tích toàn bộ thông tin lâm sàng khi bạn mở trợ lý lần đầu.
                    </div>
                )}

                {messages.map((msg) => (
                    <div key={msg.id} style={{ display: 'flex', gap: 8, flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
                        <Avatar
                            icon={msg.role === 'user' ? <UserOutlined /> : <MedicineBoxOutlined />}
                            style={{ backgroundColor: msg.role === 'user' ? '#3b82f6' : '#10b981', flexShrink: 0 }}
                            size="small"
                        />
                        <div style={{
                            maxWidth: '85%', padding: '10px 12px', borderRadius: 10, position: 'relative',
                            backgroundColor: msg.role === 'user' ? '#2563eb' : '#f3f4f6',
                            color: msg.role === 'user' ? '#fff' : '#1f2937',
                            border: msg.role === 'assistant' ? '1px solid #e5e7eb' : 'none',
                        }} className="group">
                            {msg.role === 'assistant' ? (
                                <div className="prose prose-sm max-w-none" style={{ fontSize: 13 }}>
                                    {msg.isStreaming && !msg.content && (
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6b7280' }}>
                                            <LoadingOutlined spin />
                                            <span>Đang tạo phản hồi...</span>
                                        </div>
                                    )}
                                    {msg.content && <ReactMarkdown>{msg.content}</ReactMarkdown>}
                                    {msg.isStreaming && msg.content && <span className="animate-pulse">▊</span>}
                                </div>
                            ) : (
                                <Text style={{ color: '#fff', fontSize: 13 }}>{msg.content}</Text>
                            )}

                            {msg.role === 'assistant' && msg.content && !msg.isStreaming && (
                                <Tooltip title={copied === msg.id ? 'Đã sao chép!' : 'Sao chép'}>
                                    <Button
                                        type="text" size="small"
                                        icon={copied === msg.id ? <CheckOutlined /> : <CopyOutlined />}
                                        style={{ position: 'absolute', top: 4, right: 4, opacity: 0 }}
                                        className="group-hover:!opacity-100 transition-opacity"
                                        onClick={() => handleCopy(msg.content, msg.id)}
                                    />
                                </Tooltip>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end', paddingTop: 8, borderTop: '1px solid #f0f0f0', marginTop: 8 }}>
                <TextArea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
                    }}
                    placeholder="Nhập câu hỏi... (Enter để gửi, Shift+Enter xuống dòng)"
                    disabled={loading}
                    autoSize={{ minRows: 1, maxRows: 5 }}
                    style={{ fontSize: 13 }}
                />
                <Button
                    type="primary" icon={<SendOutlined />}
                    onClick={handleSend} loading={loading}
                    style={{ flexShrink: 0, height: 36, backgroundColor: '#2563eb' }}
                />
            </div>
        </div>
    );
}
