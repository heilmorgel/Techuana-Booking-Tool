<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <div class="modal modal-compact amend-modal" role="dialog" aria-modal="true">
      <div class="panel-header compact-header">
        <h2>Buchung anpassen</h2>
        <button type="button" class="btn secondary btn-sm" @click="emit('close')">Schließen</button>
      </div>

      <p v-if="loading" class="muted tiny">Lade…</p>
      <p v-else-if="error" class="error">{{ error }}</p>

      <template v-else>
        <p class="muted tiny">
          {{ booking?.group_name }} · {{ booking?.start_date }} – {{ booking?.end_date }}
        </p>

        <section class="compact-section">
          <strong>Aktuell gebucht (entfernen möglich)</strong>

          <div class="amend-block">
            <h4>Zeltplätze</h4>
            <p v-if="!activePitches.length" class="muted tiny">Keine</p>
            <div v-for="p in activePitches" :key="p.id" class="amend-row">
              <span>{{ p.name }}</span>
              <button type="button" class="btn secondary btn-sm" @click="removePitch(p.id)">Entfernen</button>
            </div>
          </div>

          <div class="amend-block">
            <h4>Personen</h4>
            <p v-if="!activePersons.length" class="muted tiny">Keine</p>
            <div v-for="(person, idx) in activePersons" :key="idx" class="amend-row">
              <span>
                {{ person.name }} ({{ person.birth_date }}, {{ person.nationality }},
                {{ profileName(person.price_profile_id) }}
                <template v-if="person.travel_document">, {{ person.travel_document }}</template>)
              </span>
              <button type="button" class="btn secondary btn-sm" @click="removePerson(idx)">Entfernen</button>
            </div>
          </div>

          <div class="amend-block">
            <h4>Dienste</h4>
            <p v-if="!activeServiceRows.length" class="muted tiny">Keine</p>
            <div v-for="svc in activeServiceRows" :key="svc.service_id" class="amend-row">
              <span>{{ svc.quantity }}× {{ svc.name }}</span>
              <button type="button" class="btn secondary btn-sm" @click="removeService(svc.service_id)">
                Entfernen
              </button>
            </div>
          </div>
        </section>

        <section class="compact-section">
          <strong>Zum Hinzufügen verfügbar</strong>

          <div class="amend-block">
            <h4>Zeltplätze</h4>
            <p v-if="loadingAvail" class="muted tiny">Lade…</p>
            <p v-else-if="!availablePitchesToAdd.length" class="muted tiny">Keine weiteren freien Plätze</p>
            <div v-for="p in availablePitchesToAdd" :key="p.id" class="amend-row">
              <span>{{ p.name }}</span>
              <button type="button" class="btn btn-sm" @click="addPitch(p)">Hinzufügen</button>
            </div>
          </div>

          <div class="amend-block">
            <h4>Dienste</h4>
            <p v-if="!availableServicesToAdd.length" class="muted tiny">Keine weiteren Dienste</p>
            <div v-for="svc in availableServicesToAdd" :key="svc.service_id" class="amend-row">
              <div class="service-meta">
                <span class="service-name">{{ svc.name }}</span>
                <span class="muted tiny">frei {{ svc.remaining }}/{{ svc.available_quantity }}</span>
              </div>
              <div class="qty-stepper">
                <button type="button" class="btn secondary btn-icon" @click="bumpAddQty(svc, -1)">−</button>
                <span class="qty-readonly">{{ addQuantities[svc.service_id] || 0 }}</span>
                <button type="button" class="btn secondary btn-icon" @click="bumpAddQty(svc, 1)">+</button>
                <button
                  type="button"
                  class="btn btn-sm"
                  :disabled="!(addQuantities[svc.service_id] > 0)"
                  @click="commitAddService(svc)"
                >
                  Hinzufügen
                </button>
              </div>
            </div>
          </div>

          <div class="amend-block">
            <h4>Person hinzufügen</h4>
            <div class="person-row person-row-compact">
              <input v-model.trim="newPerson.name" placeholder="Name" />
              <input v-model="newPerson.birth_date" type="date" title="Geburtsdatum" />
              <select v-model="newPerson.nationality">
                <option v-for="c in countries" :key="c.code" :value="c.code">{{ c.code }}</option>
              </select>
              <select v-model.number="newPerson.price_profile_id" title="Preisprofil">
                <option v-for="p in priceProfiles" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
              <input
                v-if="showTravelDocument(newPerson)"
                v-model.trim="newPerson.travel_document"
                placeholder="Reisedokument"
                title="Reisedokument"
                class="person-travel-doc"
              />
              <button type="button" class="btn btn-sm" @click="addPerson">Hinzufügen</button>
            </div>
          </div>
        </section>

        <div class="panel-header" style="margin-top: 0.75rem">
          <label>
            Abreise (optional ändern)
            <input v-model="endDate" type="date" :min="booking?.start_date" />
          </label>
          <button type="button" class="btn" :disabled="!hasChanges || saving" @click="openConfirm">
            Weiter…
          </button>
        </div>
      </template>
    </div>

    <div v-if="confirmOpen" class="modal-backdrop confirm-layer" @click.self="confirmOpen = false">
      <div class="modal modal-confirm" role="dialog" aria-modal="true">
        <h3>Wirkdatum festlegen</h3>
        <p class="muted tiny">Ab diesem Tag gelten die Änderungen.</p>
        <label>
          Wirkdatum
          <input
            v-model="effectiveDate"
            type="date"
            required
            :min="booking?.start_date"
            :max="endDate"
          />
        </label>
        <ul class="change-preview">
          <li v-for="(line, i) in previewLines" :key="i">{{ line }}</li>
        </ul>
        <p v-if="confirmError" class="error">{{ confirmError }}</p>
        <div class="warning-actions">
          <button type="button" class="btn" :disabled="saving" @click="submitAmend">Speichern</button>
          <button type="button" class="btn secondary" :disabled="saving" @click="confirmOpen = false">
            Zurück
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'

