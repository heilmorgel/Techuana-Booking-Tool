<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h1>Preisprofile</h1>
        <p class="muted">Profile mit eigenen fixen und altersabhängigen Personenpreisen</p>
      </div>
    </div>

    <div class="compact-section" style="margin-bottom: 1.25rem">
      <div class="panel-header compact-header">
        <strong>Profile</strong>
      </div>
      <form class="grid-form" @submit.prevent="saveProfile">
        <div class="grid-2">
          <label>
            Name
            <input
              v-model.trim="profileForm.name"
              required
              maxlength="120"
              placeholder="z. B. Standard"
            />
          </label>
          <label>
            Reihenfolge
            <input v-model.number="profileForm.sort_order" type="number" />
          </label>
          <label>
            Kaution (€)
            <input v-model.number="profileForm.deposit" type="number" min="0" step="0.01" />
          </label>
          <label class="checkbox-label">
            <input v-model="profileForm.is_default" type="checkbox" />
            Als Standard markieren
          </label>
        </div>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap">
          <button class="btn" type="submit">
            {{ editingProfileId ? 'Profil aktualisieren' : 'Profil anlegen' }}
          </button>
          <button
            v-if="editingProfileId"
            class="btn secondary"
            type="button"
            @click="resetProfileForm"
          >
            Abbrechen
          </button>
        </div>
      </form>

      <table class="table" style="margin-top: 0.75rem">
        <thead>
          <tr>
            <th>Name</th>
            <th>Standard</th>
            <th>Kaution</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="p in profiles"
            :key="p.id"
            :class="{ 'row-selected': selectedProfileId === p.id }"
            @click="selectProfile(p.id)"
            style="cursor: pointer"
          >
            <td>{{ p.name }}</td>
            <td>{{ p.is_default ? 'Ja' : '' }}</td>
            <td>{{ formatPrice(p.deposit) }}</td>
            <td style="display: flex; gap: 0.4rem; justify-content: flex-end" @click.stop>
              <button class="btn secondary" type="button" @click="editProfile(p)">Bearbeiten</button>
              <button
                v-if="!p.is_default"
                class="btn secondary"
                type="button"
                @click="setDefault(p)"
              >
                Als Standard
              </button>
              <button class="btn danger" type="button" @click="removeProfile(p)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!profiles.length" class="muted">Noch keine Preisprofile.</p>
      <p v-if="profileError" class="error">{{ profileError }}</p>
    </div>

    <template v-if="selectedProfileId">
      <div class="panel-header">
        <div>
          <h2>Preiskomponenten — {{ selectedProfileName }}</h2>
          <p class="muted">Fixe und altersabhängige Tagespreise für dieses Profil</p>
        </div>
      </div>

      <form class="grid-form" style="margin-bottom: 1.25rem" @submit.prevent="saveElement">
        <div class="grid-2">
          <label>
            Name
            <input
              v-model.trim="elementForm.name"
              required
              maxlength="120"
              placeholder="z. B. Tourismusabgabe"
            />
          </label>
          <label>
            Art
            <select v-model="elementForm.kind" required>
              <option value="fixed">Fix (jede Person)</option>
              <option value="age_based">Altersabhängig</option>
            </select>
          </label>
          <label v-if="elementForm.kind === 'fixed'">
            Tagespreis (€)
            <input
              v-model.number="elementForm.daily_price"
              type="number"
              min="0"
              step="0.01"
              required
            />
          </label>
          <label>
            Reihenfolge
            <input v-model.number="elementForm.sort_order" type="number" />
          </label>
        </div>

        <div v-if="elementForm.kind === 'age_based'" class="compact-section">
          <div class="panel-header compact-header">
            <strong>Altersstufen</strong>
            <button type="button" class="btn secondary btn-sm" @click="addBracket">+ Stufe</button>
          </div>
          <div
            v-for="(bracket, index) in elementForm.brackets"
            :key="index"
            class="person-row person-row-compact"
          >
            <input
              v-model.number="bracket.age_from"
              type="number"
              min="0"
              title="Alter von (inkl.)"
              required
            />
            <input
              v-model.number="bracket.age_to_exclusive"
              type="number"
              min="0"
              title="Alter bis (exklusiv, leer = unbegrenzt)"
              placeholder="∞"
            />
            <input
              v-model.number="bracket.daily_price"
              type="number"
              min="0"
              step="0.01"
              title="Tagespreis"
              required
            />
            <button type="button" class="btn secondary btn-icon" @click="removeBracket(index)">
              ×
            </button>
          </div>
          <p class="muted tiny">
            Alter von inklusiv, bis exklusiv (leer = unbegrenzt). Beispiel: 0–17 und 17–∞
          </p>
        </div>

        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap">
          <button class="btn" type="submit">
            {{ editingElementId ? 'Aktualisieren' : 'Anlegen' }}
          </button>
          <button
            v-if="editingElementId"
            class="btn secondary"
            type="button"
            @click="resetElementForm"
          >
            Abbrechen
          </button>
        </div>
        <p v-if="elementError" class="error">{{ elementError }}</p>
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
              <button class="btn secondary" type="button" @click="editElement(el)">Bearbeiten</button>
              <button class="btn danger" type="button" @click="removeElement(el)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!elements.length" class="muted">Noch keine Preiskomponenten in diesem Profil.</p>
    </template>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'

const profiles = ref([])
const elements = ref([])
const selectedProfileId = ref(null)
const profileError = ref('')
const elementError = ref('')
const editingProfileId = ref(null)
const editingElementId = ref(null)

const profileForm = reactive({
  name: '',
  is_default: false,
  sort_order: 0,
  deposit: 0,
})

const elementForm = reactive({
  name: '',
  kind: 'fixed',
  daily_price: 0,
  sort_order: 0,
  brackets: [],
})

