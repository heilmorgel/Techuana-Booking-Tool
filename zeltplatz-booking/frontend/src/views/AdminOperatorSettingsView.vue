<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h1>Betreiber / Verein</h1>
        <p class="muted">Kopf- und Fußdaten für Rechnungen inkl. Logo</p>
      </div>
    </div>

    <form class="grid-form" @submit.prevent="save">
      <label>
        Vereinsbezeichnung
        <input
          v-model.trim="form.organization_name"
          maxlength="200"
          placeholder="z. B. Pfadfindergruppe Musterstadt"
        />
      </label>
      <label>
        Adresse
        <textarea
          v-model="form.address"
          rows="4"
          placeholder="Straße und Hausnummer&#10;PLZ Ort&#10;Land"
        ></textarea>
      </label>
      <label>
        IBAN
        <input
          v-model.trim="form.iban"
          maxlength="64"
          placeholder="AT00 0000 0000 0000 0000"
          autocomplete="off"
        />
      </label>
      <label>
        Heimatland
        <select v-model="form.home_country">
          <option v-for="c in countries" :key="c.code" :value="c.code">
            {{ c.code }} — {{ c.name }}
          </option>
        </select>
        <span class="muted tiny">
          Reisedokument in der Personenliste nur bei abweichender Staatsangehörigkeit
        </span>
      </label>

      <div class="logo-block">
        <div class="logo-preview" v-if="hasLogo">
          <img :src="logoSrc" alt="Logo" />
        </div>
        <div class="logo-actions">
          <label class="btn secondary btn-file">
            Logo hochladen
            <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" @change="onLogoSelected" />
          </label>
          <button
            v-if="hasLogo"
            class="btn danger"
            type="button"
            :disabled="savingLogo"
            @click="removeLogo"
          >
            Logo entfernen
          </button>
          <p class="muted tiny">PNG, JPG, GIF oder WebP · max. 2 MB</p>
        </div>
      </div>

      <div style="display: flex; gap: 0.5rem; flex-wrap: wrap">
        <button class="btn" type="submit" :disabled="saving">Speichern</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <p v-if="savedHint" class="muted">{{ savedHint }}</p>
    </form>
  </section>

  <section class="panel danger-zone" data-debug-demo-reset="1">
    <div class="panel-header">
      <div>
        <h2>Demodaten</h2>
        <p class="muted">Aktuelle App-Daten löschen und Demo-Stammdaten neu anlegen</p>
      </div>
    </div>
    <p class="muted tiny">
      Buchungen, Zeltplätze, Dienste, Preisprofile, Rechnungen und das Logo werden unwiderruflich
      gelöscht.
    </p>
    <button class="btn danger" type="button" @click="openReset">Auf Demodaten zurücksetzen</button>
    <p v-if="resetError && !resetOpen" class="error">{{ resetError }}</p>
  </section>

  <div v-if="resetOpen" class="modal-backdrop confirm-layer" @click.self="closeReset">
    <div class="modal modal-confirm" role="dialog" aria-modal="true">
      <h3>Alle Daten löschen?</h3>
      <p class="muted tiny">
        Die aktuellen Daten der installierten App werden unwiderruflich gelöscht und durch die
        Demodaten ersetzt.
      </p>
      <div class="checkbox-list">
        <label>
          <input v-model="resetAcknowledged" type="checkbox" />
          Ich verstehe, dass alle aktuellen Daten gelöscht werden
        </label>
      </div>
      <p v-if="resetError" class="error">{{ resetError }}</p>
      <div class="warning-actions">
        <button
          type="button"
          class="btn danger"
          :disabled="!resetAcknowledged || resetting"
          @click="confirmReset"
        >
          {{ resetting ? 'Setze zurück…' : 'Endgültig zurücksetzen' }}
        </button>
        <button type="button" class="btn secondary" :disabled="resetting" @click="closeReset">
          Abbrechen
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { nextTick, onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const form = reactive({
  organization_name: '',
  address: '',
  iban: '',
  home_country: 'AT',
})
const countries = ref([])
const hasLogo = ref(false)
const logoSrc = ref('')
const error = ref('')
const savedHint = ref('')
const saving = ref(false)
const savingLogo = ref(false)
const resetOpen = ref(false)
const resetAcknowledged = ref(false)
const resetting = ref(false)
const resetError = ref('')

function refreshLogoSrc() {
  logoSrc.value = hasLogo.value ? `${api.operatorLogoUrl()}?t=${Date.now()}` : ''
}

async function load() {
  error.value = ''
  const [data, countryList] = await Promise.all([api.getOperatorSettings(), api.countries()])
  countries.value = countryList
  form.organization_name = data.organization_name || ''
  form.address = data.address || ''
  form.iban = data.iban || ''
  form.home_country = data.home_country || 'AT'
  hasLogo.value = Boolean(data.has_logo)
  refreshLogoSrc()
}

async function save() {
  error.value = ''
  savedHint.value = ''
  saving.value = true
  try {
    const data = await api.updateOperatorSettings({
      organization_name: form.organization_name,
      address: form.address,
      iban: form.iban,
      home_country: form.home_country,
    })
    form.organization_name = data.organization_name || ''
    form.address = data.address || ''
    form.iban = data.iban || ''
    form.home_country = data.home_country || 'AT'
    hasLogo.value = Boolean(data.has_logo)
    savedHint.value = 'Gespeichert.'
  } catch (e) {
    error.value = e.message
  } finally {
    saving.value = false
  }
}

async function onLogoSelected(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  error.value = ''
  savedHint.value = ''
  savingLogo.value = true
  try {
    const data = await api.uploadOperatorLogo(file)
    hasLogo.value = Boolean(data.has_logo)
    refreshLogoSrc()
    savedHint.value = 'Logo aktualisiert.'
  } catch (e) {
    error.value = e.message
  } finally {
    savingLogo.value = false
  }
}

function openReset() {
  resetError.value = ''
  resetAcknowledged.value = false
  resetOpen.value = true
}

function closeReset() {
  if (resetting.value) return
  resetOpen.value = false
  resetAcknowledged.value = false
}

async function confirmReset() {
  if (!resetAcknowledged.value) return
  resetError.value = ''
  resetting.value = true
  try {
    await api.resetDemoData()
    window.location.reload()
  } catch (e) {
    resetError.value = e.message
  } finally {
    resetting.value = false
  }
}

async function removeLogo() {
  if (!confirm('Logo wirklich entfernen?')) return
  error.value = ''
  savedHint.value = ''
  savingLogo.value = true
  try {
    const data = await api.deleteOperatorLogo()
    hasLogo.value = Boolean(data.has_logo)
    refreshLogoSrc()
    savedHint.value = 'Logo entfernt.'
  } catch (e) {
    error.value = e.message
  } finally {
    savingLogo.value = false
  }
}

onMounted(async () => {
  // #region agent log
  fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'8e282a'},body:JSON.stringify({sessionId:'8e282a',runId:'pre-fix',hypothesisId:'A',location:'AdminOperatorSettingsView.vue:onMounted',message:'operator view mounted',data:{hasResetApi:typeof api.resetDemoData==='function',href:window.location.href,path:window.location.pathname,hash:window.location.hash,inIframe:window.parent!==window},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
  try {
    await load()
    // #region agent log
    try {
      const health = await api.health()
      fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'8e282a'},body:JSON.stringify({sessionId:'8e282a',runId:'pre-fix',hypothesisId:'A',location:'AdminOperatorSettingsView.vue:health',message:'backend health',data:{health},timestamp:Date.now()})}).catch(()=>{});
    } catch (healthErr) {
      fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'8e282a'},body:JSON.stringify({sessionId:'8e282a',runId:'pre-fix',hypothesisId:'A',location:'AdminOperatorSettingsView.vue:health',message:'backend health failed',data:{error:String(healthErr)},timestamp:Date.now()})}).catch(()=>{});
    }
    // #endregion
  } catch (e) {
    error.value = e.message
  }
  await nextTick()
  // #region agent log
  const zone = document.querySelector('[data-debug-demo-reset="1"]')
  const btn = zone ? zone.querySelector('button') : null
  const zrect = zone ? zone.getBoundingClientRect() : null
  const cs = zone ? window.getComputedStyle(zone) : null
  fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'8e282a'},body:JSON.stringify({sessionId:'8e282a',runId:'pre-fix',hypothesisId:'B',location:'AdminOperatorSettingsView.vue:layout',message:'danger-zone layout',data:{found:Boolean(zone),btnText:btn?String(btn.textContent||'').trim():null,rect:zrect?{top:zrect.top,bottom:zrect.bottom,height:zrect.height,width:zrect.width}:null,viewportH:window.innerHeight,scrollH:document.documentElement.scrollHeight,display:cs?cs.display:null,visibility:cs?cs.visibility:null,inViewport:zrect?zrect.top<window.innerHeight&&zrect.bottom>0:false},timestamp:Date.now()})}).catch(()=>{});
  // #endregion
})
</script>

<style scoped>
.logo-block {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: flex-start;
  margin: 0.5rem 0 0.25rem;
}

.logo-preview {
  width: 120px;
  height: 90px;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.logo-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.logo-actions {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
  align-items: flex-start;
}

.btn-file {
  position: relative;
  overflow: hidden;
  display: inline-flex;
}

.btn-file input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.danger-zone {
  margin-top: 1.25rem;
}

.danger-zone .btn.danger {
  margin-top: 0.65rem;
}

.modal-confirm .checkbox-list {
  margin: 0.75rem 0 0.25rem;
}
</style>
