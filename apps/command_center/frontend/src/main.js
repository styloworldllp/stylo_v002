import './index.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'

import {
  FrappeUI,
  Button,
  Input,
  TextInput,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
  setConfig,
  frappeRequest,
  FeatherIcon,
} from 'frappe-ui'

let globalComponents = {
  Button,
  TextInput,
  Input,
  FormControl,
  ErrorMessage,
  Dialog,
  Alert,
  Badge,
  FeatherIcon,
}

let pinia = createPinia()
let app = createApp(App)

setConfig('resourceFetcher', frappeRequest)
app.use(FrappeUI)
app.use(pinia)
app.use(router)
for (let key in globalComponents) {
  app.component(key, globalComponents[key])
}

if (import.meta.env.DEV) {
  // Mirror how the production Jinja template injects boot data: one flat window[key]
  // global per boot key (frappe-ui itself reads e.g. window.csrf_token this way).
  frappeRequest({ url: '/api/method/command_center.www.command_center.get_context_for_dev' }).then(
    (values) => {
      for (const key in values) {
        window[key] = values[key]
      }
      app.mount('#app')
    },
  )
} else {
  app.mount('#app')
}
