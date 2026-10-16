import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('livo_access_token')?.value;
  const { pathname } = request.nextUrl;
  const isAuthRoute = pathname === '/login';
  const isPublicAsset = pathname.startsWith('/_next') || 
                        pathname.startsWith('/api') || 
                        pathname === '/favicon.ico' ||
                        pathname === '/favicon.svg' ||
                        pathname === '/manifest.json' ||
                        pathname === '/privacy' ||
                        pathname === '/terms';

  if (isPublicAsset) {
    const res = NextResponse.next();
    res.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
    return res;
  }

  // Unauthenticated access to protected routes -> redirect cleanly to /login
  if (!token && !isAuthRoute) {
    const loginUrl = new URL('/login', request.url);
    if (pathname && pathname !== '/' && !pathname.startsWith('/login')) {
      loginUrl.searchParams.set('return_url', pathname);
    }
    const redirectResponse = NextResponse.redirect(loginUrl);
    redirectResponse.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
    return redirectResponse;
  }

  // Auth route (/login): always allow viewing the login page.
  // Never bounce back to root to prevent infinite ping-pong loops when tokens expire.
  if (isAuthRoute) {
    const res = NextResponse.next();
    res.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
    if (request.nextUrl.searchParams.get('session_expired') === '1') {
      res.cookies.delete('livo_access_token');
      res.cookies.delete('token');
    }
    return res;
  }

  const response = NextResponse.next();
  response.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
