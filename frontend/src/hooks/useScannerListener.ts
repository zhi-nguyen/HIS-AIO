import { useEffect, useRef, useCallback } from 'react';

interface UseScannerListenerOptions {
    onScan: (data: string) => void;
    /** Maximum time (in ms) between keystrokes to be considered part of the same scan (default: 30ms) */
    timeout?: number;
    /** Minimum time (in ms) to wait before accepting another scan (default: 1500ms) */
    debounceTime?: number;
    /** Prevent default behavior (e.g., form submission) when a scan is detected (default: true) */
    preventDefaultOnMatch?: boolean;
}

/**
 * Hook to listen for inputs from a hardware barcode/QR scanner acting in Keyboard Emulation (HID) mode.
 * It listens globally to 'keydown' events, accumulating characters that arrive faster than `timeout`.
 * When 'Enter' is pressed, it triggers `onScan` if the accumulated string is long enough.
 */
export function useScannerListener({
    onScan,
    timeout = 30, // Hardware scanners usually output at < 10ms per char
    debounceTime = 1500,
    preventDefaultOnMatch = true,
}: UseScannerListenerOptions) {
    const bufferRef = useRef<string>('');
    const lastKeyTimeRef = useRef<number>(0);
    const lastScanTimeRef = useRef<number>(0);

    const handleKeyDown = useCallback(
        (e: KeyboardEvent) => {
            const currentTime = performance.now();

            // If we are within the debounce period after a successful scan, ignore
            if (currentTime - lastScanTimeRef.current < debounceTime) {
                return;
            }

            // If the time between this key and the last key is greater than our timeout,
            // it's likely human typing, so reset the buffer.
            if (currentTime - lastKeyTimeRef.current > timeout) {
                bufferRef.current = '';
            }

            lastKeyTimeRef.current = currentTime;

            if (e.key === 'Enter') {
                // Determine if it looks like a barcode/QR scan
                // E.g., at least 5 characters accumulated quickly
                if (bufferRef.current.length > 5) {
                    onScan(bufferRef.current);
                    lastScanTimeRef.current = currentTime;

                    if (preventDefaultOnMatch) {
                        e.preventDefault();
                        e.stopPropagation();
                    }
                }
                // Clear buffer after Enter
                bufferRef.current = '';
                return;
            }

            // Accumulate printable characters
            if (e.key.length === 1) {
                bufferRef.current += e.key;
            }
        },
        [onScan, timeout, debounceTime, preventDefaultOnMatch]
    );

    useEffect(() => {
        // Use capture phase to intercept the event before it reaches other elements
        document.addEventListener('keydown', handleKeyDown, true);
        return () => {
            document.removeEventListener('keydown', handleKeyDown, true);
        };
    }, [handleKeyDown]);
}
