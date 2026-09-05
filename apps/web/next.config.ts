import type { NextConfig } from "next";

// Strict-Transport-Security is deliberately not set here -- Vercel already injects it
// at the edge for every HTTPS deployment on this platform, confirmed via `curl -I`.
const SECURITY_HEADERS = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Content-Security-Policy",
    value: [
      "default-src 'self'",
      "script-src 'self' 'unsafe-inline'",
      "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
      "font-src 'self' https://fonts.gstatic.com",
      "img-src 'self' data: https:",
      "connect-src 'self' https://bughound-api.vercel.app",
      "frame-ancestors 'none'",
      "base-uri 'self'",
      "form-action 'self'",
    ].join("; "),
  },
];

// Report/scan pages render whatever a scan found on someone else's site -- if a page
// like that ever got indexed, "example.com has 15 security issues" showing up in
// search results is a reputational problem for the site owner, not BugHound. Job ids
// are already unguessable UUIDs, so this is defense in depth on top of that, not the
// only thing stopping indexing.
const NOINDEX_HEADERS = [{ key: "X-Robots-Tag", value: "noindex, nofollow" }];

const nextConfig: NextConfig = {
  async headers() {
    return [
      { source: "/(.*)", headers: SECURITY_HEADERS },
      { source: "/reports/:path*", headers: NOINDEX_HEADERS },
      { source: "/scan/:path*", headers: NOINDEX_HEADERS },
    ];
  },
};

export default nextConfig;
