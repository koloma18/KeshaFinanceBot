import { NextRequest, NextResponse } from "next/server";

const PROTECTED_API = ["/api/sheets", "/api/mono/accounts"];
const PROTECTED_PAGES = ["/", "/analytics", "/transactions"];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  const password = process.env.DASHBOARD_PASSWORD;
  if (!password) return NextResponse.next();

  const cookiePwd = request.cookies.get("dashboard_auth")?.value;
  const isAuthenticated = cookiePwd === password;

  // ── API routes ──────────────────────────────────────────────────────
  const isProtectedApi = PROTECTED_API.some((p) => pathname.startsWith(p));
  if (isProtectedApi) {
    if (!isAuthenticated) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }
    return NextResponse.next();
  }

  // ── Pages ───────────────────────────────────────────────────────────
  const isProtectedPage = PROTECTED_PAGES.some((p) => pathname === p);
  if (isProtectedPage && !isAuthenticated) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/",
    "/analytics",
    "/transactions",
    "/api/sheets/:path*",
    "/api/mono/accounts",
  ],
};
