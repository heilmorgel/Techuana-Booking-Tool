import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import '../assets/main.css'

function parentPathname() {
  try {
    if (window.parent === window) return null
    return window.parent.location.pathname || ''
  } catch {
    return null
  }
}

function parentWantsAdmin(parentPath) {
  if (!parentPath) return false
  // HA panel deep-link: /app/<slug>/admin or /app/<slug>/admin/
  return /\/admin\/?$/.test(parentPath) || /\/admin\//.test(parentPath)
}

const alreadyAdmin = /\/admin(\/|$)/.test(window.location.pathname)

// HA keeps the iframe at ingress "/" when the sidebar URL is /app/<slug>/admin/.
// Detect the parent path and send the iframe to the admin SPA.
if (parentWantsAdmin(parentPathname()) && !alreadyAdmin) {
  window.location.replace(new URL('admin/', window.location.href).href)
} else {
  createApp(App).use(router).mount('#app')
}
