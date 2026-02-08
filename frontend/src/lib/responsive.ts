/**
 * Responsive Utility Hooks & Classes
 * Mobile-first responsive design utilities
 */

import { useState, useEffect } from 'react';

/**
 * Breakpoints theo Tailwind CSS
 */
export const breakpoints = {
    sm: 640,
    md: 768,
    lg: 1024,
    xl: 1280,
    '2xl': 1536,
};

/**
 * Hook kiểm tra breakpoint hiện tại
 */
export function useBreakpoint() {
    const [breakpoint, setBreakpoint] = useState<string>('lg');
    const [isMobile, setIsMobile] = useState(false);
    const [isTablet, setIsTablet] = useState(false);
    const [isDesktop, setIsDesktop] = useState(true);

    useEffect(() => {
        const updateBreakpoint = () => {
            const width = window.innerWidth;

            if (width < breakpoints.sm) {
                setBreakpoint('xs');
                setIsMobile(true);
                setIsTablet(false);
                setIsDesktop(false);
            } else if (width < breakpoints.md) {
                setBreakpoint('sm');
                setIsMobile(true);
                setIsTablet(false);
                setIsDesktop(false);
            } else if (width < breakpoints.lg) {
                setBreakpoint('md');
                setIsMobile(false);
                setIsTablet(true);
                setIsDesktop(false);
            } else if (width < breakpoints.xl) {
                setBreakpoint('lg');
                setIsMobile(false);
                setIsTablet(false);
                setIsDesktop(true);
            } else {
                setBreakpoint('xl');
                setIsMobile(false);
                setIsTablet(false);
                setIsDesktop(true);
            }
        };

        updateBreakpoint();
        window.addEventListener('resize', updateBreakpoint);
        return () => window.removeEventListener('resize', updateBreakpoint);
    }, []);

    return { breakpoint, isMobile, isTablet, isDesktop };
}

/**
 * Hook cho sidebar collapse trên mobile
 */
export function useSidebarCollapse() {
    const { isMobile, isTablet } = useBreakpoint();
    const [collapsed, setCollapsed] = useState(false);

    useEffect(() => {
        setCollapsed(isMobile || isTablet);
    }, [isMobile, isTablet]);

    return { collapsed, setCollapsed, shouldAutoCollapse: isMobile || isTablet };
}

/**
 * Responsive table scroll config
 */
export function useTableScroll() {
    const { isMobile, isTablet } = useBreakpoint();

    if (isMobile) {
        return { x: 800, y: 400 };
    }
    if (isTablet) {
        return { x: 1000, y: 500 };
    }
    return { x: undefined, y: undefined };
}

/**
 * Responsive modal width
 */
export function useModalWidth() {
    const { isMobile, isTablet } = useBreakpoint();

    if (isMobile) return '95vw';
    if (isTablet) return '80vw';
    return 720;
}

/**
 * Grid cols based on screen size
 */
export function useGridCols(base: number = 4) {
    const { isMobile, isTablet } = useBreakpoint();

    if (isMobile) return 1;
    if (isTablet) return Math.min(base, 2);
    return base;
}
