<template>
  <div class="flex h-screen bg-gray-50">
    <!-- Sidebar -->
    <aside class="w-60 flex-shrink-0 bg-gray-900 flex flex-col">
      <!-- Logo -->
      <div class="flex items-center gap-3 px-5 py-5 border-b border-gray-700">
        <div class="w-8 h-8 rounded-lg bg-brand-500 flex items-center justify-center">
          <span class="text-white font-bold text-sm">S</span>
        </div>
        <div>
          <p class="text-white font-semibold text-sm leading-tight">Stylo Control</p>
          <p class="text-gray-400 text-xs">Center</p>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto scrollbar-thin">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors"
          :class="isActive(item.to)
            ? 'bg-brand-600 text-white'
            : 'text-gray-400 hover:bg-gray-800 hover:text-white'"
        >
          <span class="text-base">{{ item.icon }}</span>
          {{ item.label }}
        </RouterLink>
      </nav>

      <!-- Logout -->
      <div class="px-3 py-4 border-t border-gray-700">
        <button
          @click="handleLogout"
          class="flex items-center gap-3 px-3 py-2 w-full rounded-lg text-sm text-gray-400 hover:bg-gray-800 hover:text-white transition-colors"
        >
          <span>🚪</span> Sign out
        </button>
      </div>
    </aside>

    <!-- Main -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Top bar -->
      <header class="h-14 bg-white border-b border-gray-200 flex items-center px-6 flex-shrink-0">
        <h1 class="text-sm font-semibold text-gray-900">
          {{ currentTitle }}
        </h1>
        <div class="ml-auto flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-green-500"></span>
          <span class="text-xs text-gray-500">API connected</span>
        </div>
      </header>

      <!-- Page content -->
      <main class="flex-1 overflow-y-auto p-6">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
/**
 * AppLayout.vue — persistent shell wrapping all authenticated pages.
 *
 * Layout:
 *   ┌─────────────┬───────────────────────────────┐
 *   │  Sidebar    │  Top bar (title + API status)  │
 *   │  (nav items)│───────────────────────────────│
 *   │             │  <RouterView />  (page content) │
 *   └─────────────┴───────────────────────────────┘
 *
 * navItems defines the sidebar links and their emoji icons.
 * isActive() highlights the current route (including child routes like /sites/:id).
 * currentTitle reads from titleMap to show the page name in the top bar.
 * handleLogout() calls auth.logout() and redirects to /login.
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const navItems = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/servers', label: 'Servers', icon: '🖥️' },
  { to: '/clients', label: 'Clients', icon: '🏢' },
  { to: '/sites', label: 'Sites', icon: '🌐' },
  { to: '/licenses', label: 'Licenses', icon: '🔑' },
  { to: '/alerts', label: 'Alerts', icon: '🔔' },
]

const titleMap = {
  '/dashboard': 'Dashboard',
  '/servers': 'Servers',
  '/clients': 'Clients',
  '/sites': 'Sites',
  '/licenses': 'User Licenses',
  '/alerts': 'Alerts',
}

const currentTitle = computed(() => {
  return titleMap[route.path] || 'Site Detail'
})

function isActive(to) {
  return route.path === to || (to !== '/dashboard' && route.path.startsWith(to))
}

function handleLogout() {
  auth.logout()
  router.push('/login')
}
</script>
