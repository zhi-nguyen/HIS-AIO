'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import type { CalledPatient, NoShowEntry } from '@/types';

interface QmsBoardData {
    currently_serving: CalledPatient[];
    no_show_list: NoShowEntry[];
}

interface UseQmsSocketOptions {
    stationId: string | null;
    onBoardUpdate?: (data: QmsBoardData) => void;
}

interface UseQmsSocketReturn {
    isConnected: boolean;
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

/**
 * useQmsSocket — connects to ws/qms/display/<stationId>/ for real-time
 * queue board updates.
 *
 * Replaces polling setInterval(fetchQueueBoard, N).
 * Auto-reconnects with exponential backoff.
 */
export function useQmsSocket(
    options: UseQmsSocketOptions
): UseQmsSocketReturn {
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const reconnectAttemptRef = useRef(0);

    const onBoardUpdateRef = useRef(options.onBoardUpdate);
    onBoardUpdateRef.current = options.onBoardUpdate;

    const stationId = options.stationId;

    useEffect(() => {
        if (!stationId) return;

        const connect = () => {
            if (wsRef.current) {
                wsRef.current.close();
            }

            const url = `${WS_BASE}/ws/qms/display/${stationId}/`;
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                reconnectAttemptRef.current = 0;
                console.log('[QmsSocket] Connected to station', stationId);
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);
                    if (msg.type === 'queue_update' && msg.data) {
                        onBoardUpdateRef.current?.({
                            currently_serving: msg.data.currently_serving || [],
                            no_show_list: msg.data.no_show_list || [],
                        });
                    }
                } catch {
                    // Ignore
                }
            };

            ws.onclose = (event) => {
                setIsConnected(false);
                wsRef.current = null;

                if (event.code === 1000) return;

                const attempt = reconnectAttemptRef.current;
                const delay = Math.min(1000 * Math.pow(2, attempt), 30000);
                reconnectAttemptRef.current = attempt + 1;
                console.log(`[QmsSocket] Reconnecting in ${delay}ms (attempt ${attempt + 1})`);
                reconnectTimerRef.current = setTimeout(connect, delay);
            };

            ws.onerror = () => {
                // onclose handles reconnection
            };
        };

        connect();

        // Ping keepalive every 30s
        const pingInterval = setInterval(() => {
            if (wsRef.current?.readyState === WebSocket.OPEN) {
                wsRef.current.send(JSON.stringify({ type: 'ping' }));
            }
        }, 30000);

        return () => {
            clearInterval(pingInterval);
            if (reconnectTimerRef.current) {
                clearTimeout(reconnectTimerRef.current);
            }
            if (wsRef.current) {
                wsRef.current.close(1000);
                wsRef.current = null;
            }
            setIsConnected(false);
            reconnectAttemptRef.current = 0;
        };
    }, [stationId]);

    return { isConnected };
}