const props = defineProps({
  open: { type: Boolean, default: false },
  bookingId: { type: [Number, String], required: true },
})
const emit = defineEmits(['close', 'saved'])

const loading = ref(false)
const loadingAvail = ref(false)
const saving = ref(false)
const error = ref('')
const confirmError = ref('')
const confirmOpen = ref(false)
const booking = ref(null)
const countries = ref([])
const homeCountry = ref('AT')
const priceProfiles = ref([])
const availablePitches = ref([])
const availability = ref([])
const endDate = ref('')
const effectiveDate = ref('')

const activePitchIds = ref([])
const activePersons = ref([])
const activeServices = reactive({}) // service_id -> { quantity, name, group_name }
const addQuantities = reactive({})
const pitchNameById = ref({})

const initialSnapshot = ref(null)

const newPerson = reactive({
  name: '',
  birth_date: '',
  nationality: 'AT',
  travel_document: '',
  price_profile_id: null,
})

function showTravelDocument(person) {
  return (person?.nationality || '').toUpperCase() !== (homeCountry.value || 'AT').toUpperCase()
}

function todayIso() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function defaultPriceProfileId() {
  const def = priceProfiles.value.find((p) => p.is_default)
  return def?.id ?? priceProfiles.value[0]?.id ?? null
}

function profileName(id) {
  return priceProfiles.value.find((p) => p.id === id)?.name || `#${id}`
}

const activePitches = computed(() =>
  activePitchIds.value.map((id) => ({
    id,
    name: pitchNameById.value[id] || `Platz #${id}`,
  })),
)

const activeServiceRows = computed(() =>
  Object.entries(activeServices)
    .filter(([, v]) => v.quantity > 0)
    .map(([id, v]) => ({ service_id: Number(id), ...v }))
    .sort((a, b) => a.name.localeCompare(b.name, 'de')),
)

const availablePitchesToAdd = computed(() =>
  availablePitches.value.filter((p) => !activePitchIds.value.includes(p.id)),
)

const availableServicesToAdd = computed(() =>
  availability.value.filter((s) => !(activeServices[s.service_id]?.quantity > 0)),
)

const hasChanges = computed(() => {
  if (!initialSnapshot.value) return false
  const snap = initialSnapshot.value
  if (endDate.value !== snap.endDate) return true
  if (JSON.stringify([...activePitchIds.value].sort()) !== JSON.stringify([...snap.pitchIds].sort())) {
    return true
  }
  if (JSON.stringify(activePersons.value) !== JSON.stringify(snap.persons)) return true
  const svcNow = Object.fromEntries(
    Object.entries(activeServices)
      .filter(([, v]) => v.quantity > 0)
      .map(([k, v]) => [k, v.quantity]),
  )
  return JSON.stringify(svcNow) !== JSON.stringify(snap.services)
})

const previewLines = computed(() => buildPreviewLines())

