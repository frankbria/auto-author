export const dynamic = 'force-dynamic';

export async function GET() {
  // Use a relative URL to avoid hardcoding domains
  return Response.redirect('/sign-up/');
}

export default function Page() {
  return null;
}
