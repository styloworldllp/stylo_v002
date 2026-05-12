// ─────────────────────────────────────────────────────────────────────────────
// src/api.js
//
// Shared Axios instance used by all views and stores.
//
// baseURL is '/' — the Vite dev server proxies /api/* to http://localhost:8080
// (configured in vite.config.js).  In production, Nginx proxies /api/* to the
// FastAPI container (configured in frontend/nginx.conf).
//
// Global 401 interceptor:
//   If any request returns 401 (token expired or invalid), the interceptor
//   clears the stored token from localStorage and redirects to /login so the
//   user re-authenticates without seeing a confusing error.
// ─────────────────────────────────────────────────────────────────────────────
import axios from 'axios'
import router from './router'

const api = axios.create({ baseURL: '/' })

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('cc_token')
      router.push('/login')
    }
    return Promise.reject(err)
  },
)

export default api
