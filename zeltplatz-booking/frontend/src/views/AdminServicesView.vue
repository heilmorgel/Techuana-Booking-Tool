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
        @submit.prevent="saveService"
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
            <button class="btn" type="submit">{{ serviceEditingId ? 'Aktualisieren' : 'Anlegen' }}</button>
            <button
              v-if="serviceEditingId"
              class="btn secondary"
              type="button"
              @click="resetServiceForm"
            >
              Abbrechen
            </button>
          </div>
        </fieldset>
        <p v-if="serviceError" class="error">{{ serviceError }}</p>
      </form>

      <label style="max-width: 260px; margin-bottom: 0.85rem">
        Filter nach Gruppe
        <select v-model="filterGroupId" @change="loadServices">
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
            <th>Tagespreis</th>
            <th>Kaution</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="service in services" :key="service.id">
            <td>{{ service.name }}</td>
            <td>{{ service.group_name }}</td>
            <td>{{ service.available_quantity }}</td>
            <td>{{ formatPrice(service.daily_price) }}</td>
            <td>{{ formatPrice(service.deposit) }}</td>
            <td style="display: flex; gap: 0.4rem; justify-content: flex-end">
              <button class="btn secondary" type="button" @click="editService(service)">Bearbeiten</button>
              <button class="btn danger" type="button" @click="removeService(service)">Löschen</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="groups.length && !services.length" class="muted">Noch keine Dienste angelegt.</p>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { api } from '../api'

const groups = ref([])
const services = ref([])
const filterGroupId = ref('')
const groupError = ref('')
const serviceError = ref('')
const groupEditingId = ref(null)
const serviceEditingId = ref(null)

const groupForm = reactive({ name: '' })
const serviceForm = reactive({
  name: '',
  group_id: '',
  available_quantity: 0,
  daily_price: 0,
  deposit: 0,
})

function formatPrice(value) {
  const amount = Number(value || 0)
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(amount)
}

function resetGroupForm() {
  groupEditingId.value = null
  groupForm.name = ''
  groupError.value = ''
}

function resetServiceForm() {
  serviceEditingId.value = null
  serviceForm.name = ''
  serviceForm.group_id = groups.value[0] ? String(groups.value[0].id) : ''
  serviceForm.available_quantity = 0
  serviceForm.daily_price = 0
  serviceForm.deposit = 0
  serviceError.value = ''
}

async function loadGroups() {
  groups.value = await api.listServiceGroups()
  if (!serviceForm.group_id && groups.value.length) {
    serviceForm.group_id = String(groups.value[0].id)
  }
}

async function loadServices() {
  const groupId = filterGroupId.value ? Number(filterGroupId.value) : null
  services.value = await api.listServices(groupId)
}

async function reloadAll() {
  await loadGroups()
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

function editService(service) {
  serviceEditingId.value = service.id
  serviceForm.name = service.name
  serviceForm.group_id = String(service.group_id)
  serviceForm.available_quantity = service.available_quantity
  serviceForm.daily_price = Number(service.daily_price || 0)
  serviceForm.deposit = Number(service.deposit || 0)
  serviceError.value = ''
}

async function saveService() {
  serviceError.value = ''
  try {
    const body = {
      name: serviceForm.name,
      group_id: Number(serviceForm.group_id),
      available_quantity: Number(serviceForm.available_quantity),
      daily_price: Number(serviceForm.daily_price),
      deposit: Number(serviceForm.deposit),
    }
    if (serviceEditingId.value) {
      await api.updateService(serviceEditingId.value, body)
    } else {
      await api.createService(body)
    }
    resetServiceForm()
    await reloadAll()
  } catch (e) {
    serviceError.value = e.message
  }
}

async function removeService(service) {
  if (!confirm(`Dienst „${service.name}“ wirklich löschen?`)) return
  serviceError.value = ''
  try {
    await api.deleteService(service.id)
    await reloadAll()
  } catch (e) {
    serviceError.value = e.message
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