function buildPreviewLines() {
  if (!initialSnapshot.value) return []
  const snap = initialSnapshot.value
  const lines = []
  const beforeP = new Set(snap.pitchIds)
  const afterP = new Set(activePitchIds.value)
  for (const id of beforeP) {
    if (!afterP.has(id)) lines.push(`− Platz "${pitchNameById.value[id] || id}"`)
  }
  for (const id of afterP) {
    if (!beforeP.has(id)) lines.push(`+ Platz "${pitchNameById.value[id] || id}"`)
  }
  const personKey = (p) => `${p.name}|${p.birth_date}|${p.nationality}`
  const beforePer = new Map(snap.persons.map((p) => [personKey(p), p.name]))
  const afterPer = new Map(activePersons.value.map((p) => [personKey(p), p.name]))
  for (const [k, name] of beforePer) {
    if (!afterPer.has(k)) lines.push(`− Person "${name}"`)
  }
  for (const [k, name] of afterPer) {
    if (!beforePer.has(k)) lines.push(`+ Person "${name}"`)
  }
  const beforeS = snap.services
  const afterS = Object.fromEntries(
    Object.entries(activeServices)
      .filter(([, v]) => v.quantity > 0)
      .map(([k, v]) => [k, v.quantity]),
  )
  const ids = new Set([...Object.keys(beforeS), ...Object.keys(afterS)])
  for (const id of ids) {
    const oldQ = beforeS[id] || 0
    const newQ = afterS[id] || 0
    const name = activeServices[id]?.name || availability.value.find((s) => String(s.service_id) === id)?.name || id
    if (oldQ === newQ) continue
    if (oldQ === 0) lines.push(`+ ${newQ}x ${name}`)
    else if (newQ === 0) lines.push(`− ${oldQ}x ${name}`)
    else lines.push(`~ ${name}: ${oldQ}x → ${newQ}x`)
  }
  if (endDate.value !== snap.endDate) {
    lines.push(`Abreise ${snap.endDate} → ${endDate.value}`)
  }
  return lines.length ? lines : ['Keine Netto-Änderung']
}

