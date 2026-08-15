<template>
  <div class="admin-services">
    <section class="panel" style="margin-bottom: 1.25rem">
      <div class="panel-header">
        <div>
          <h1>Dienstgruppen</h1>
          <p class="muted">Gruppen für Zusatzdienste (z. B. Mobiliar)</p>
        </div>
      </div>

      <form class="grid-form" style="margin-bottom: 1.25rem" @submit.prevent="saveGroup">
        <div class="grid-2">
          <label>
            Name
            <input v-model.trim="groupForm.name" required maxlength="120" placeholder="z. B. Mobiliar" />
          </label>
        </div>
        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap">
          <button class="btn" type="submit">{{ groupEditingId ? 'Aktualisieren' : 'Anlegen' }}</button>
          <button v-if="groupEditingId" class="btn secondary" type="button" @click="resetGroupForm">Abbrechen</button>
        </div>
        <p v-if="groupError" class="error">{{ groupError }}</p>
      </form>

      <table class="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Dienste</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="group in groups" :key="group.id">
            <td>{{ group.name }}</td>
            <td>{{ group.service_count }}</td>
            <td style="display: flex; gap: 0.4rem; justify-content: flex-end">
              <button class="btn secondary" type="button" @click="editGroup(group)">Bearbeiten</button>
              <button class="btn danger" type="button" @click="removeGroup(group)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!groups.length" class="muted">Noch keine Dienstgruppen angelegt.</p>
    </section>

    <section class="panel">
      <div class="panel-header">
        <div>
          <h1>Dienste</h1>
          <p class="muted">Name, Gruppe, Bestand und Tagespreis</p>
        </div>
      </div>

      <p v-if="!groups.length" class="muted">Zuerst eine Dienstgruppe anlegen.</p>

      <form
        class="grid-form"
        style="margin-bottom: 1.25rem"
        :class="{ disabled: !groups.length }"
        @submit.prevent="createService"
      >
        <fieldset :disabled="!groups.length" style="border: 0; padding: 0; margin: 0">
          <div class="grid-2">
            <label>
              Name
              <input
                v-model.trim="serviceForm.name"
                required
                maxlength="120"
                placeholder="z. B. Festbankgarnituren"
              />
            </label>
            <label>
              Dienstgruppe
              <select v-model="serviceForm.group_id" required>
                <option disabled value="">Bitte wählen</option>
                <option v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
              </select>
            </label>
            <label>
              Verfügbare Anzahl
              <input v-model.number="serviceForm.available_quantity" type="number" min="0" required />
            </label>
            <label>
              Tagespreis (€)
              <input
                v-model.number="serviceForm.daily_price"
                type="number"
                min="0"
                step="0.01"
                required
              />
            </label>
            <label>
              Kaution (€)
              <input
                v-model.number="serviceForm.deposit"
                type="number"
                min="0"
                step="0.01"
                required
              />
            </label>
          </div>
          <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.85rem">
            <button class="btn" type="submit">Anlegen</button>
          </div>
        </fieldset>
        <p v-if="createError" class="error">{{ createError }}</p>
      </form>

      <label style="max-width: 260px; margin-bottom: 0.85rem">
        Filter nach Gruppe
        <select v-model="filterGroupId" @change="onFilterChange">
          <option value="">Alle</option>
          <option v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
        </select>
      </label>

      <table class="table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Gruppe</th>
            <th>Verfügbare Anzahl</th>
            <th>Tagespreis (€)</th>
            <th>Kaution (€)</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="service in services" :key="service.id">
            <td>
              <input v-model.trim="service.name" maxlength="120" required />
            </td>
            <td>
              <select v-model="service.group_id" required>
                <option v-for="g in groups" :key="g.id" :value="String(g.id)">{{ g.name }}</option>
              </select>
            </td>
            <td>
              <input
                v-model.number="service.available_quantity"
                type="number"
                min="0"
                required
              />
            </td>
            <td>
              <input
                v-model.number="service.daily_price"
                type="number"
                min="0"
                step="0.01"
                required
              />
            </td>
            <td>
              <input
                v-model.number="service.deposit"
                type="number"
                min="0"
                step="0.01"
                required
              />
            </td>
            <td style="display: flex; gap: 0.4rem; justify-content: flex-end">
              <button class="btn danger" type="button" @click="removeService(service)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="groups.length && !services.length" class="muted">Noch keine Dienste angelegt.</p>
      <div
        v-if="services.length"
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
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const groups = ref([])
const services = ref([])
const originals = ref({})
const filterGroupId = ref('')
const groupError = ref('')
const createError = ref('')
const saveError = ref('')
const saveSuccess = ref('')
const saving = ref(false)
const groupEditingId = ref(null)

