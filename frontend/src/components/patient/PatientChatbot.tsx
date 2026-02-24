'use client';

import { useState, useRef, useEffect, memo } from 'react';
import { Button, Input, Typography, Avatar, Spin, Tag } from 'antd';
import {
    SendOutlined,
    MedicineBoxOutlined,
    UserOutlined,
    CloseOutlined,
    MessageOutlined,
    AlertOutlined,
    WarningOutlined,
    CalendarOutlined,
    DownOutlined,
    RightOutlined,
    LoadingOutlined,
} from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import BookingForm from './BookingForm';

const { Text } = Typography;

/**
 * Patient Chatbot Component
 * AI Chatbot công khai cho bệnh nhân hỏi đáp
 * 
 * Features:
 * - Lưu lịch sử chat vào localStorage (TTL 1 giờ từ tin nhắn cuối cùng)
 * - Hiển thị quá trình "thinking" của AI phía trên câu trả lời
 */

// ==========================================
// Chat History Persistence (localStorage)
// ==========================================
const CHAT_STORAGE_KEY = 'patient_chat_history';
const CHAT_TTL_MS = 60 * 60 * 1000; // 1 giờ = 3,600,000 ms

interface StoredChat {
    messages: StoredMessage[];
    lastMessageAt: number; // Unix timestamp ms
}

interface StoredMessage {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    thinking?: string;
    timestamp: string; // ISO string (Date không serialize được)
}

/** Lưu messages vào localStorage với timestamp */
function saveChatToStorage(messages: Message[]) {
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
        localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(data));
    } catch {
        // localStorage full hoặc không khả dụng
    }
}

