'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Modal } from 'antd';
import { Html5Qrcode } from 'html5-qrcode';
import { ScanOutlined } from '@ant-design/icons';

interface ScannerModalProps {
    open: boolean;
    onCancel: () => void;
    onScanSuccess: (decodedText: string) => void;
    title?: React.ReactNode;
}

export default function ScannerModal({ open, onCancel, onScanSuccess, title = 'Quét mã QR' }: ScannerModalProps) {
    const scannerRef = useRef<Html5Qrcode | null>(null);
    const [error, setError] = useState<string>('');
    const isScanning = useRef(false);

    useEffect(() => {
        if (open) {
            setError('');
            isScanning.current = true;

            // Allow modal transition to finish
            const timerId = setTimeout(() => {
                if (!isScanning.current) return;
                try {
                    const scanner = new Html5Qrcode('qr-reader');
                    scannerRef.current = scanner;

                    scanner.start(
                        { facingMode: 'environment' },
                        {
                            fps: 10,
                            qrbox: { width: 250, height: 250 }
                        },
                        (decodedText) => {
                            // Only trigger once
                            if (isScanning.current) {
                                isScanning.current = false;
                                if (scannerRef.current) {
                                    scannerRef.current.stop().then(() => {
                                        scannerRef.current?.clear();
                                        onScanSuccess(decodedText);
                                    }).catch(console.error);
                                } else {
                                    onScanSuccess(decodedText);
                                }
                            }
                        },
                        (err) => {
                            // Ignored (continuous scan)
                        }
                    ).catch(err => {
                        console.error("Camera start error", err);
                        setError('Không thể mở Camera. Vui lòng kiểm tra quyền truy cập hoặc thử lại.');
                    });
                } catch (e) {
                    console.error("Scanner init error", e);
                    setError('Lỗi khởi tạo máy quét.');
                }
            }, 300);

            return () => {
                clearTimeout(timerId);
                isScanning.current = false;
                if (scannerRef.current) {
                    const currentScanner = scannerRef.current;
                    if (currentScanner.isScanning) {
                        currentScanner.stop().catch(console.error).finally(() => {
                            currentScanner.clear();
                        });
                    }
                    scannerRef.current = null;
                }
            };
        }
    }, [open, onScanSuccess]);

    return (
        <Modal
            title={
                <span>
                    <ScanOutlined className="mr-2" />
                    {title}
                </span>
            }
            open={open}
            onCancel={() => {
                isScanning.current = false;
                if (scannerRef.current && scannerRef.current.isScanning) {
                    scannerRef.current.stop().catch(console.error).finally(() => {
                        scannerRef.current?.clear();
                        onCancel();
                    });
                } else {
                    onCancel();
                }
            }}
            footer={null}
            destroyOnClose
            centered
        >
            <div className="flex flex-col items-center">
                <div id="qr-reader" className="w-full max-w-sm rounded-lg overflow-hidden border border-gray-200" style={{ minHeight: '300px' }} />
                {error && <p className="text-red-500 mt-4 font-medium">{error}</p>}
                <p className="text-gray-500 mt-4 text-center">
                    Hướng Camera vào mã QR trên Căn cước công dân để quét
                </p>
            </div>
        </Modal>
    );
}
