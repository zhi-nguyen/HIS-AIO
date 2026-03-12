'use client';

import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import { TextStyle } from '@tiptap/extension-text-style';
import Color from '@tiptap/extension-color';
import Highlight from '@tiptap/extension-highlight';
import Placeholder from '@tiptap/extension-placeholder';
import { useEffect, useRef, useCallback } from 'react';
import {
    BoldOutlined, ItalicOutlined, UnderlineOutlined,
    OrderedListOutlined, UnorderedListOutlined, ClearOutlined,
} from '@ant-design/icons';
import { Button, Tooltip, Popover } from 'antd';

/* ── Bảng màu dùng cho color picker ── */
const COLORS = [
    '#000000', '#434343', '#666666', '#999999', '#b7b7b7', '#cccccc', '#d9d9d9', '#ffffff',
    '#e60000', '#ff9900', '#ffff00', '#008a00', '#0066cc', '#9933ff',
    '#facccc', '#ffebcc', '#ffffcc', '#cce8cc', '#cce0f5', '#ebd6ff',
];

const BG_COLORS = [
    '#ffffff', '#fef3cd', '#d4edda', '#cce5ff', '#f8d7da',
    '#fff3cd', '#d1ecf1', '#e2e3e5', '#f5c6cb',
];

/* ── Toolbar Button nhỏ gọn ── */
function TBBtn({ active, onClick, icon, title }: {
    active?: boolean; onClick: () => void; icon: React.ReactNode; title: string;
}) {
    return (
        <Tooltip title={title}>
            <button
                type="button"
                onMouseDown={(e) => { e.preventDefault(); onClick(); }}
                style={{
                    display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                    width: 28, height: 28, border: '1px solid transparent', borderRadius: 4,
                    cursor: 'pointer', fontSize: 14,
                    background: active ? '#e6f4ff' : 'transparent',
                    color: active ? '#1677ff' : '#595959',
                }}
            >
                {icon}
            </button>
        </Tooltip>
    );
}

/* ── Color Picker Grid ── */
function ColorGrid({ colors, onPick }: { colors: string[]; onPick: (c: string) => void }) {
    return (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3, maxWidth: 160 }}>
            {colors.map((c) => (
                <button
                    key={c}
                    type="button"
                    onMouseDown={(e) => { e.preventDefault(); onPick(c); }}
                    style={{
                        width: 18, height: 18, borderRadius: 3, border: '1px solid #d9d9d9',
                        background: c, cursor: 'pointer',
                    }}
                />
            ))}
        </div>
    );
}

/* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   RichTextEditor — Thay thế Quill, xuất HTML chuẩn, tiếng Việt OK
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
interface RichTextEditorProps {
    value: string;
    onChange: (html: string) => void;
    placeholder?: string;
    style?: React.CSSProperties;
}

export default function RichTextEditor({ value, onChange, placeholder, style }: RichTextEditorProps) {
    const isInternalUpdate = useRef(false);

    const editor = useEditor({
        immediatelyRender: false,
        extensions: [
            StarterKit.configure({
                bulletList: { keepMarks: true },
                orderedList: { keepMarks: true },
            }),
            Underline,
            TextStyle,
            Color,
            Highlight.configure({ multicolor: true }),
            Placeholder.configure({ placeholder: placeholder || '' }),
        ],
        content: value || '',
        onUpdate: ({ editor: ed }) => {
            isInternalUpdate.current = true;
            onChange(ed.getHTML());
        },
    });

    /* Sync external value → editor (chỉ khi thay đổi từ bên ngoài) */
    useEffect(() => {
        if (isInternalUpdate.current) {
            isInternalUpdate.current = false;
            return;
        }
        if (editor && value !== editor.getHTML()) {
            editor.commands.setContent(value || '');
        }
    }, [value, editor]);

    const setColor = useCallback((color: string) => {
        editor?.chain().focus().setColor(color).run();
    }, [editor]);

    const setBg = useCallback((color: string) => {
        editor?.chain().focus().toggleHighlight({ color }).run();
    }, [editor]);

    if (!editor) return null;

    return (
        <div style={{
            border: '1px solid #d9d9d9', borderRadius: 6, overflow: 'hidden',
            background: '#fff', ...style,
        }}>
            {/* ── Toolbar ── */}
            <div style={{
                display: 'flex', alignItems: 'center', gap: 2, padding: '4px 8px',
                borderBottom: '1px solid #f0f0f0', background: '#fafafa', flexWrap: 'wrap',
            }}>
                <TBBtn
                    title="In đậm" icon={<BoldOutlined />}
                    active={editor.isActive('bold')}
                    onClick={() => editor.chain().focus().toggleBold().run()}
                />
                <TBBtn
                    title="In nghiêng" icon={<ItalicOutlined />}
                    active={editor.isActive('italic')}
                    onClick={() => editor.chain().focus().toggleItalic().run()}
                />
                <TBBtn
                    title="Gạch chân" icon={<UnderlineOutlined />}
                    active={editor.isActive('underline')}
                    onClick={() => editor.chain().focus().toggleUnderline().run()}
                />

                <div style={{ width: 1, height: 18, background: '#e5e7eb', margin: '0 4px' }} />

                {/* Color picker */}
                <Popover
                    content={<ColorGrid colors={COLORS} onPick={setColor} />}
                    title="Màu chữ" trigger="click" placement="bottom"
                >
                    <Tooltip title="Màu chữ">
                        <button type="button" style={{
                            width: 28, height: 28, border: '1px solid transparent', borderRadius: 4,
                            cursor: 'pointer', background: 'transparent', display: 'inline-flex',
                            alignItems: 'center', justifyContent: 'center', fontSize: 14, fontWeight: 700,
                            color: '#595959', position: 'relative',
                        }}>
                            A
                            <span style={{
                                position: 'absolute', bottom: 2, left: 4, right: 4, height: 3,
                                background: editor.getAttributes('textStyle').color || '#000', borderRadius: 1,
                            }} />
                        </button>
                    </Tooltip>
                </Popover>

                {/* Background picker */}
                <Popover
                    content={<ColorGrid colors={BG_COLORS} onPick={setBg} />}
                    title="Nền chữ" trigger="click" placement="bottom"
                >
                    <Tooltip title="Tô nền">
                        <button type="button" style={{
                            width: 28, height: 28, border: '1px solid transparent', borderRadius: 4,
                            cursor: 'pointer', background: 'transparent', display: 'inline-flex',
                            alignItems: 'center', justifyContent: 'center', fontSize: 13,
                            color: '#595959',
                        }}>
                            🖍
                        </button>
                    </Tooltip>
                </Popover>

                <div style={{ width: 1, height: 18, background: '#e5e7eb', margin: '0 4px' }} />

                <TBBtn
                    title="Danh sách số" icon={<OrderedListOutlined />}
                    active={editor.isActive('orderedList')}
                    onClick={() => editor.chain().focus().toggleOrderedList().run()}
                />
                <TBBtn
                    title="Danh sách gạch" icon={<UnorderedListOutlined />}
                    active={editor.isActive('bulletList')}
                    onClick={() => editor.chain().focus().toggleBulletList().run()}
                />

                <div style={{ width: 1, height: 18, background: '#e5e7eb', margin: '0 4px' }} />

                <TBBtn
                    title="Xoá định dạng" icon={<ClearOutlined />}
                    onClick={() => editor.chain().focus().unsetAllMarks().clearNodes().run()}
                />
            </div>

            {/* ── Editor Content ── */}
            <EditorContent
                editor={editor}
                style={{ padding: '8px 12px', fontSize: 13, minHeight: 120, lineHeight: 1.7 }}
            />

            {/* ── Tiptap base styles ── */}
            <style>{`
                .tiptap { outline: none; }
                .tiptap p { margin: 0; }
                .tiptap ul, .tiptap ol { padding-left: 1.5em; margin: 4px 0; }
                .tiptap li { margin: 0; }
                .tiptap p.is-editor-empty:first-child::before {
                    color: #adb5bd;
                    content: attr(data-placeholder);
                    float: left;
                    height: 0;
                    pointer-events: none;
                }
            `}</style>
        </div>
    );
}
