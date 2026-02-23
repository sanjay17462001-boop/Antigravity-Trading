/**
 * Get the API base URL for backend calls.
 * Priority: localStorage > env var > same-origin (Vercel API routes)
 *
 * Users can set a custom backend URL (e.g. ngrok tunnel) via
 * the Settings page or browser console:
 *   localStorage.setItem('AG_API_URL', 'https://xxxx.ngrok-free.app')
 */
export function getApiUrl(): string {
    if (typeof window !== "undefined") {
        const stored = localStorage.getItem("AG_API_URL");
        if (stored) return stored.replace(/\/+$/, ""); // trim trailing slash
    }
    return process.env.NEXT_PUBLIC_API_URL || "";
}
