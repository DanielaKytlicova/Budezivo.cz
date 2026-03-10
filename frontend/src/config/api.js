/**
 * API Configuration
 * 
 * Determines the correct API base URL based on environment:
 * - Development/Preview: Uses REACT_APP_BACKEND_URL (absolute URL)
 * - Production (Vercel): Uses REACT_APP_BACKEND_URL pointing to Railway
 * 
 * IMPORTANT: On Vercel production, REACT_APP_BACKEND_URL must be set to 
 * the Railway backend URL (e.g., https://budezivo-backend.up.railway.app)
 */

// Get the backend URL from environment
const backendUrl = process.env.REACT_APP_BACKEND_URL;

// Validate that we have a backend URL configured
if (!backendUrl) {
  console.warn('REACT_APP_BACKEND_URL is not set. API calls will fail.');
}

// Always use the full backend URL
export const API_BASE_URL = backendUrl ? `${backendUrl}/api` : '/api';

// Export for backwards compatibility
export const API = API_BASE_URL;

export default API_BASE_URL;
