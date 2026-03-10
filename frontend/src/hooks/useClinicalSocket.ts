'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Payload khi có bệnh nhân mới được phân đến phòng khám
 */
export interface ClinicalVisitPayload {
    id: string;
    visit_code: string;
    queue_number: string;
    patient_name: string;
    chief_complaint: string;
    priority: string;
    triage_code: string;
    department: string;
}

interface UseClinicalSocketOptions {
    stationId: string | null;
    onNewPatientAssigned?: (visit: ClinicalVisitPayload) => void;
    onQueueUpdate?: (data: unknown) => void;
}

interface UseClinicalSocketReturn {
    isConnected: boolean;
}

const WS_BASE = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

/**
 * useClinicalSocket — connects to ws/clinical/<stationId>/ for real-time
 * clinical dashboard notifications.
 *
 * Fires callbacks when new patients are assigned to the connected station.
 * Auto-reconnects with exponential backoff.
 */
export function useClinicalSocket(
    options: UseClinicalSocketOptions
): UseClinicalSocketReturn {
    const [isConnected, setIsConnected] = useState(false);
    const wsRef = useRef<WebSocket | null>(null);
    const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const reconnectAttemptRef = useRef(0);

    // Use refs for callbacks to avoid re-connecting on every render
    const onNewPatientRef = useRef(options.onNewPatientAssigned);
    const onQueueUpdateRef = useRef(options.onQueueUpdate);
    onNewPatientRef.current = options.onNewPatientAssigned;
    onQueueUpdateRef.current = options.onQueueUpdate;

    const stationId = options.stationId;

    useEffect(() => {
        if (!stationId) return;

        const connect = () => {
            if (wsRef.current) {
                wsRef.current.close();
            }

            const url = `${WS_BASE}/ws/clinical/${stationId}/`;
            const ws = new WebSocket(url);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsConnected(true);
                reconnectAttemptRef.current = 0;
                console.log('[ClinicalSocket] Connected to station', stationId);
            };

            ws.onmessage = (event) => {
                try {
                    const msg = JSON.parse(event.data);

                    if (msg.type === 'new_patient_assigned' && msg.visit) {
                        onNewPatientRef.current?.(msg.visit as ClinicalVisitPayload);
                    } else if (msg.type === 'queue_update' && msg.data) {
                        onQueueUpdateRef.current?.(msg.data);
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
                console.log(`[ClinicalSocket] Reconnecting in ${delay}ms (attempt ${attempt + 1})`);
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
