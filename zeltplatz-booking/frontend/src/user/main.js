import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { apiBasePath } from '../api'
import '../assets/main.css'

// #region agent log
function _parentPathname() {
  try {
    if (window.parent === window) return { inIframe: false, parentPath: null, readable: true }
    return {
      inIframe: true,
      parentPath: window.parent.location.pathname || '',
      parentHref: window.parent.location.href || '',
      readable: true,
    }
  } catch (err) {
    return { inIframe: true, parentPath: null, readable: false, error: String(err) }
  }
}

function _parentWantsAdmin(parentPath) {
  if (!parentPath) return false
  // HA panel deep-link: /app/<slug>/admin or /app/<slug>/admin/
  return /\/admin\/?$/.test(parentPath) || /\/admin\//.test(parentPath)
}

const _parentInfo = _parentPathname()
const _wantsAdmin = _parentWantsAdmin(_parentInfo.parentPath)
const _alreadyAdmin = /\/admin(\/|$)/.test(window.location.pathname)

fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '3650c0' },
  body: JSON.stringify({
    sessionId: '3650c0',
    hypothesisId: 'A',
    location: 'user/main.js',
    message: 'user_spa_booted',
    data: {
      href: window.location.href,
      pathname: window.location.pathname,
      baseURI: document.baseURI,
      ..._parentInfo,
      wantsAdmin: _wantsAdmin,
      alreadyAdmin: _alreadyAdmin,
      runId: 'admin-deeplink',
    },
    timestamp: Date.now(),
  }),
}).catch(() => {})

// HA keeps iframe at ingress "/" when the sidebar URL is /app/<slug>/admin/.
// Detect parent path and send the iframe to the admin SPA.
if (_wantsAdmin && !_alreadyAdmin) {
  const target = new URL('admin/', window.location.href).href
  fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': '3650c0' },
    body: JSON.stringify({
      sessionId: '3650c0',
      hypothesisId: 'A',
      location: 'user/main.js',
      message: 'redirect_iframe_to_admin',
      data: { target, parentPath: _parentInfo.parentPath, runId: 'admin-deeplink' },
      timestamp: Date.now(),
    }),
  }).catch(() => {})
  window.location.replace(target)
} else {
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
            runId: 'admin-deeplink',
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
          data: { error: String(err), pathname: window.location.pathname, runId: 'admin-deeplink' },
          timestamp: Date.now(),
        }),
      }).catch(() => {}),
    )

  createApp(App).use(router).mount('#app')
}
// #endregion