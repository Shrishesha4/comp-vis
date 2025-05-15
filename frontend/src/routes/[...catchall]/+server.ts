import { json } from '@sveltejs/kit';

export function GET({ params }) {
  // Check if this is a well-known request
  if (params.catchall.startsWith('.well-known/')) {
    return json({
      version: 1
    });
  }
  
  // Return 404 for other routes
  return new Response('Not found', { status: 404 });
}