const selectedProfileName = computed(() => {
  const p = profiles.value.find((x) => x.id === selectedProfileId.value)
  return p?.name || ''
})

function formatPrice(value) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(
    Number(value || 0),
  )
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

function resetProfileForm() {
  editingProfileId.value = null
  profileForm.name = ''
  profileForm.is_default = false
  profileForm.sort_order = 0
  profileForm.deposit = 0
  profileError.value = ''
}

function resetElementForm() {
  editingElementId.value = null
  elementForm.name = ''
  elementForm.kind = 'fixed'
  elementForm.daily_price = 0
  elementForm.sort_order = 0
  elementForm.brackets = []
  elementError.value = ''
}

function addBracket() {
  const last = elementForm.brackets[elementForm.brackets.length - 1]
  elementForm.brackets.push({
    age_from: last?.age_to_exclusive ?? 0,
    age_to_exclusive: null,
    daily_price: 0,
  })
}

function removeBracket(index) {
  elementForm.brackets.splice(index, 1)
}

async function loadProfiles() {
  profiles.value = await api.listPriceProfiles()
  if (!selectedProfileId.value && profiles.value.length) {
    const def = profiles.value.find((p) => p.is_default) || profiles.value[0]
    selectedProfileId.value = def.id
  } else if (
    selectedProfileId.value &&
    !profiles.value.some((p) => p.id === selectedProfileId.value)
  ) {
    selectedProfileId.value = profiles.value[0]?.id ?? null
  }
}

async function loadElements() {
  if (!selectedProfileId.value) {
    elements.value = []
    return
  }
  elements.value = await api.listPersonFeeElements(selectedProfileId.value)
}

function selectProfile(id) {
  selectedProfileId.value = id
  resetElementForm()
}

function editProfile(p) {
  editingProfileId.value = p.id
  profileForm.name = p.name
  profileForm.is_default = !!p.is_default
  profileForm.sort_order = p.sort_order || 0
  profileForm.deposit = Number(p.deposit || 0)
  selectedProfileId.value = p.id
}

async function saveProfile() {
  profileError.value = ''
  try {
    const body = {
      name: profileForm.name,
      is_default: !!profileForm.is_default,
      sort_order: Number(profileForm.sort_order) || 0,
      deposit: Number(profileForm.deposit) || 0,
    }
    if (editingProfileId.value) {
      await api.updatePriceProfile(editingProfileId.value, body)
    } else {
      const created = await api.createPriceProfile(body)
      selectedProfileId.value = created.id
    }
    resetProfileForm()
    await loadProfiles()
    await loadElements()
  } catch (e) {
    profileError.value = e.message
  }
}

async function setDefault(p) {
  profileError.value = ''
  try {
    await api.updatePriceProfile(p.id, { is_default: true })
    await loadProfiles()
  } catch (e) {
    profileError.value = e.message
  }
}

async function removeProfile(p) {
  if (!confirm(`Preisprofil „${p.name}“ löschen?`)) return
  profileError.value = ''
  try {
    await api.deletePriceProfile(p.id)
    if (selectedProfileId.value === p.id) selectedProfileId.value = null
    await loadProfiles()
    await loadElements()
  } catch (e) {
    profileError.value = e.message
  }
}

function editElement(el) {
  editingElementId.value = el.id
  elementForm.name = el.name
  elementForm.kind = el.kind
  elementForm.daily_price = Number(el.daily_price || 0)
  elementForm.sort_order = el.sort_order || 0
  elementForm.brackets = (el.brackets || []).map((b) => ({
    age_from: b.age_from,
    age_to_exclusive: b.age_to_exclusive,
    daily_price: Number(b.daily_price || 0),
  }))
}

async function saveElement() {
  elementError.value = ''
  try {
    if (!selectedProfileId.value) {
      elementError.value = 'Bitte ein Preisprofil wählen.'
      return
    }
    if (elementForm.kind === 'age_based' && elementForm.brackets.length === 0) {
      elementError.value = 'Mindestens eine Altersstufe erforderlich.'
      return
    }
    const body = {
      price_profile_id: selectedProfileId.value,
      name: elementForm.name,
      kind: elementForm.kind,
      daily_price: elementForm.kind === 'fixed' ? Number(elementForm.daily_price) : 0,
      sort_order: Number(elementForm.sort_order) || 0,
      brackets:
        elementForm.kind === 'age_based'
          ? elementForm.brackets.map((b) => ({
              age_from: Number(b.age_from),
              age_to_exclusive:
                b.age_to_exclusive === '' || b.age_to_exclusive == null
                  ? null
                  : Number(b.age_to_exclusive),
              daily_price: Number(b.daily_price),
            }))
          : [],
    }
    if (editingElementId.value) {
      const { price_profile_id: _pid, ...updateBody } = body
      await api.updatePersonFeeElement(editingElementId.value, updateBody)
    } else {
      await api.createPersonFeeElement(body)
    }
    resetElementForm()
    await loadElements()
  } catch (e) {
    elementError.value = e.message
  }
}

async function removeElement(el) {
  if (!confirm(`Element „${el.name}“ löschen?`)) return
  elementError.value = ''
  try {
    await api.deletePersonFeeElement(el.id)
    await loadElements()
  } catch (e) {
    elementError.value = e.message
  }
}

watch(selectedProfileId, () => {
  loadElements().catch((e) => {
    elementError.value = e.message
  })
})

onMounted(async () => {
  try {
    await loadProfiles()
    await loadElements()
  } catch (e) {
    profileError.value = e.message
  }
})
</script>

<style scoped>
.row-selected td {
  background: color-mix(in srgb, var(--accent, #2a6f4e) 12%, transparent);
}
.checkbox-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-top: 1.5rem;
}
</style>
