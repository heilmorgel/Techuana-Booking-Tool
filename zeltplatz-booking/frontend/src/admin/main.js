import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import '../assets/main.css'

createApp(App).use(router).mount('#app')
// #region agent log
fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'8e282a'},body:JSON.stringify({sessionId:'8e282a',runId:'pre-fix',hypothesisId:'E',location:'admin/main.js:mount',message:'admin spa mounted',data:{href:window.location.href,hash:window.location.hash,inIframe:window.parent!==window},timestamp:Date.now()})}).catch(()=>{});
// #endregion
