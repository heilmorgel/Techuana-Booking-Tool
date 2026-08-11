<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h1>Personenpreise</h1>
        <p class="muted">Fixe und altersabhängige Tagespreise pro Person</p>
      </div>
    </div>

    <form class="grid-form" style="margin-bottom: 1.25rem" @submit.prevent="save">
      <div class="grid-2">
        <label>
          Name
          <input v-model.trim="form.name" required maxlength="120" placeholder="z. B. Tourismusabgabe" />
        </label>
        <label>
          Art
          <select v-model="form.kind" required>
            <option value="fixed">Fix (jede Person)</option>
            <option value="age_based">Altersabhängig</option>
          </select>
        </label>
        <label v-if="form.kind === 'fixed'">
          Tagespreis (€)
          <input v-model.number="form.daily_price" type="number" min="0" step="0.01" required />
        </label>
        <label>
          Reihenfolge
          <input v-model.number="form.sort_order" type="number" />
        </label>
      </div>

      <div v-if="form.kind === 'age_based'" class="compact-section">
        <div class="panel-header compact-header">
          <strong>Altersstufen</strong>
          <button type="button" class="btn secondary btn-sm" @click="addBracket">+ Stufe</button>
        </div>
        <div v-for="(bracket, index) in form.brackets" :key="index" class="person-row person-row-compact">
          <input v-model.number="bracket.age_from" type="number" min="0" title="Alter von (inkl.)" required />
          <input
            v-model.number="bracket.age_to_exclusive"
            type="number"
            min="0"
            title="Alter bis (exklusiv, leer = unbegrenzt)"
            placeholder="∞"
          />
          <input v-model.number="bracket.daily_price" type="number" min="0" step="0.01" title="Tagespreis" required />
          <button type="button" class="btn secondary btn-icon" @click="removeBracket(index)">×</button>
        </div>
        <p class="muted tiny">Alter von inklusiv, bis exklusiv (leer = unbegrenzt). Beispiel: 0–17 und 17–∞</p>
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
          <th>Art</th>
          <th>Preis / Stufen</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="el in elements" :key="el.id">
          <td>{{ el.name }}</td>
          <td>{{ el.kind === 'fixed' ? 'Fix' : 'Alter' }}</td>
          <td>{{ summarize(el) }}</td>
          <td style="display: flex; gap: 0.4rem; justify-content: flex-end">
            <button class="btn secondary" type="button" @click="edit(el)">Bearbeiten</button>
            <button class="btn danger" type="button" @click="remove(el)">Löschen</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="!elements.length" class="muted">Noch keine Personenpreis-Elemente.</p>
  </section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const elements = ref([])
const error = ref('')
const editingId = ref(null)
const form = reactive({
  name: '',
  kind: 'fixed',
  daily_price: 0,
  sort_order: 0,
  brackets: [],
})

function formatPrice(value) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(Number(value || 0))
}

function summarize(el) {
  if (el.kind === 'fixed') return `${formatPrice(el.daily_price)} / Tag`
  return (el.brackets || [])
    .map((b) => {
      const to = b.age_to_exclusive == null ? '∞' : String(b.age_to_exclusive)
      return `${b.age_from}–${to}: ${formatPrice(b.daily_price)}`
    })
    .join(' · ')
}

function resetForm() {
  editingId.value = null
  form.name = ''
  form.kind = 'fixed'
  form.daily_price = 0
  form.sort_order = 0
  form.brackets = []
  error.value = ''
}

function addBracket() {
  const last = form.brackets[form.brackets.length - 1]
  form.brackets.push({
    age_from: last?.age_to_exclusive ?? 0,
    age_to_exclusive: null,
    daily_price: 0,
  })
}

function removeBracket(index) {
  form.brackets.splice(index, 1)
}

async function load() {
  elements.value = await api.listPersonFeeElements()
}

function edit(el) {
  editingId.value = el.id
  form.name = el.name
  form.kind = el.kind
  form.daily_price = Number(el.daily_price || 0)
  form.sort_order = el.sort_order || 0
  form.brackets = (el.brackets || []).map((b) => ({
    age_from: b.age_from,
    age_to_exclusive: b.age_to_exclusive,
    daily_price: Number(b.daily_price || 0),
  }))
}

async function save() {
  error.value = ''
  try {
    if (form.kind === 'age_based' && form.brackets.length === 0) {
      error.value = 'Mindestens eine Altersstufe erforderlich.'
      return
    }
    const body = {
      name: form.name,
      kind: form.kind,
      daily_price: form.kind === 'fixed' ? Number(form.daily_price) : 0,
      sort_order: Number(form.sort_order) || 0,
      brackets:
        form.kind === 'age_based'
          ? form.brackets.map((b) => ({
              age_from: Number(b.age_from),
              age_to_exclusive:
                b.age_to_exclusive === '' || b.age_to_exclusive == null
                  ? null
                  : Number(b.age_to_exclusive),
              daily_price: Number(b.daily_price),
            }))
          : [],
    }
    if (editingId.value) {
      await api.updatePersonFeeElement(editingId.value, body)
    } else {
      await api.createPersonFeeElement(body)
    }
    resetForm()
    await load()
  } catch (e) {
    error.value = e.message
  }
}

async function remove(el) {
  if (!confirm(`Element „${el.name}“ löschen?`)) return
  error.value = ''
  try {
    await api.deletePersonFeeElement(el.id)
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