/** Load messages từ localStorage, trả về null nếu hết hạn hoặc không có */
function loadChatFromStorage(): Message[] | null {
    if (typeof window === 'undefined') return null;
    try {
        const raw = localStorage.getItem(CHAT_STORAGE_KEY);
        if (!raw) return null;

        const data: StoredChat = JSON.parse(raw);
        const elapsed = Date.now() - data.lastMessageAt;

        // Hết hạn sau 1 giờ từ tin nhắn cuối
        if (elapsed > CHAT_TTL_MS) {
            localStorage.removeItem(CHAT_STORAGE_KEY);
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
        localStorage.removeItem(CHAT_STORAGE_KEY);
        return null;
    }
}

// ==========================================
// Urgency Configuration
// ==========================================
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

// ==========================================
// Thinking Section Component
// ==========================================

/** Lọc bỏ phần JSON routing, chỉ giữ từ "**Bước 1" trở đi */
function cleanThinkingContent(raw: string): string {
    // Tìm vị trí "**Bước 1" (phần thinking thực sự)
    const match = raw.match(/\*\*Bước 1/);
    if (match && match.index !== undefined) {
        return raw.slice(match.index).trim();
    }
    // Fallback: nếu không có "Bước 1", bỏ phần JSON block (```...```) ở đầu
    const cleaned = raw.replace(/```[\s\S]*?```/g, '').trim();
    return cleaned || raw;
}

function ThinkingSection({ thinking, isStreaming }: { thinking: string; isStreaming: boolean }) {
    const [expanded, setExpanded] = useState(false);
    const displayThinking = thinking ? cleanThinkingContent(thinking) : '';

    if (!displayThinking && !isStreaming) return null;

    // Đang stream thinking → hiện animation
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

    // Đã xong → hiện toggle "Hiện quá trình tư duy"
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
    isThinking?: boolean; // Đang trong giai đoạn thinking
}

interface PatientChatbotProps {
    apiEndpoint?: string;
}

// ==========================================
// Welcome message mặc định
// ==========================================

// ==========================================
// Memoized Message Component to prevent re-renders on input typing
// ==========================================
const MessageItem = memo(({ msg, isLast, activeForm, formDismissed, bookingCompleted, lastFormPayload, onReopenForm, onBookingSubmit, onBookingCancel }: {
    msg: Message;
    isLast: boolean;
    activeForm: any;
    formDismissed: boolean;
    bookingCompleted: boolean;
    lastFormPayload: any;
    onReopenForm: () => void;
    onBookingSubmit: (ref: string) => void;
    onBookingCancel: () => void;
}) => {
    // Skip rendering empty assistant messages (show loading spinner instead handled by parent)
    if (msg.role === 'assistant' && !msg.content && !msg.isThinking && msg.isStreaming) {
        return null;
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
            <div className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <Avatar
                    icon={msg.role === 'user' ? <UserOutlined /> : <MedicineBoxOutlined />}
                    size="large"
                    className={msg.role === 'user' ? 'bg-blue-600' : 'bg-emerald-600'}
                />
                <div
                    className={`max-w-[85%] p-4 rounded-2xl text-base shadow-sm ${msg.role === 'user'
                        ? 'bg-blue-600 text-white rounded-br-none'
                        : 'bg-white text-gray-800 rounded-bl-none border border-gray-100'
                        }`}
                >
                    {msg.role === 'assistant' ? (
                        <div className="prose prose-base max-w-none">
                            <ThinkingSection
                                thinking={msg.thinking || ''}
                                isStreaming={!!msg.isThinking}
                            />
                            <UrgencyBadge content={msg.content} />
                            {msg.content && (
                                <ReactMarkdown>{cleanUrgencyTags(msg.content)}</ReactMarkdown>
                            )}
                            {msg.isStreaming && msg.content && <span className="animate-pulse inline-block ml-1">▊</span>}
                        </div>
                    ) : (
                        <span className="whitespace-pre-wrap">{msg.content}</span>
                    )}
                </div>
            </div>

            {/* Booking Form */}
            {msg.role === 'assistant' && isLast && activeForm?.action === 'open_booking_form' && (
                <div style={{ marginTop: '12px', paddingLeft: '52px' }}>
                    <BookingForm
                        department={activeForm.payload.department || ''}
                        date={activeForm.payload.date || ''}
                        suggestedTimes={activeForm.payload.suggested_times || []}
                        patientNote={activeForm.payload.patient_note || ''}
                        onSubmitted={onBookingSubmit}
                        onCancel={onBookingCancel}
                    />
                </div>
            )}

            {/* Reopen Form Button */}
            {msg.role === 'assistant' && isLast && formDismissed && !bookingCompleted && !activeForm && lastFormPayload && (
                <div style={{ marginTop: '12px', paddingLeft: '52px' }}>
                    <button
                        onClick={onReopenForm}
                        style={{
                            padding: '8px 20px',
                            backgroundColor: '#1677ff',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontSize: '14px',
                            fontWeight: 500,
                            display: 'flex',
                            alignItems: 'center',
                            gap: '8px',
                            boxShadow: '0 2px 0 rgba(0,0,0,0.04)'
                        }}
                    >
                        <CalendarOutlined /> Mở lại form đặt lịch
                    </button>
                </div>
            )}
        </div>
    );
});

const MessageList = memo(({ messages, loading, activeForm, formDismissed, bookingCompleted, lastFormPayload, onReopenForm, onBookingSubmit, onBookingCancel, messagesEndRef }: any) => {
    return (
        <div className="flex-1 overflow-y-auto p-5 space-y-5 bg-gray-50 scroll-smooth">
            {messages.map((msg: Message, msgIndex: number) => (
                <MessageItem
                    key={msg.id}
                    msg={msg}
                    isLast={msgIndex === messages.length - 1}
                    activeForm={activeForm}
                    formDismissed={formDismissed}
                    bookingCompleted={bookingCompleted}
                    lastFormPayload={lastFormPayload}
                    onReopenForm={onReopenForm}
                    onBookingSubmit={onBookingSubmit}
                    onBookingCancel={onBookingCancel}
                />
            ))}
            {loading && messages[messages.length - 1]?.content === '' && !messages[messages.length - 1]?.isThinking && (
                <div className="flex gap-3">
                    <Avatar icon={<MedicineBoxOutlined />} className="bg-emerald-600" size="large" />
                    <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 rounded-bl-none">
                        <Spin size="default" />
                    </div>
                </div>
            )}
            <div ref={messagesEndRef} />
        </div>
    );
});


// ==========================================
// Welcome message mặc định
// ==========================================
const WELCOME_MESSAGE: Message = {
    id: '1',
    role: 'assistant',
    content: 'Xin chào! Tôi là trợ lý AI của Bệnh viện. Tôi có thể giúp bạn:\n\n• Tìm hiểu về dịch vụ y tế\n• Hướng dẫn đặt lịch khám\n• Giải đáp thắc mắc sức khỏe cơ bản\n• Cung cấp thông tin liên hệ\n\nBạn cần hỗ trợ gì ạ?',
    timestamp: new Date(),
};

export default function PatientChatbot({ apiEndpoint = '/chat/stream/' }: PatientChatbotProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [messages, setMessages] = useState<Message[]>(() => {
        // Khởi tạo từ localStorage nếu còn hạn, fallback về welcome message
        const stored = loadChatFromStorage();
        return stored && stored.length > 0 ? stored : [WELCOME_MESSAGE];
    });
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const [isComposing, setIsComposing] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const abortControllerRef = useRef<AbortController | null>(null);
    const inputRef = useRef<any>(null); // Ref to focus input


    // UI Action state: khi Agent gọi open_booking_form → hiện form đặt lịch
    const [activeForm, setActiveForm] = useState<{
        action: string;
        payload: Record<string, any>;
    } | null>(null);

    // Trạng thái form: đã đóng (dismiss) hay đã hoàn tất booking
    const [formDismissed, setFormDismissed] = useState(false);
    const [bookingCompleted, setBookingCompleted] = useState(false);
    // Lưu lại payload để reopen form
    const [lastFormPayload, setLastFormPayload] = useState<{
        action: string;
        payload: Record<string, any>;
    } | null>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    useEffect(() => {
        const hasStreaming = messages.some(m => m.isStreaming);
        if (!hasStreaming) {
            saveChatToStorage(messages);
        }
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
            { id: assistantId, role: 'assistant', content: '', timestamp: new Date(), isStreaming: true, isThinking: true },
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

            // Focus input after sending
            setTimeout(() => inputRef.current?.focus(), 100);

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

                                // Backend SSE format:
                                // {"type": "thinking", "content": "..."} ← Phase 1: thinking tokens
                                // {"type": "result_json", "content": {"message": "...", "final_response": "..."}}
                                // {"type": "token", "content": "text"} 
                                // {"type": "done", "full_response": "..."}
                                // {"type": "status", "message": "..."} - Status (ignore)

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
                                    // Phase 2: Extract message from nested content object
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
                                    // FALLBACK: Check __ui_action__ embedded in result_json
                                    if (data.content.__ui_action__) {
                                        const uiData = data.content.__ui_action__;
                                        const actionPayload = { ...uiData };
                                        delete actionPayload.__ui_action__;
                                        const actionName = uiData.__ui_action__ || 'open_booking_form';
                                        setActiveForm({ action: actionName, payload: actionPayload });
                                        setLastFormPayload({ action: actionName, payload: actionPayload });
                                        setFormDismissed(false);
                                        setBookingCompleted(false);
                                    }
                                } else if (data.type === 'token' && typeof data.content === 'string') {
                                    fullContent += data.content;
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId
                                            ? { ...m, content: fullContent, isThinking: false }
                                            : m
                                        )
                                    );
                                } else if (data.type === 'done' && data.full_response) {
                                    fullContent = data.full_response;
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId
                                            ? { ...m, content: fullContent, isThinking: false }
                                            : m
                                        )
                                    );
                                } else if (data.type === 'ui_action' && data.action) {
                                    // ==========================================
                                    // UI ACTION: Agent yêu cầu hiển thị UI component
                                    // vd: open_booking_form → render <BookingForm />
                                    // ==========================================
                                    const formData = {
                                        action: data.action,
                                        payload: data.payload || {},
                                    };
                                    setActiveForm(formData);
                                    setLastFormPayload(formData);
                                    setFormDismissed(false);
                                    setBookingCompleted(false);
                                    // Thêm message cho user biết form đã mở
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId
                                            ? { ...m, content: 'Mời bạn điền thông tin đặt lịch bên dưới:', isThinking: false, isStreaming: false }
                                            : m
                                        )
                                    );
                                }
                                // Ignore status messages (type: "status")
                            } catch {
                                // Handle plain text (non-JSON)
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
                // Stream xong: set thinking content cuối cùng, tắt streaming
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, isStreaming: false, isThinking: false, thinking: thinkingContent || undefined }
                        : m
                ));
            }
        } catch (error) {
            if ((error as Error).name === 'AbortError') return;
            console.error('Chat error:', error);
            setMessages(prev =>
                prev.map(m =>
                    m.id === assistantId
                        ? { ...m, content: 'Xin lỗi, đã có lỗi xảy ra. Vui lòng thử lại sau hoặc gọi hotline: 1900-xxxx', isStreaming: false, isThinking: false }
                        : m
                )
            );
        } finally {
            setLoading(false);
        }
    };

    // ==========================================
    // Xử lý khi form đặt lịch submit thành công
    // Gửi confirmation message cho Agent tiếp tục hội thoại
    // ==========================================
    const handleBookingConfirmed = async (bookingRef: string) => {
        setActiveForm(null);
        setBookingCompleted(true);
        setFormDismissed(false);

        // Thêm message xác nhận từ hệ thống
        const confirmMsg: Message = {
            id: Date.now().toString(),
            role: 'user',
            content: `[BOOKING_CONFIRMED] Mã đặt lịch: ${bookingRef}`,
            timestamp: new Date(),
        };
        setMessages(prev => [...prev, confirmMsg]);

        // Gửi message cho Agent để tiếp tục hội thoại
        setLoading(true);
        const assistantId = (Date.now() + 1).toString();
        setMessages(prev => [
            ...prev,
            { id: assistantId, role: 'assistant', content: '', timestamp: new Date(), isStreaming: true, isThinking: true },
        ]);

        try {
            abortControllerRef.current?.abort();
            abortControllerRef.current = new AbortController();

            const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

            const response = await fetch(`${baseUrl}${apiEndpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: `[BOOKING_CONFIRMED] Bệnh nhân đã đặt lịch thành công. Mã đặt lịch: ${bookingRef}. Hãy xác nhận lại cho bệnh nhân.`
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
                                } else if (data.type === 'token' && typeof data.content === 'string') {
                                    fullContent += data.content;
                                    setMessages(prev =>
                                        prev.map(m => m.id === assistantId
                                            ? { ...m, content: fullContent, isThinking: false }
                                            : m
                                        )
                                    );
                                }
                            } catch {
                                // ignore parse errors
                            }
                        }
                    }
                }
                setMessages(prev => prev.map(m =>
                    m.id === assistantId
                        ? { ...m, isStreaming: false, isThinking: false, thinking: thinkingContent || undefined }
                        : m
                ));
            }
        } catch (error) {
            if ((error as Error).name === 'AbortError') return;
            setMessages(prev =>
                prev.map(m =>
                    m.id === assistantId
                        ? { ...m, content: `Đặt lịch thành công! Mã đặt lịch: ${bookingRef}. Vui lòng đến trước 15 phút.`, isStreaming: false, isThinking: false }
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
                <div className="fixed bottom-6 right-6 w-[500px] h-[700px] max-h-[85vh] bg-white rounded-2xl shadow-2xl flex flex-col z-50 overflow-hidden border border-gray-200 font-sans animate-fade-in-up">
                    {/* Header */}
                    <div className="bg-gradient-to-r from-blue-600 to-blue-700 p-5 flex items-center justify-between text-white shadow-md z-10">
                        <div className="flex items-center gap-4">
                            <div className="relative">
                                <Avatar icon={<MedicineBoxOutlined />} size="large" className="bg-white/20" />
                                <span className="absolute bottom-0 right-0 w-3 h-3 bg-green-400 border-2 border-blue-600 rounded-full"></span>
                            </div>
                            <div>
                                <Text strong className="text-white text-lg block">Trợ lý AI Bệnh viện</Text>
                                <Text className="text-blue-100 text-sm">Luôn sẵn sàng hỗ trợ</Text>
                            </div>
                        </div>
                        <Button
                            type="text"
                            icon={<CloseOutlined className="text-white text-xl" />}
                            onClick={() => setIsOpen(false)}
                            className="hover:bg-white/20 rounded-full w-10 h-10 flex items-center justify-center"
                        />
                    </div>

                    {/* Messages (Memoized) */}
                    <MessageList
                        messages={messages}
                        loading={loading}
                        activeForm={activeForm}
                        formDismissed={formDismissed}
                        bookingCompleted={bookingCompleted}
                        lastFormPayload={lastFormPayload}
                        onReopenForm={() => {
                            if (lastFormPayload) {
                                setActiveForm(lastFormPayload);
                                setFormDismissed(false);
                            }
                        }}
                        onBookingSubmit={handleBookingConfirmed}
                        onBookingCancel={() => {
                            setActiveForm(null);
                            setFormDismissed(true);
                        }}
                        messagesEndRef={messagesEndRef}
                    />

                    {/* Input */}
                    <div className="p-4 bg-white border-t border-gray-100">
                        <div className="flex gap-3 items-end bg-gray-50 p-2 rounded-3xl border border-gray-200 focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100 transition-all">
                            <Input.TextArea
                                ref={inputRef}
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
                                autoSize={{ minRows: 1, maxRows: 4 }}
                                className="text-base bg-transparent border-none shadow-none focus:shadow-none !px-3 !py-2 resize-none"
                                style={{ minHeight: '44px' }}
                            />
                            <Button
                                type="primary"
                                shape="circle"
                                size="large"
                                icon={<SendOutlined />}
                                onClick={handleSend}
                                loading={loading}
                                className="flex-shrink-0 shadow-lg mb-1 mr-1 bg-blue-600 hover:bg-blue-700"
                            />
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
