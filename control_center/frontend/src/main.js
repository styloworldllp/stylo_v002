// ─────────────────────────────────────────────────────────────────────────────
// src/main.js
//
// Vue 3 application bootstrap.
//
// Registers:
//   Pinia  — global state management (stores/auth.js)
//   Router — Vue Router with history mode (router/index.js)
//   App    — root component that renders <RouterView />
//
// style.css is imported first so Tailwind base/components/utilities load before
// any component-scoped styles.
// ─────────────────────────────────────────────────────────────────────────────
import './style.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