const groupForm = reactive({ name: '' })
const serviceForm = reactive({
  name: '',
  group_id: '',
  available_quantity: 0,
  daily_price: 0,
  deposit: 0,
})

function snapshot(service) {
  return {
    name: service.name,
    group_id: String(service.group_id),
    available_quantity: Number(service.available_quantity || 0),
    daily_price: Number(service.daily_price || 0),
    deposit: Number(service.deposit || 0),
  }
}

function isDirty(service) {
  const original = originals.value[service.id]
  if (!original) return true
  const current = snapshot(service)
  return (
    current.name !== original.name ||
    current.group_id !== original.group_id ||
    current.available_quantity !== original.available_quantity ||
    current.daily_price !== original.daily_price ||
    current.deposit !== original.deposit
  )
}

const hasChanges = computed(() => services.value.some(isDirty))

function resetGroupForm() {
  groupEditingId.value = null
  groupForm.name = ''
  groupError.value = ''
}

function resetServiceForm() {
  serviceForm.name = ''
  serviceForm.group_id = groups.value[0] ? String(groups.value[0].id) : ''
  serviceForm.available_quantity = 0
  serviceForm.daily_price = 0
  serviceForm.deposit = 0
  createError.value = ''
}

function rememberOriginals(list) {
  const next = {}
  for (const service of list) {
    next[service.id] = snapshot(service)
  }
  originals.value = next
}

async function loadGroups() {
  groups.value = await api.listServiceGroups()
  if (!serviceForm.group_id && groups.value.length) {
    serviceForm.group_id = String(groups.value[0].id)
  }
}

async function loadServices() {
  const groupId = filterGroupId.value ? Number(filterGroupId.value) : null
  const list = await api.listServices(groupId)
  services.value = list.map((service) => ({
    ...service,
    group_id: String(service.group_id),
    available_quantity: Number(service.available_quantity || 0),
    daily_price: Number(service.daily_price || 0),
    deposit: Number(service.deposit || 0),
  }))
  rememberOriginals(services.value)
}

async function reloadAll() {
  await loadGroups()
  await loadServices()
}

async function onFilterChange() {
  saveError.value = ''
  saveSuccess.value = ''
  await loadServices()
}

function editGroup(group) {
  groupEditingId.value = group.id
  groupForm.name = group.name
  groupError.value = ''
}

async function saveGroup() {
  groupError.value = ''
  try {
    if (groupEditingId.value) {
      await api.updateServiceGroup(groupEditingId.value, { name: groupForm.name })
    } else {
      await api.createServiceGroup({ name: groupForm.name })
    }
    resetGroupForm()
    await reloadAll()
  } catch (e) {
    groupError.value = e.message
  }
}

async function removeGroup(group) {
  if (!confirm(`Dienstgruppe „${group.name}“ wirklich löschen?`)) return
  groupError.value = ''
  try {
    await api.deleteServiceGroup(group.id)
    await reloadAll()
  } catch (e) {
    groupError.value = e.message
  }
}

async function createService() {
  createError.value = ''
  saveSuccess.value = ''
  try {
    await api.createService({
      name: serviceForm.name,
      group_id: Number(serviceForm.group_id),
      available_quantity: Number(serviceForm.available_quantity),
      daily_price: Number(serviceForm.daily_price),
      deposit: Number(serviceForm.deposit),
    })
    resetServiceForm()
    await reloadAll()
  } catch (e) {
    createError.value = e.message
  }
}

async function saveAll() {
  saveError.value = ''
  saveSuccess.value = ''
  const dirty = services.value.filter(isDirty)
  if (!dirty.length) return

  saving.value = true
  try {
    for (const service of dirty) {
      await api.updateService(service.id, {
        name: service.name,
        group_id: Number(service.group_id),
        available_quantity: Number(service.available_quantity),
        daily_price: Number(service.daily_price),
        deposit: Number(service.deposit),
      })
    }
    await loadServices()
    saveSuccess.value = 'Änderungen gespeichert.'
  } catch (e) {
    saveError.value = e.message
  } finally {
    saving.value = false
  }
}

async function removeService(service) {
  if (!confirm(`Dienst „${service.name}“ wirklich löschen?`)) return
  saveError.value = ''
  saveSuccess.value = ''
  try {
    await api.deleteService(service.id)
    await reloadAll()
  } catch (e) {
    saveError.value = e.message
  }
}

onMounted(async () => {
  try {
    await reloadAll()
    resetServiceForm()
  } catch (e) {
    groupError.value = e.message
  }
})
</script>
