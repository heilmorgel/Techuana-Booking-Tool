import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { apiBasePath } from '../api'
import '../assets/main.css'

// #region agent log
fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '3650c0' },
  body: JSON.stringify({
    sessionId: '3650c0',
    hypothesisId: 'D',
    location: 'user/main.js',
    message: 'user_spa_booted',
    data: {
      href: window.location.href,
      pathname: window.location.pathname,
      baseURI: document.baseURI,
      runId: 'post-fix',
    },
    timestamp: Date.now(),
  }),
}).catch(() => {})
fetch(`${apiBasePath()}/health`)
  .then((r) =>
    fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '3650c0' },
      body: JSON.stringify({
        sessionId: '3650c0',
        hypothesisId: 'E',
        location: 'user/main.js',
        message: 'api_health_from_spa',
        data: {
          status: r.status,
          ok: r.ok,
          pathname: window.location.pathname,
          apiBase: apiBasePath(),
          runId: 'post-fix',
        },
        timestamp: Date.now(),
      }),
    }).catch(() => {}),
  )
  .catch((err) =>
    fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '3650c0' },
      body: JSON.stringify({
        sessionId: '3650c0',
        hypothesisId: 'E',
        location: 'user/main.js',
        message: 'api_health_failed',
        data: { error: String(err), pathname: window.location.pathname, runId: 'post-fix' },
        timestamp: Date.now(),
      }),
    }).catch(() => {}),
  )
// #endregion

createApp(App).use(router).mount('#app')
