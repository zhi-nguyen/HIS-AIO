'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Mobile Scanner Page — /scanner
 * 
 * Public page (no auth required) for pairing a phone with a PC workstation.
 * Flow:
 *   1. Enter/scan station ID → WebSocket connection
 *   2. Continuous camera scanning with html5-qrcode
 *   3. On scan: send data via WebSocket, show toast, debounce 2s
 *   4. On ACK from PC: vibrate phone
 */

// ============================================================
// Types
// ============================================================

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface ScanLog {
    content: string;
    timestamp: Date;
    acked: boolean;
}

// ============================================================
// Component
// ============================================================

export default function ScannerPage() {
    const [stationId, setStationId] = useState('');
    const [pairedStationId, setPairedStationId] = useState<string | null>(null);
    const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected');
    const [scanLogs, setScanLogs] = useState<ScanLog[]>([]);
    const [isScannerActive, setIsScannerActive] = useState(false);
    const [lastError, setLastError] = useState<string | null>(null);

    const wsRef = useRef<WebSocket | null>(null);
    const scannerRef = useRef<{ stop: () => Promise<void> } | null>(null);
    const debounceRef = useRef(false);
    const scannerContainerRef = useRef<string>('qr-reader');

    const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

    // ============================================================
    // WebSocket Connection
    // ============================================================

    const connectToStation = useCallback((sid: string) => {
        if (wsRef.current) {
            wsRef.current.close();
        }

        setConnectionStatus('connecting');
        setLastError(null);

        const url = `${WS_BASE}/ws/scanner/${sid}/`;
        const ws = new WebSocket(url);
        wsRef.current = ws;

        ws.onopen = () => {
            setConnectionStatus('connected');
            setPairedStationId(sid);
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                if (data.type === 'ack') {
                    // PC acknowledged — vibrate!
                    if (navigator.vibrate) {
                        navigator.vibrate(200);
                    }
                    // Update last log as acked
                    setScanLogs((prev) => {
                        if (prev.length === 0) return prev;
                        const updated = [...prev];
                        updated[0] = { ...updated[0], acked: true };
                        return updated;
                    });
                }
            } catch {
                // Ignore
            }
        };

        ws.onclose = () => {
            setConnectionStatus('disconnected');
            wsRef.current = null;
        };

        ws.onerror = () => {
            setConnectionStatus('error');
            setLastError('Không thể kết nối. Kiểm tra lại mã trạm và mạng.');
        };
    }, [WS_BASE]);

    const disconnect = useCallback(async () => {
        // Stop scanner
        if (scannerRef.current) {
            try {
                await scannerRef.current.stop();
            } catch { /* ignore */ }
            scannerRef.current = null;
            setIsScannerActive(false);
        }

        // Close WebSocket
        if (wsRef.current) {
            wsRef.current.close(1000);
            wsRef.current = null;
        }

        setConnectionStatus('disconnected');
        setPairedStationId(null);
        setScanLogs([]);
    }, []);

    // ============================================================
    // QR Scanner (html5-qrcode)
    // ============================================================

    const startScanner = useCallback(async () => {
        if (isScannerActive) return;

        try {
            // Dynamic import to avoid SSR issues
            const { Html5Qrcode } = await import('html5-qrcode');

            const scanner = new Html5Qrcode(scannerContainerRef.current);
            scannerRef.current = scanner;

            await scanner.start(
                { facingMode: 'environment' }, // Back camera
                {
                    fps: 10,
                    qrbox: { width: 250, height: 250 },
                    aspectRatio: 1.0,
                },
                // ---- onScanSuccess ----
                (decodedText) => {
                    // Debounce: prevent same code scanned multiple times
                    if (debounceRef.current) return;
                    debounceRef.current = true;

                    // Send via WebSocket
                    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                        wsRef.current.send(JSON.stringify({
                            type: 'scan',
                            content: decodedText,
                        }));

                        // Add to log
                        setScanLogs((prev) => [
                            { content: decodedText, timestamp: new Date(), acked: false },
                            ...prev.slice(0, 19), // Keep last 20
                        ]);
                    }

                    // Release debounce after 2 seconds
                    setTimeout(() => {
                        debounceRef.current = false;
                    }, 2000);
                },
                // ---- onScanFailure ----
                () => { /* Scanner continuously tries, ignore failures */ }
            );

            setIsScannerActive(true);
        } catch (err) {
            setLastError(`Lỗi camera: ${err instanceof Error ? err.message : 'Không thể truy cập camera'}`);
        }
    }, [isScannerActive]);

    // Auto-start scanner when connected
    useEffect(() => {
        if (connectionStatus === 'connected' && !isScannerActive) {
            // Small delay for DOM to be ready
            const timer = setTimeout(startScanner, 500);
            return () => clearTimeout(timer);
        }
    }, [connectionStatus, isScannerActive, startScanner]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (scannerRef.current) {
                scannerRef.current.stop().catch(() => { });
            }
            if (wsRef.current) {
                wsRef.current.close(1000);
            }
        };
    }, []);

    // ============================================================
    // Handle pair form
    // ============================================================

    const handlePair = (e: React.FormEvent) => {
        e.preventDefault();
        const sid = stationId.trim().toUpperCase();
        if (sid) {
            connectToStation(sid);
        }
    };

    // ============================================================
    // Render
    // ============================================================

    // Status color
    const statusColor = {
        disconnected: '#999',
        connecting: '#faad14',
        connected: '#52c41a',
        error: '#ff4d4f',
    }[connectionStatus];

    const statusText = {
        disconnected: 'Chưa kết nối',
        connecting: 'Đang kết nối...',
        connected: `Đã kết nối: ${pairedStationId}`,
        error: 'Lỗi kết nối',
    }[connectionStatus];

    return (
        <div style={{
            minHeight: '100vh',
            background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
            color: '#f1f5f9',
            fontFamily: "'Inter', -apple-system, sans-serif",
        }}>
            {/* Header */}
            <div style={{
                padding: '16px 20px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid rgba(255,255,255,0.1)',
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: 24 }}>📷</span>
                    <span style={{ fontWeight: 700, fontSize: 18 }}>HIS Scanner</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <div style={{
                        width: 10,
                        height: 10,
                        borderRadius: '50%',
                        background: statusColor,
                        boxShadow: connectionStatus === 'connected' ? `0 0 8px ${statusColor}` : 'none',
                    }} />
                    <span style={{ fontSize: 12, color: '#94a3b8' }}>{statusText}</span>
                </div>
            </div>

            {/* Main Content */}
            <div style={{ padding: '20px' }}>

                {/* ---- PAIRING SCREEN ---- */}
                {!pairedStationId && (
                    <div style={{
                        maxWidth: 400,
                        margin: '40px auto',
                        textAlign: 'center',
                    }}>
                        <div style={{ fontSize: 64, marginBottom: 16 }}>🔗</div>
                        <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
                            Ghép đôi với máy tính
                        </h2>
                        <p style={{ color: '#94a3b8', marginBottom: 24, fontSize: 14 }}>
                            Nhập mã trạm hiển thị trên màn hình máy tính tại quầy tiếp đón
                        </p>

                        <form onSubmit={handlePair} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                            <input
                                type="text"
                                value={stationId}
                                onChange={(e) => setStationId(e.target.value)}
                                placeholder="VD: QUAY_TIEP_DON_01"
                                autoFocus
                                style={{
                                    padding: '14px 16px',
                                    borderRadius: 12,
                                    border: '2px solid rgba(255,255,255,0.15)',
                                    background: 'rgba(255,255,255,0.05)',
                                    color: '#f1f5f9',
                                    fontSize: 16,
                                    textAlign: 'center',
                                    textTransform: 'uppercase',
                                    letterSpacing: 2,
                                    outline: 'none',
                                }}
                            />
                            <button
                                type="submit"
                                disabled={!stationId.trim() || connectionStatus === 'connecting'}
                                style={{
                                    padding: '14px',
                                    borderRadius: 12,
                                    border: 'none',
                                    background: stationId.trim() ? 'linear-gradient(135deg, #3b82f6, #2563eb)' : '#334155',
                                    color: '#fff',
                                    fontSize: 16,
                                    fontWeight: 600,
                                    cursor: stationId.trim() ? 'pointer' : 'default',
                                    opacity: stationId.trim() ? 1 : 0.5,
                                }}
                            >
                                {connectionStatus === 'connecting' ? '⏳ Đang kết nối...' : '🔗 Ghép đôi'}
                            </button>
                        </form>

                        {lastError && (
                            <div style={{
                                marginTop: 16,
                                padding: '12px 16px',
                                borderRadius: 8,
                                background: 'rgba(239,68,68,0.15)',
                                color: '#fca5a5',
                                fontSize: 13,
                            }}>
                                ⚠️ {lastError}
                            </div>
                        )}
                    </div>
                )}

                {/* ---- SCANNING SCREEN ---- */}
                {pairedStationId && (
                    <div>
                        {/* Camera View */}
                        <div style={{
                            borderRadius: 16,
                            overflow: 'hidden',
                            background: '#000',
                            position: 'relative',
                            marginBottom: 16,
                        }}>
                            <div id={scannerContainerRef.current} style={{ width: '100%' }} />
                        </div>

                        {/* Disconnect Button */}
                        <button
                            onClick={disconnect}
                            style={{
                                width: '100%',
                                padding: '14px',
                                borderRadius: 12,
                                border: '2px solid rgba(239,68,68,0.4)',
                                background: 'rgba(239,68,68,0.1)',
                                color: '#fca5a5',
                                fontSize: 15,
                                fontWeight: 600,
                                cursor: 'pointer',
                                marginBottom: 20,
                            }}
                        >
                            ⛓️‍💥 Ngắt kết nối
                        </button>

                        {/* Scan Logs */}
                        {scanLogs.length > 0 && (
                            <div>
                                <h3 style={{ fontSize: 14, fontWeight: 600, color: '#94a3b8', marginBottom: 8 }}>
                                    Lịch sử quét ({scanLogs.length})
                                </h3>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                                    {scanLogs.map((log, i) => (
                                        <div
                                            key={i}
                                            style={{
                                                padding: '10px 14px',
                                                borderRadius: 10,
                                                background: 'rgba(255,255,255,0.05)',
                                                border: `1px solid ${log.acked ? 'rgba(74,222,128,0.3)' : 'rgba(255,255,255,0.08)'}`,
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: 10,
                                            }}
                                        >
                                            <span style={{ fontSize: 18 }}>
                                                {log.acked ? '✅' : '⏳'}
                                            </span>
                                            <div style={{ flex: 1, minWidth: 0 }}>
                                                <div style={{
                                                    fontSize: 13,
                                                    fontFamily: 'monospace',
                                                    wordBreak: 'break-all',
                                                    color: '#e2e8f0',
                                                }}>
                                                    {log.content.length > 60
                                                        ? log.content.substring(0, 60) + '...'
                                                        : log.content}
                                                </div>
                                                <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
                                                    {log.timestamp.toLocaleTimeString('vi-VN')}
                                                    {log.acked && ' — PC đã nhận ✓'}
                                                </div>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Info */}
                        {scanLogs.length === 0 && isScannerActive && (
                            <div style={{
                                textAlign: 'center',
                                padding: '40px 20px',
                                color: '#64748b',
                            }}>
                                <div style={{ fontSize: 48, marginBottom: 12 }}>📸</div>
                                <p style={{ fontSize: 15 }}>Đưa mã vào khung hình để quét</p>
                                <p style={{ fontSize: 13, marginTop: 4 }}>
                                    Camera sẽ tự động nhận diện QR/Barcode
                                </p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
}
