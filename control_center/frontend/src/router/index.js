// ─────────────────────────────────────────────────────────────────────────────
// src/router/index.js
//
// Vue Router configuration for the Control Center SPA.
//
// Route structure:
//   /login              — public login page (meta.public = true)
//   /                   → AppLayout (sidebar + top bar wrapper)
//     /dashboard        — overview stats + expiring licenses
//     /servers          — server list + add/edit/health check
//     /clients          — client list + add/edit
//     /sites            — site list with search + status filter
//     /sites/:id        — per-site detail: licenses + deploy history
//     /licenses         — all licenses across all sites
//     /alerts           — alert config + test send
//
// All routes under / use lazy imports (()=>import(...)) so each page is a
// separate chunk — only loaded when the user navigates to it.
//
// Auth guard (beforeEach):
//   Any route without meta.public redirects to /login if the Pinia auth store
//   has no token.  The token is persisted in localStorage and restored on page
//   reload by the auth store initializer.
// ─────────────────────────────────────────────────────────────────────────────
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../components/AppLayout.vue'),
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'servers', component: () => import('../views/Servers.vue') },
      { path: 'clients', component: () => import('../views/Clients.vue') },
      { path: 'sites', component: () => import('../views/Sites.vue') },
      { path: 'sites/:id', component: () => import('../views/SiteDetail.vue') },
      { path: 'licenses', component: () => import('../views/Licenses.vue') },
      { path: 'alerts', component: () => import('../views/Alerts.vue') },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (!to.meta.public && !auth.token) {
    return '/login'
  }
})

export default router
