'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Beep sound generator using Web Audio API
 * No external file needed — generates a short beep programmatically
 */
function playBeep() {
    try {
        const audioCtx = new (window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext)();
        const oscillator = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioCtx.destination);

        oscillator.frequency.value = 1800; // Hz — pleasant beep
        oscillator.type = 'sine';
        gainNode.gain.value = 0.3; // Volume

        oscillator.start();
        oscillator.stop(audioCtx.currentTime + 0.15); // 150ms beep

        // Clean up
        oscillator.onended = () => {
            gainNode.disconnect();
            audioCtx.close();
        };
    } catch {
        // Silently fail — audio not critical
    }
}

interface UseRemoteScannerReturn {
    isConnected: boolean;
    stationId: string | null;
    setStationId: (id: string | null) => void;
    lastScan: string | null;
    disconnect: () => void;
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const STORAGE_KEY = 'his_station_id';

/**
 * useRemoteScanner — PC Client Hook
 * 
 * Connects to the WebSocket scanner station and dispatches
 * `HIS_SCANNED_DATA` custom events globally when scan data arrives.
 * 
 * Plays a beep sound and sends an ACK back to the phone.
 */
export function useRemoteScanner(): UseRemoteScannerReturn {
    const [isConnected, setIsConnected] = useState(false);
    const [stationId, setStationIdState] = useState<string | null>(null);
    const [lastScan, setLastScan] = useState<string | null>(null);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const reconnectAttemptRef = useRef(0);

    // Load stationId from localStorage on mount
    useEffect(() => {
        if (typeof window !== 'undefined') {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (stored) {
                setStationIdState(stored);
            }
        }
    }, []);

    // Set station ID (persist to localStorage)
    const setStationId = useCallback((id: string | null) => {
        if (id) {
            localStorage.setItem(STORAGE_KEY, id);
        } else {
            localStorage.removeItem(STORAGE_KEY);
        }
        setStationIdState(id);
    }, []);

    // Disconnect helper
    const disconnect = useCallback(() => {
        if (reconnectTimerRef.current) {
            clearTimeout(reconnectTimerRef.current);
            reconnectTimerRef.current = null;
        }
        if (wsRef.current) {
            wsRef.current.close(1000, 'Manual disconnect');
            wsRef.current = null;
        }
        setIsConnected(false);
        reconnectAttemptRef.current = 0;
    }, []);

    // WebSocket connection effect
    useEffect(() => {
        if (!stationId) {
            disconnect();
            return;
        }

        const connect = () => {
            // Close existing connection
            if (wsRef.current) {
                wsRef.current.close();
            }

            const url = `${WS_BASE}/ws/scanner/${stationId}/`;
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                reconnectAttemptRef.current = 0;
                console.log(`[Scanner] Connected to station: ${stationId}`);
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'scan_event') {
                        const content = data.content;
                        setLastScan(content);

                        // ★ THE MAGIC TRICK — Dispatch global custom event
                        const customEvent = new CustomEvent('HIS_SCANNED_DATA', {
                            detail: content,
                        });
                        window.dispatchEvent(customEvent);

                        // Play beep sound
                        playBeep();

                        // Send ACK back (so phone can vibrate)
                        if (ws.readyState === WebSocket.OPEN) {
                            ws.send(JSON.stringify({ type: 'ack' }));
                        }

                        console.log(`[Scanner] Received scan: ${content.substring(0, 30)}...`);
                    }
                } catch {
                    // Ignore malformed messages
                }
            };

            ws.onclose = (event) => {
                setIsConnected(false);
                wsRef.current = null;

                // Don't reconnect if manually disconnected or station cleared
                if (event.code === 1000) return;

                // Exponential backoff reconnection
                const attempt = reconnectAttemptRef.current;
                const delay = Math.min(1000 * Math.pow(2, attempt), 30000); // Max 30s
                reconnectAttemptRef.current = attempt + 1;

                console.log(`[Scanner] Disconnected. Reconnecting in ${delay}ms (attempt ${attempt + 1})`);
                reconnectTimerRef.current = setTimeout(connect, delay);
            };

            ws.onerror = () => {
                // onclose will handle reconnection
            };
        };

        connect();

        return () => {
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current);
            }
            if (wsRef.current) {
                wsRef.current.close(1000);
            }
        };
    }, [stationId, disconnect]);

    return { isConnected, stationId, setStationId, lastScan, disconnect };
}
