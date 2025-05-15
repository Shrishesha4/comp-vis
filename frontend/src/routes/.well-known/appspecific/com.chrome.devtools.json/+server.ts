import { json } from '@sveltejs/kit';

export function GET() {
  return json({
    version: 1,
    // Add any Chrome DevTools specific configuration here if needed
  });
}