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

  // Unauthenticated access to protected routes -> bounce immediately to /login
  if (!token && !isAuthRoute) {
    const loginUrl = new URL('/login', request.url);
    const redirectResponse = NextResponse.redirect(loginUrl);
    redirectResponse.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
    return redirectResponse;
  }

  // Authenticated user hitting /login -> bounce directly to root workspace
  if (token && isAuthRoute) {
    const rootUrl = new URL('/', request.url);
    const redirectResponse = NextResponse.redirect(rootUrl);
    redirectResponse.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
    return redirectResponse;
  }

  const response = NextResponse.next();
  response.headers.set('X-Robots-Tag', 'noindex, nofollow, noarchive');
  return response;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
