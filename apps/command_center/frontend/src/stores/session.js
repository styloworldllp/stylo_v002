import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'
import { ref, computed } from 'vue'

export const sessionStore = defineStore('command-center-session', () => {
  function sessionUser() {
    let cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
    let _sessionUser = cookies.get('user_id')
    if (_sessionUser === 'Guest') {
      _sessionUser = null
    }
    return _sessionUser
  }

  let user = ref(sessionUser())
  const isLoggedIn = computed(() => !!user.value)

  const roles = window.user_roles || []
  const isSuperAdmin = computed(() => roles.includes('Command Center Super Admin'))
  const isAdmin = computed(() => roles.includes('Command Center Admin') || isSuperAdmin.value)
  const isSupportStaff = computed(() => roles.includes('Command Center Support Staff'))

  const logout = createResource({
    url: 'logout',
    onSuccess() {
      user.value = null
      window.location.href = '/login?redirect-to=/command-center'
    },
  })

  return { user, isLoggedIn, roles, isSuperAdmin, isAdmin, isSupportStaff, logout }
})
