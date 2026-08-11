<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h1>Zeltplätze verwalten</h1>
        <p class="muted">Name, Verfügbarkeit und Tagespreis</p>
      </div>
    </div>

    <form class="grid-form" style="margin-bottom: 1.5rem" @submit.prevent="save">
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
      </div>
      <div style="display: flex; gap: 0.5rem; flex-wrap: wrap">
        <button class="btn" type="submit">{{ editingId ? 'Aktualisieren' : 'Anlegen' }}</button>
        <button v-if="editingId" class="btn secondary" type="button" @click="resetForm">Abbrechen</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </form>

    <table class="table">
      <thead>
        <tr>
          <th>Name</th>
          <th>Von</th>
          <th>Bis</th>
          <th>Tagespreis</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="pitch in pitches" :key="pitch.id">
          <td>{{ pitch.name }}</td>
          <td>{{ pitch.available_from }}</td>
          <td>{{ pitch.available_to }}</td>
          <td>{{ formatPrice(pitch.daily_price) }}</td>
          <td style="display: flex; gap: 0.4rem; justify-content: flex-end">
            <button class="btn secondary" type="button" @click="edit(pitch)">Bearbeiten</button>
            <button class="btn danger" type="button" @click="remove(pitch)">Löschen</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="!pitches.length" class="muted">Noch keine Zeltplätze angelegt.</p>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const pitches = ref([])
const error = ref('')
const editingId = ref(null)
const form = reactive({
  name: '',
  available_from: '',
  available_to: '',
  daily_price: 0,
})

function formatPrice(value) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(Number(value || 0))
}

function resetForm() {
  editingId.value = null
  form.name = ''
  form.available_from = ''
  form.available_to = ''
  form.daily_price = 0
  error.value = ''
}

async function load() {
  pitches.value = await api.listPitches()
}

function edit(pitch) {
  editingId.value = pitch.id
  form.name = pitch.name
  form.available_from = pitch.available_from
  form.available_to = pitch.available_to
  form.daily_price = Number(pitch.daily_price || 0)
}

async function save() {
  error.value = ''
  try {
    const body = {
      name: form.name,
      available_from: form.available_from,
      available_to: form.available_to,
      daily_price: Number(form.daily_price),
    }
    if (editingId.value) {
      await api.updatePitch(editingId.value, body)
    } else {
      await api.createPitch(body)
    }
    resetForm()
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove(pitch) {
  if (!confirm(`Zeltplatz „${pitch.name}“ wirklich löschen?`)) return
  error.value = ''
  try {
    await api.deletePitch(pitch.id)
    await load()
  } catch (e) {
    error.value = e.message
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
