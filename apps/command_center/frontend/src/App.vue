<template>
  <div class="flex h-full">
    <aside class="w-56 shrink-0 border-r bg-surface-menu-bar p-3 flex flex-col gap-1">
      <div class="px-2 py-3 text-lg font-semibold">Command Center</div>
      <RouterLink
        v-for="item in navItems"
        :key="item.route"
        :to="item.route"
        class="rounded px-2 py-1.5 text-sm hover:bg-surface-gray-2"
        active-class="bg-surface-gray-3 font-medium"
      >
        {{ item.label }}
      </RouterLink>
      <div class="mt-auto px-2 pb-2 text-xs text-ink-gray-5">
        {{ session.user }}
        <button class="ml-2 underline" @click="session.logout.submit()">Log out</button>
      </div>
    </aside>
    <main class="flex-1 overflow-auto p-6">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { sessionStore } from '@/stores/session'

const session = sessionStore()

const navItems = computed(() => {
  const items = [{ label: 'Dashboard', route: '/command-center' }]
  if (session.isAdmin) {
    items.push({ label: 'Sites', route: '/command-center/sites' })
    items.push({ label: 'Site Requests', route: '/command-center/requests' })
  }
  if (session.isSuperAdmin) {
    items.push({ label: 'Servers', route: '/command-center/servers' })
  }
  if (session.isAdmin) {
    items.push({ label: 'Licenses', route: '/command-center/licenses' })
  }
  items.push({ label: 'Support', route: '/command-center/support' })
  if (session.isSuperAdmin) {
    items.push({ label: 'Team', route: '/command-center/team' })
  }
  return items
})
</script>
