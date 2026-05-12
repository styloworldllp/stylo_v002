// ─────────────────────────────────────────────────────────────────────────────
// src/stores/auth.js
//
// Pinia store for admin authentication state.
//
// State:
//   token — JWT string; persisted in localStorage as "cc_token" so it survives
//            page reloads.  Empty string means unauthenticated.
//
// Actions:
//   login(username, password) — POSTs to /api/auth/login, stores the returned
//                               JWT, and sets the Axios Authorization header
//   logout()                  — clears token from state, localStorage, and the
//                               Axios default headers
//
// The store also restores the Authorization header immediately on module load
// if a token already exists in localStorage (page reload scenario).
//
// Used by:
//   router/index.js   — beforeEach guard checks auth.token
//   views/Login.vue   — calls auth.login()
//   components/AppLayout.vue — calls auth.logout() on sign-out button
// ─────────────────────────────────────────────────────────────────────────────
import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('cc_token') || '')

  function setToken(t) {
    token.value = t
    localStorage.setItem('cc_token', t)
    api.defaults.headers.common['Authorization'] = `Bearer ${t}`
  }

  async function login(username, password) {
    const { data } = await api.post('/api/auth/login', { username, password })
    setToken(data.access_token)
  }

  function logout() {
    token.value = ''
    localStorage.removeItem('cc_token')
    delete api.defaults.headers.common['Authorization']
  }

  // Restore auth header on page reload
  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  return { token, login, logout }
})
