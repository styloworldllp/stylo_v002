<template>
  <div class="min-h-screen bg-gray-900 flex items-center justify-center p-4">
    <div class="w-full max-w-sm">
      <!-- Logo -->
      <div class="flex flex-col items-center mb-8">
        <div class="w-12 h-12 rounded-2xl bg-brand-500 flex items-center justify-center mb-4">
          <span class="text-white font-bold text-xl">S</span>
        </div>
        <h1 class="text-white text-xl font-semibold">Stylo Control Center</h1>
        <p class="text-gray-400 text-sm mt-1">Sign in to your admin account</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-sm text-gray-300 mb-1.5">Username</label>
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            class="w-full bg-gray-800 border border-gray-600 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent placeholder-gray-500"
            placeholder="admin"
          />
        </div>

        <div>
          <label class="block text-sm text-gray-300 mb-1.5">Password</label>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            class="w-full bg-gray-800 border border-gray-600 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent placeholder-gray-500"
            placeholder="••••••••"
          />
        </div>

        <p v-if="error" class="text-red-400 text-sm">{{ error }}</p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full bg-brand-500 hover:bg-brand-600 disabled:opacity-60 text-white rounded-lg py-2.5 text-sm font-medium transition-colors"
        >
          {{ loading ? 'Signing in…' : 'Sign in' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
/**
 * Login.vue — admin authentication page.
 *
 * Renders a centered card on a dark background.
 * Calls auth.login() on submit; on success redirects to /dashboard.
 * Displays server error messages (e.g. "Invalid credentials") inline.
 *
 * Default credentials for dev: admin / stylo-admin
 * (configured in backend/main.py login endpoint)
 */
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const username = ref('admin')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/dashboard')
  } catch (e) {
    error.value = e.response?.data?.detail || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>