async function load() {
  loading.value = true
  error.value = ''
  confirmOpen.value = false
  try {
    const [b, pitches, meta, profiles] = await Promise.all([
      api.getBooking(props.bookingId),
      api.listPitches(),
      countries.value.length
        ? Promise.resolve({ countries: countries.value, home_country: homeCountry.value })
        : api.getMeta(),
      priceProfiles.value.length ? Promise.resolve(priceProfiles.value) : api.listPriceProfiles(),
    ])
    countries.value = meta.countries || countries.value
    homeCountry.value = meta.home_country || homeCountry.value || 'AT'
    priceProfiles.value = profiles
    if (newPerson.price_profile_id == null) {
      newPerson.price_profile_id = defaultPriceProfileId()
    }
    if (!newPerson.nationality) {
      newPerson.nationality = homeCountry.value
    }
    booking.value = b
    endDate.value = b.end_date
    const names = {}
    for (const p of pitches) names[p.id] = p.name
    for (const seg of b.pitch_segments || []) {
      if (seg.pitch_name) names[seg.pitch_id] = seg.pitch_name
    }
    pitchNameById.value = names

    const today = todayIso()
    const asOf = today > b.start_date && today < b.end_date ? today : b.start_date
    activePitchIds.value = [...(b.pitch_ids || [])]

    activePersons.value = (b.persons || [])
      .filter((p) => p.end_date > asOf)
      .map((p) => ({
        name: p.name,
        birth_date: p.birth_date,
        nationality: p.nationality,
        travel_document: p.travel_document || '',
        price_profile_id: p.price_profile_id ?? defaultPriceProfileId(),
        start_date: p.start_date,
        end_date: p.end_date,
      }))

    Object.keys(activeServices).forEach((k) => delete activeServices[k])
    for (const svc of b.services || []) {
      if (svc.start_date <= asOf && asOf < svc.end_date) {
        activeServices[svc.service_id] = {
          quantity: svc.quantity,
          name: svc.service_name,
          group_name: svc.group_name,
        }
      }
    }

    initialSnapshot.value = {
      endDate: b.end_date,
      pitchIds: [...activePitchIds.value],
      persons: JSON.parse(JSON.stringify(activePersons.value)),
      services: Object.fromEntries(
        Object.entries(activeServices).map(([k, v]) => [k, v.quantity]),
      ),
    }

    await reloadAvailability(asOf, b.end_date)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function reloadAvailability(start, end) {
  loadingAvail.value = true
  try {
    const [pitches, services] = await Promise.all([
      api.availablePitches(start, end, props.bookingId),
      api.servicesAvailability(start, end, props.bookingId),
    ])
    availablePitches.value = pitches
    availability.value = services
    Object.keys(addQuantities).forEach((k) => delete addQuantities[k])
    for (const s of services) addQuantities[s.service_id] = 0
  } catch (e) {
    error.value = e.message
  } finally {
    loadingAvail.value = false
  }
}

function removePitch(id) {
  activePitchIds.value = activePitchIds.value.filter((x) => x !== id)
}

function addPitch(p) {
  if (!activePitchIds.value.includes(p.id)) {
    activePitchIds.value = [...activePitchIds.value, p.id]
    pitchNameById.value = { ...pitchNameById.value, [p.id]: p.name }
  }
}

function removePerson(idx) {
  activePersons.value.splice(idx, 1)
}

function addPerson() {
  if (
    !newPerson.name?.trim() ||
    !newPerson.birth_date ||
    !newPerson.nationality ||
    !newPerson.price_profile_id
  ) {
    error.value = 'Bitte Personenangaben vollständig ausfüllen.'
    return
  }
  error.value = ''
  activePersons.value.push({
    name: newPerson.name.trim(),
    birth_date: newPerson.birth_date,
    nationality: newPerson.nationality,
    travel_document: showTravelDocument(newPerson) ? newPerson.travel_document || '' : '',
    price_profile_id: newPerson.price_profile_id,
    start_date: todayIso(),
    end_date: endDate.value,
  })
  newPerson.name = ''
  newPerson.birth_date = ''
  newPerson.nationality = homeCountry.value || 'AT'
  newPerson.travel_document = ''
  newPerson.price_profile_id = defaultPriceProfileId()
}

function removeService(serviceId) {
  delete activeServices[serviceId]
}

function bumpAddQty(svc, delta) {
  const cur = Number(addQuantities[svc.service_id] || 0)
  addQuantities[svc.service_id] = Math.max(0, cur + delta)
}

function commitAddService(svc) {
  const qty = Number(addQuantities[svc.service_id] || 0)
  if (qty <= 0) return
  activeServices[svc.service_id] = {
    quantity: qty,
    name: svc.name,
    group_name: svc.group_name,
  }
  addQuantities[svc.service_id] = 0
}

function openConfirm() {
  if (!activePitchIds.value.length) {
    error.value = 'Mindestens ein Zeltplatz muss bleiben.'
    return
  }
  error.value = ''
  const t = todayIso()
  const start = booking.value.start_date
  const end = endDate.value
  effectiveDate.value = t > start && t < end ? t : start
  confirmOpen.value = true
  confirmError.value = ''
}

async function submitAmend() {
  confirmError.value = ''
  if (!effectiveDate.value || effectiveDate.value < booking.value.start_date || effectiveDate.value >= endDate.value) {
    confirmError.value = 'Wirkdatum muss innerhalb [Anreise, Abreise) liegen.'
    return
  }
  saving.value = true
  try {
    const persons = activePersons.value.map((p) => ({
      name: p.name,
      birth_date: p.birth_date,
      nationality: p.nationality,
      price_profile_id: p.price_profile_id,
      start_date: p.start_date < effectiveDate.value ? effectiveDate.value : p.start_date,
      end_date: p.end_date > endDate.value ? endDate.value : p.end_date,
    }))
    await api.amendBooking(props.bookingId, {
      effective_date: effectiveDate.value,
      end_date: endDate.value,
      pitch_ids: activePitchIds.value,
      persons,
      services: Object.entries(activeServices)
        .filter(([, v]) => v.quantity > 0)
        .map(([id, v]) => ({ service_id: Number(id), quantity: v.quantity })),
    })
    confirmOpen.value = false
    emit('saved')
    emit('close')
  } catch (e) {
    confirmError.value = e.message
  } finally {
    saving.value = false
  }
}

watch(
  () => [props.open, props.bookingId],
  ([isOpen]) => {
    if (isOpen) load()
  },
  { immediate: true },
)

onMounted(async () => {
  const [countryList, profiles] = await Promise.all([api.countries(), api.listPriceProfiles()])
  countries.value = countryList
  priceProfiles.value = profiles
  newPerson.price_profile_id = defaultPriceProfileId()
})
</script>
