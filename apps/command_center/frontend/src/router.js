import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/command-center',
    name: 'Dashboard',
    component: () => import('@/pages/Dashboard.vue'),
  },
  {
    path: '/command-center/sites',
    name: 'Sites',
    component: () => import('@/pages/Sites.vue'),
  },
  {
    path: '/command-center/sites/:siteName',
    name: 'SiteDetail',
    component: () => import('@/pages/SiteDetail.vue'),
    props: true,
  },
  {
    path: '/command-center/requests',
    name: 'SiteRequests',
    component: () => import('@/pages/SiteRequests.vue'),
  },
  {
    path: '/command-center/servers',
    name: 'Servers',
    component: () => import('@/pages/Servers.vue'),
  },
  {
    path: '/command-center/licenses',
    name: 'Licenses',
    component: () => import('@/pages/Licenses.vue'),
  },
  {
    path: '/command-center/support',
    name: 'Support',
    component: () => import('@/pages/Support.vue'),
  },
  {
    path: '/command-center/team',
    name: 'Team',
    component: () => import('@/pages/Team.vue'),
  },
]

const router = createRouter({
  history: createWebHistory('/'),
  routes,
})

router.beforeEach((to, from, next) => {
  if (!window.frappe?.boot) {
    next()
    return
  }
  next()
})

export default router
