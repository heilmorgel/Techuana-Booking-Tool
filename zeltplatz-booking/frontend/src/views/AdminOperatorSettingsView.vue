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
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const form = reactive({
  organization_name: '',
  address: '',
  iban: '',
})
const hasLogo = ref(false)
const logoSrc = ref('')
const error = ref('')
const savedHint = ref('')
const saving = ref(false)
const savingLogo = ref(false)

function refreshLogoSrc() {
  logoSrc.value = hasLogo.value ? `${api.operatorLogoUrl()}?t=${Date.now()}` : ''
}

async function load() {
  error.value = ''
  const data = await api.getOperatorSettings()
  form.organization_name = data.organization_name || ''
  form.address = data.address || ''
  form.iban = data.iban || ''
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
    })
    form.organization_name = data.organization_name || ''
    form.address = data.address || ''
    form.iban = data.iban || ''
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
  try {
    await load()
  } catch (e) {
    error.value = e.message
  }
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
</style>
