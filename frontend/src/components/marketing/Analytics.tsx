import { headers } from 'next/headers';
import { analyticsOrigin } from '@/lib/analytics';

// GoatCounter's counting script, on the public pages only (never inside the
// app, where a page view would say what a signed-in author is working on).
// Renders nothing unless GOATCOUNTER_URL is set. The script carries the CSP
// nonce; it sends its count to the same origin, which middleware adds to
// connect-src.
export default async function Analytics() {
  const origin = analyticsOrigin();
  if (!origin) return null;
  const nonce = (await headers()).get('x-nonce') ?? undefined;
  return <script data-goatcounter={`${origin}/count`} async src={`${origin}/count.js`} nonce={nonce} />;
}
