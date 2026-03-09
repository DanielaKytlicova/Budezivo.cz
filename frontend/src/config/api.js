/**
 * API Configuration
 * 
 * Determines the correct API base URL based on environment:
 * - Development/Preview: Uses REACT_APP_BACKEND_URL (absolute URL)
 * - Production (Vercel): Uses relative path /api (Vercel proxies to backend)
 */

// Check if we're running on Vercel production (not preview)
const isVercelProduction = typeof window !== 'undefined' && 
  window.location.hostname.includes('budezivo.cz');

// For Vercel production, use relative path (Vercel proxies /api/* to backend)
// For development/preview, use the full backend URL
export const API_BASE_URL = isVercelProduction 
  ? '/api'
  : `${process.env.REACT_APP_BACKEND_URL}/api`;

// Export for backwards compatibility
export const API = API_BASE_URL;

export default API_BASE_URL;
