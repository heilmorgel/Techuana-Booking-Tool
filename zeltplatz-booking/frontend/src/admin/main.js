import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { apiBasePath, appRootPath } from '../api'
import '../assets/main.css'

// #region agent log
fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '3650c0' },
  body: JSON.stringify({
    sessionId: '3650c0',
    hypothesisId: 'D',
    location: 'admin/main.js',
    message: 'admin_spa_booted',
    data: {
      href: window.location.href,
      pathname: window.location.pathname,
      search: window.location.search,
      hash: window.location.hash,
      baseURI: document.baseURI,
      appRoot: appRootPath(),
      apiBase: apiBasePath(),
      inIframe: window.top !== window.self,
      runId: 'admin-url',
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
        location: 'admin/main.js',
        message: 'admin_api_health',
        data: { status: r.status, ok: r.ok, apiBase: apiBasePath(), runId: 'admin-url' },
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
        location: 'admin/main.js',
        message: 'admin_api_health_failed',
        data: { error: String(err), apiBase: apiBasePath(), runId: 'admin-url' },
        timestamp: Date.now(),
      }),
    }).catch(() => {}),
  )
// #endregion

createApp(App).use(router).mount('#app')

