// CORS headers for the browser-facing `subscribe` function. The confirm/unsubscribe functions
// are visited directly from email links (no preflight), so they don't need these.
export const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods': 'POST, OPTIONS',
};
