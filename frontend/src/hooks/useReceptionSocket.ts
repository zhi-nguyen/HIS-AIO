'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Lightweight payload from backend WebSocket
 */
export interface WsVisitPayload {
    id: string;
    visit_code: string;
    queue_number: number;
    status: string;
    priority: string;
    check_in_time: string | null;
    chief_complaint: string;
    patient: {
        id: string;
        patient_code: string;
        full_name: string;
    };
}

interface UseReceptionSocketOptions {
    onNewVisit?: (visit: WsVisitPayload) => void;
    onVisitUpdated?: (visit: WsVisitPayload) => void;
}

interface UseReceptionSocketReturn {
    isConnected: boolean;
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

/**
 * useReceptionSocket — connects to ws/reception/ for real-time notifications.
 *
 * Fires callbacks when new visits arrive or existing visits are updated.
 * Auto-reconnects with exponential backoff.
 */
export function useReceptionSocket(
    options: UseReceptionSocketOptions = {}
): UseReceptionSocketReturn {
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const reconnectAttemptRef = useRef(0);

    // Use refs for callbacks to avoid re-connecting on every render
    const onNewVisitRef = useRef(options.onNewVisit);
    const onVisitUpdatedRef = useRef(options.onVisitUpdated);
    onNewVisitRef.current = options.onNewVisit;
    onVisitUpdatedRef.current = options.onVisitUpdated;

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

    useEffect(() => {
        const connect = () => {
            if (wsRef.current) {
                wsRef.current.close();
            }

            const url = `${WS_BASE}/ws/reception/`;
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                reconnectAttemptRef.current = 0;
                console.log('[ReceptionSocket] Connected');
            };

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);

                    if (data.type === 'new_visit' && data.visit) {
                        onNewVisitRef.current?.(data.visit as WsVisitPayload);
                    } else if (data.type === 'visit_updated' && data.visit) {
                        onVisitUpdatedRef.current?.(data.visit as WsVisitPayload);
                    }
                } catch {
                    // Ignore malformed messages
                }
            };

            ws.onclose = (event) => {
                setIsConnected(false);
                wsRef.current = null;

                if (event.code === 1000) return;

                const attempt = reconnectAttemptRef.current;
                const delay = Math.min(1000 * Math.pow(2, attempt), 30000);
                reconnectAttemptRef.current = attempt + 1;

                console.log(`[ReceptionSocket] Reconnecting in ${delay}ms (attempt ${attempt + 1})`);
                reconnectTimerRef.current = setTimeout(connect, delay);
            };

            ws.onerror = () => {
                // onclose handles reconnection
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
    }, [disconnect]);

    return { isConnected };
}
