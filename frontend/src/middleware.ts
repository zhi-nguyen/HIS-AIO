import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Middleware
 * Bảo vệ các routes yêu cầu authentication
 * 
 * Lưu ý: Middleware chạy ở Edge runtime, không truy cập được localStorage
 * Do đó, việc verify token thực sự sẽ được thực hiện ở client-side
 */

// Protected routes - yêu cầu đăng nhập
const protectedRoutes = ['/dashboard'];

// Public routes - không cần đăng nhập
const publicRoutes = ['/login', '/register', '/kiosk'];

export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;

    // Bỏ qua static files và API routes
    if (
        pathname.startsWith('/_next') ||
        pathname.startsWith('/api') ||
        pathname.includes('.')
    ) {
        return NextResponse.next();
    }

    // Kiểm tra có phải protected route không
    const isProtectedRoute = protectedRoutes.some(route =>
        pathname.startsWith(route)
    );

    // Kiểm tra có phải public route không
    const isPublicRoute = publicRoutes.some(route =>
        pathname.startsWith(route)
    );

    // Với protected routes, để client-side AuthContext xử lý redirect
    // Middleware chỉ đảm bảo routing cơ bản

    return NextResponse.next();
}

export const config = {
    matcher: [
        /*
         * Match tất cả paths trừ:
         * - api (API routes)
         * - _next/static (static files)
         * - _next/image (image optimization files)
         * - favicon.ico (favicon file)
         */
        '/((?!api|_next/static|_next/image|favicon.ico).*)',
    ],
};
