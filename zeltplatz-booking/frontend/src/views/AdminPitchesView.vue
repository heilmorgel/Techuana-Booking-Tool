<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h1>Zeltplätze verwalten</h1>
        <p class="muted">Name, Verfügbarkeit und Tagespreis</p>
      </div>
    </div>

    <form class="grid-form" style="margin-bottom: 1.5rem" @submit.prevent="create">
      <div class="grid-2">
        <label>
          Name
          <input v-model.trim="form.name" required maxlength="120" placeholder="z. B. Platz Nord" />
        </label>
        <label>
          Verfügbar von
          <input v-model="form.available_from" type="date" required />
        </label>
        <label>
          Verfügbar bis
          <input v-model="form.available_to" type="date" required />
        </label>
        <label>
          Tagespreis (€)
          <input v-model.number="form.daily_price" type="number" min="0" step="0.01" required />
        </label>
        <label>
          Kaution (€)
          <input v-model.number="form.deposit" type="number" min="0" step="0.01" required />
        </label>
      </div>
      <div style="display: flex; gap: 0.5rem; flex-wrap: wrap">
        <button class="btn" type="submit">Anlegen</button>
      </div>
      <p v-if="createError" class="error">{{ createError }}</p>
    </form>

    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Von</th>
          <th>Bis</th>
          <th>Tagespreis (€)</th>
          <th>Kaution (€)</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pitch in pitches" :key="pitch.id">
          <td>
            <input v-model.trim="pitch.name" maxlength="120" required />
          </td>
          <td>
            <input v-model="pitch.available_from" type="date" required />
          </td>
          <td>
            <input v-model="pitch.available_to" type="date" required />
          </td>
          <td>
            <input v-model.number="pitch.daily_price" type="number" min="0" step="0.01" required />
          </td>
          <td>
            <input v-model.number="pitch.deposit" type="number" min="0" step="0.01" required />
          </td>
          <td style="display: flex; gap: 0.4rem; justify-content: flex-end">
            <button class="btn danger" type="button" @click="remove(pitch)">Löschen</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="!pitches.length" class="muted">Noch keine Zeltplätze angelegt.</p>
    <div
      v-if="pitches.length"
      style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.75rem; align-items: center"
    >
      <button class="btn" type="button" :disabled="saving || !hasChanges" @click="saveAll">
        {{ saving ? 'Speichern…' : 'Speichern' }}
      </button>
      <span v-if="hasChanges" class="muted">Ungespeicherte Änderungen</span>
      <p v-if="saveError" class="error" style="margin: 0">{{ saveError }}</p>
      <p v-if="saveSuccess" class="muted" style="margin: 0">{{ saveSuccess }}</p>
    </div>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const pitches = ref([])
const originals = ref({})
const createError = ref('')
const saveError = ref('')
const saveSuccess = ref('')
const saving = ref(false)

const form = reactive({
  name: '',
  available_from: '',
  available_to: '',
  daily_price: 0,
  deposit: 0,
})

function snapshot(pitch) {
  return {
    name: pitch.name,
    available_from: pitch.available_from,
    available_to: pitch.available_to,
    daily_price: Number(pitch.daily_price || 0),
    deposit: Number(pitch.deposit || 0),
  }
}

function isDirty(pitch) {
  const original = originals.value[pitch.id]
  if (!original) return true
  const current = snapshot(pitch)
  return (
    current.name !== original.name ||
    current.available_from !== original.available_from ||
    current.available_to !== original.available_to ||
    current.daily_price !== original.daily_price ||
    current.deposit !== original.deposit
  )
}

const hasChanges = computed(() => pitches.value.some(isDirty))

function resetForm() {
  form.name = ''
  form.available_from = ''
  form.available_to = ''
  form.daily_price = 0
  form.deposit = 0
  createError.value = ''
}

function rememberOriginals(list) {
  const next = {}
  for (const pitch of list) {
    next[pitch.id] = snapshot(pitch)
  }
  originals.value = next
}

async function load() {
  const list = await api.listPitches()
  pitches.value = list.map((pitch) => ({
    ...pitch,
    daily_price: Number(pitch.daily_price || 0),
    deposit: Number(pitch.deposit || 0),
  }))
  rememberOriginals(pitches.value)
}

async function create() {
  createError.value = ''
  saveSuccess.value = ''
  try {
    await api.createPitch({
      name: form.name,
      available_from: form.available_from,
      available_to: form.available_to,
      daily_price: Number(form.daily_price),
      deposit: Number(form.deposit),
    })
    resetForm()
    await load()
  } catch (e) {
    createError.value = e.message
  }
}

async function saveAll() {
  saveError.value = ''
  saveSuccess.value = ''
  const dirty = pitches.value.filter(isDirty)
  if (!dirty.length) return

  saving.value = true
  try {
    for (const pitch of dirty) {
      await api.updatePitch(pitch.id, {
        name: pitch.name,
        available_from: pitch.available_from,
        available_to: pitch.available_to,
        daily_price: Number(pitch.daily_price),
        deposit: Number(pitch.deposit),
      })
    }
    await load()
    saveSuccess.value = 'Änderungen gespeichert.'
  } catch (e) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

async function remove(pitch) {
  if (!confirm(`Zeltplatz „${pitch.name}“ wirklich löschen?`)) return
  saveError.value = ''
  saveSuccess.value = ''
  try {
    await api.deletePitch(pitch.id)
    await load()
  } catch (e) {
    saveError.value = e.message
  }
}

onMounted(async () => {
  try {
    await load()
  } catch (e) {
    saveError.value = e.message
  }
})
</script>
