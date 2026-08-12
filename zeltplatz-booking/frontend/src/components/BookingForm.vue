<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <div
      class="modal modal-compact"
      :class="{ 'modal-with-history': isExisting }"
      role="dialog"
      aria-modal="true"
    >
      <div class="booking-dialog-body">
        <div class="booking-dialog-main">
          <div class="panel-header compact-header">
            <h2>{{ dialogTitle }}</h2>
            <div class="header-actions">
              <button
                v-if="depositDue > 0"
                type="button"
                class="btn btn-sm"
                :class="depositPaidAt ? '' : 'secondary'"
                :disabled="!isExisting || togglingDeposit"
                :title="
                  !isExisting
                    ? 'Kaution kann nach dem Speichern markiert werden'
                    : depositPaidAt
                      ? 'Klicken zum Zurücksetzen'
                      : 'Klicken, um Kaution als eingehoben zu markieren'
                "
                @click="toggleDeposit"
              >
                {{ depositButtonLabel }}
              </button>
              <button
                v-if="canImportGaesteblatt"
                type="button"
                class="btn secondary btn-sm"
                :disabled="importing"
                @click="triggerImport"
              >
                {{ importing ? 'Import…' : 'Import Gästeblatt' }}
              </button>
              <input
                ref="importInput"
                type="file"
                accept=".xlsx,.xltx,.xlsm,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                hidden
                @change="onImportFile"
              />
              <button
                v-if="canAmend && locked"
                type="button"
                class="btn btn-sm"
                @click="amendDialogOpen = true"
              >
                Anpassen
              </button>
              <button type="button" class="btn secondary btn-sm" @click="emit('close')">Schließen</button>
            </div>
          </div>

          <label class="notes-field">
            Notiz
            <textarea
              v-model="form.notes"
              rows="2"
              maxlength="2000"
              placeholder="Interne Notiz zur Buchung…"
            />
          </label>
          <div v-if="locked" class="notes-actions">
            <button
              type="button"
              class="btn btn-sm"
              :disabled="savingNotes || !notesDirty"
              @click="saveNotes"
            >
              Notiz speichern
            </button>
            <span v-if="notesSavedFlash" class="muted tiny">Gespeichert</span>
            <span v-if="notesError" class="error tiny">{{ notesError }}</span>
          </div>
          <p v-if="locked && canAmend" class="muted tiny">
            Laufende Buchung — für Änderungen ab einem Wirkdatum „Anpassen“ nutzen.
          </p>
          <p v-else-if="locked" class="muted tiny">Buchung beendet — nur noch Notizen änderbar.</p>

          <p v-if="loadingDetail" class="muted tiny">Lade Buchung…</p>

          <div v-else-if="pendingOverbook.length" class="warning-banner">
            <strong>Dienste wären überbucht</strong>
            <ul>
              <li v-for="(w, i) in pendingOverbook" :key="i">{{ w }}</li>
            </ul>
            <p class="muted">Möchten Sie die Buchung trotzdem speichern?</p>
            <div class="warning-actions">
              <button type="button" class="btn btn-sm" :disabled="saving" @click="confirmSaveAnyway">
                Buchung trotzdem speichern
              </button>
              <button type="button" class="btn secondary btn-sm" :disabled="saving" @click="backToPlanning">
                Zurück zur Planung
              </button>
            </div>
          </div>

          <form v-else class="grid-form compact-form" @submit.prevent="submit">
            <label>
              Gruppenname
              <input
                v-model.trim="form.group_name"
                required
                maxlength="200"
                :readonly="locked"
              />
            </label>

            <label>
              Reise-/Gruppenleiter (Stammdaten)
              <textarea
                v-model="form.group_leader"
                rows="3"
                maxlength="4000"
                :readonly="locked"
                placeholder="Name, Adresse, Kontaktdaten…"
              />
            </label>

            <div class="grid-2">
              <label>
                Anreise
                <input
                  v-model="form.start_date"
                  type="date"
                  required
                  :readonly="locked"
                  @change="onDatesChanged"
                />
              </label>
              <label>
                Abreise
                <input
                  v-model="form.end_date"
                  type="date"
                  required
                  :readonly="locked"
                  @change="onDatesChanged"
                />
              </label>
            </div>

            <div class="compact-section">
              <strong>Zeltplätze</strong>
              <template v-if="locked">
                <div v-if="pitchSegments.length" class="checkbox-list compact-checks">
                  <label v-for="seg in pitchSegments" :key="`${seg.pitch_id}-${seg.start_date}`" class="view-only-check">
                    <input type="checkbox" checked disabled />
                    {{ seg.pitch_name || `Platz #${seg.pitch_id}` }}
                    <span class="muted tiny">({{ seg.start_date }} – {{ seg.end_date }})</span>
                  </label>
                </div>
                <p v-else class="muted tiny">Keine Plätze</p>
              </template>
              <template v-else>
                <p v-if="!form.start_date || !form.end_date" class="muted tiny">Zeitraum wählen</p>
                <p v-else-if="loadingPitches" class="muted tiny">Lade…</p>
                <p v-else-if="availablePitches.length === 0" class="muted tiny">Keine freien Plätze</p>
                <div v-else class="checkbox-list compact-checks">
                  <label v-for="pitch in availablePitches" :key="pitch.id">
                    <input v-model="form.pitch_ids" type="checkbox" :value="pitch.id" />
                    {{ pitch.name }}
                  </label>
                </div>
              </template>
            </div>

            <div class="booking-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                class="tab-btn"
                :class="{ active: activeTab === 'persons' }"
                :aria-selected="activeTab === 'persons'"
                @click="activeTab = 'persons'"
              >
                Personen
              </button>
              <button
                type="button"
                role="tab"
                class="tab-btn"
                :class="{ active: activeTab === 'services' }"
                :aria-selected="activeTab === 'services'"
                @click="activeTab = 'services'"
              >
                Zusatzdienste
              </button>
            </div>

            <div v-show="activeTab === 'persons'" class="tab-panel compact-section" role="tabpanel">
              <div class="panel-header compact-header">
                <strong>Personen</strong>
                <div class="header-actions">
                  <button v-if="!locked" type="button" class="btn secondary btn-sm" @click="addPerson">
                    + Person
                  </button>
                </div>
              </div>
              <p v-if="!form.persons.length" class="muted tiny">
                {{ locked ? 'Keine Personen erfasst' : 'Optional — ohne Personen möglich' }}
              </p>
              <div v-if="form.persons.length" class="person-row person-row-header" aria-hidden="true">
                <span>Name</span>
                <span>Geburtsdatum</span>
                <span>Staatsangehörigkeit</span>
                <span>Preisprofil</span>
                <span>Anreise</span>
                <span>Abreise</span>
                <span class="person-row-actions-spacer"></span>
              </div>
              <div v-for="(person, index) in form.persons" :key="index" class="person-row person-row-compact">
                <input v-model.trim="person.name" placeholder="Name" aria-label="Name" :readonly="locked" />
                <input
                  v-model="person.birth_date"
                  type="date"
                  aria-label="Geburtsdatum"
                  title="Geburtsdatum"
                  :readonly="locked"
                />
                <select
                  v-model="person.nationality"
                  :disabled="locked"
                  aria-label="Staatsangehörigkeit"
                  title="Staatsangehörigkeit"
                >
                  <option v-for="c in countries" :key="c.code" :value="c.code">{{ c.code }}</option>
                </select>
                <select
                  v-model.number="person.price_profile_id"
                  :disabled="locked"
                  aria-label="Preisprofil"
                  title="Preisprofil"
                >
                  <option v-for="p in priceProfiles" :key="p.id" :value="p.id">{{ p.name }}</option>
                </select>
                <input
                  v-model="person.start_date"
                  type="date"
                  aria-label="Anreise"
                  title="Anreise"
                  :readonly="locked"
                />
                <input
                  v-model="person.end_date"
                  type="date"
                  aria-label="Abreise"
                  title="Abreise"
                  :readonly="locked"
                />
                <input
                  v-if="showTravelDocument(person)"
                  v-model.trim="person.travel_document"
                  placeholder="Reisedokument (Art, Nummer, Ausstellungsbehörde)"
                  aria-label="Reisedokument"
                  title="Reisedokument (Art, Nummer, Ausstellungsbehörde)"
                  :readonly="locked"
                  class="person-travel-doc"
                />
                <button
                  v-if="!locked"
                  type="button"
                  class="btn secondary btn-icon"
                  title="Entfernen"
                  @click="removePerson(index)"
                >
                  ×
                </button>
                <span v-else class="person-row-actions-spacer"></span>
              </div>
            </div>

            <div v-show="activeTab === 'services'" class="tab-panel compact-section" role="tabpanel">
              <template v-if="locked">
                <p v-if="!viewServices.length" class="muted tiny">Keine Zusatzdienste</p>
                <div v-else class="service-groups">
                  <div v-for="group in viewServiceGroups" :key="group.name" class="service-group">
                    <h3>{{ group.name }}</h3>
                    <div v-for="svc in group.items" :key="`${svc.service_id}-${svc.start_date}`" class="service-row">
                      <div class="service-meta">
                        <span class="service-name">{{ svc.service_name }}</span>
                        <span class="muted tiny">
                          {{ formatPrice(svc.daily_price) }}/Tag · {{ svc.start_date }} – {{ svc.end_date }}
                        </span>
                      </div>
                      <span class="qty-readonly">{{ svc.quantity }}</span>
                    </div>
                  </div>
                </div>
              </template>
              <template v-else>
                <p v-if="!form.start_date || !form.end_date" class="muted tiny">Zeitraum wählen</p>
                <p v-else-if="loadingServices" class="muted tiny">Lade…</p>
                <p v-else-if="!serviceGroups.length" class="muted tiny">Keine Dienste</p>
                <div v-else class="service-groups">
                  <div v-for="group in serviceGroups" :key="group.name" class="service-group">
                    <h3>{{ group.name }}</h3>
                    <div
                      v-for="svc in group.items"
                      :key="svc.service_id"
                      class="service-row"
                      :class="{ 'service-row-warn': quantityExceeds(svc) }"
                    >
                      <div class="service-meta">
                        <span class="service-name">{{ svc.name }}</span>
                        <span class="muted tiny">
                          frei {{ remainingFor(svc) }}/{{ svc.available_quantity }} ·
                          {{ formatPrice(svc.daily_price) }}/Tag
                        </span>
                      </div>
                      <label v-if="isBinaryService(svc)" class="service-check">
                        <input
                          type="checkbox"
                          :checked="Number(quantities[svc.service_id] || 0) === 1"
                          @change="setBinary(svc, $event.target.checked)"
                        />
                      </label>
                      <div v-else class="qty-stepper">
                        <button
                          type="button"
                          class="btn secondary btn-icon"
                          :disabled="Number(quantities[svc.service_id] || 0) <= 0"
                          @click="adjustQty(svc, -1)"
                        >
                          −
                        </button>
                        <input
                          class="qty-input"
                          :class="{ 'input-warn': quantityExceeds(svc) }"
                          type="number"
                          min="0"
                          inputmode="numeric"
                          :value="quantities[svc.service_id] ?? 0"
                          @input="onQtyInput(svc, $event)"
                        />
                        <button type="button" class="btn secondary btn-icon" @click="adjustQty(svc, 1)">
                          +
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <p v-if="error" class="error">{{ error }}</p>
            <p v-if="importHint" class="muted tiny">{{ importHint }}</p>
            <button v-if="!locked" class="btn" type="submit" :disabled="saving">
              {{ isExisting ? 'Änderungen speichern' : 'Buchung speichern' }}
            </button>
          </form>
        </div>

        <aside v-if="isExisting" class="booking-history">
          <h3>Änderungen</h3>
          <p v-if="!amendments.length" class="muted tiny">Noch keine Anpassungen.</p>
          <ul v-else class="history-list">
            <li v-for="item in amendments" :key="item.id" class="history-item">
              <div class="history-toggle">
                <strong>{{ item.effective_date }}</strong>
                <span class="muted tiny">{{ formatHistoryTime(item.created_at) }}</span>
                <ul class="history-changes">
                  <li v-for="(line, i) in historyLines(item)" :key="i">{{ line }}</li>
                </ul>
              </div>
            </li>
          </ul>
        </aside>
      </div>
    </div>

    <BookingAmendDialog
      v-if="amendDialogOpen"
      :open="amendDialogOpen"
      :booking-id="bookingId"
      @close="amendDialogOpen = false"
      @saved="onAmendSaved"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { api } from '../api'
import BookingAmendDialog from './BookingAmendDialog.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  bookingId: { type: [Number, String], default: null },
})
const emit = defineEmits(['close', 'saved'])

const isExisting = computed(() => props.bookingId != null && props.bookingId !== '')
const originalStartDate = ref('')
const originalEndDate = ref('')
const amendDialogOpen = ref(false)
const amendments = ref([])
const pitchSegments = ref([])
const importInput = ref(null)
const importing = ref(false)
const depositPaidAt = ref(null)
const togglingDeposit = ref(false)

function todayIso() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const locked = computed(
  () => isExisting.value && !!originalStartDate.value && todayIso() > originalStartDate.value,
)

const canAmend = computed(() => {
  if (!isExisting.value || !originalStartDate.value || !originalEndDate.value) return false
  const t = todayIso()
  return originalStartDate.value < t && t < originalEndDate.value
})

/** Import möglich für neue Buchungen und bestehende vor Anreise (nicht locked). */
const canImportGaesteblatt = computed(() => !locked.value)

const dialogTitle = computed(() => {
  if (!isExisting.value) return 'Neue Buchung'
  return locked.value ? 'Buchungsdetails' : 'Buchung bearbeiten'
})

const depositDue = computed(() => {
  let total = 0
  const pitchById = new Map(allPitches.value.map((p) => [p.id, p]))
  for (const p of availablePitches.value) {
    if (!pitchById.has(p.id)) pitchById.set(p.id, p)
  }
  const pitchIds = pitchSegments.value.length
    ? [...new Set(pitchSegments.value.map((s) => s.pitch_id))]
    : [...form.pitch_ids]
  for (const id of pitchIds) {
    total += Number(pitchById.get(id)?.deposit || 0)
  }

  const depositByService = new Map()
  for (const svc of availability.value) {
    depositByService.set(svc.service_id, Number(svc.deposit || 0))
  }
  for (const svc of viewServices.value) {
    if (!depositByService.has(svc.service_id)) {
      depositByService.set(svc.service_id, Number(svc.deposit || 0))
    }
  }
  const maxQty = new Map()
  for (const svc of viewServices.value) {
    maxQty.set(
      svc.service_id,
      Math.max(maxQty.get(svc.service_id) || 0, Number(svc.quantity || 0)),
    )
  }
  for (const [sid, qty] of Object.entries(quantities)) {
    const id = Number(sid)
    maxQty.set(id, Math.max(maxQty.get(id) || 0, Number(qty || 0)))
  }
  for (const [sid, qty] of maxQty.entries()) {
    if (qty > 0) total += (depositByService.get(sid) || 0) * qty
  }

  const seenProfiles = new Set()
  for (const person of form.persons) {
    const pid = person.price_profile_id
    if (!pid || seenProfiles.has(pid)) continue
    seenProfiles.add(pid)
    const profile = priceProfiles.value.find((p) => p.id === pid)
    total += Number(profile?.deposit || 0)
  }
  return Math.round(total * 100) / 100
})

const depositButtonLabel = computed(() => {
  const amount = new Intl.NumberFormat('de-AT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(depositDue.value)
  let label = `Fällige Kaution: ${amount} €`
  if (depositPaidAt.value) {
    const paid = new Date(depositPaidAt.value)
    const dateLabel = Number.isNaN(paid.getTime())
      ? ''
      : paid.toLocaleDateString('de-AT', { day: '2-digit', month: '2-digit', year: 'numeric' })
    if (dateLabel) label += ` — bezahlt am ${dateLabel}`
  }
  return label
})

async function toggleDeposit() {
  if (!isExisting.value || togglingDeposit.value) return
  togglingDeposit.value = true
  error.value = ''
  try {
    const result = await api.toggleBookingDeposit(props.bookingId)
    depositPaidAt.value = result.deposit_paid_at
  } catch (e) {
    error.value = e.message
  } finally {
    togglingDeposit.value = false
  }
}

const countries = ref([])
const homeCountry = ref('AT')
const priceProfiles = ref([])
const allPitches = ref([])
const availablePitches = ref([])
const availability = ref([])
const quantities = reactive({})
const viewServices = ref([])
const loadingPitches = ref(false)
const loadingServices = ref(false)
const loadingDetail = ref(false)
const saving = ref(false)
const savingNotes = ref(false)
const notesSavedFlash = ref(false)
const notesError = ref('')
const savedNotes = ref('')
const error = ref('')
const importWarnings = ref([])
const importHint = ref('')
const pendingOverbook = ref([])
const activeTab = ref('persons')
const previousBookingStart = ref('')
const previousBookingEnd = ref('')

const form = reactive({
  group_name: '',
  group_leader: '',
  start_date: '',
  end_date: '',
  pitch_ids: [],
  notes: '',
  persons: [],
})

const notesDirty = computed(() => (form.notes || '') !== (savedNotes.value || ''))

const viewServiceGroups = computed(() => {
  const map = new Map()
  for (const svc of viewServices.value) {
    const groupName = svc.group_name || 'Sonstiges'
    if (!map.has(groupName)) map.set(groupName, [])
    map.get(groupName).push(svc)
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b, 'de'))
    .map(([name, items]) => ({ name, items }))
})

const serviceGroups = computed(() => {
  const map = new Map()
  for (const svc of availability.value) {
    if (!map.has(svc.group_name)) map.set(svc.group_name, [])
    map.get(svc.group_name).push(svc)
  }
  return [...map.entries()]
    .sort(([a], [b]) => a.localeCompare(b, 'de'))
    .map(([name, items]) => ({
      name,
      items: items.sort((x, y) => x.name.localeCompare(y.name, 'de')),
    }))
})

function isBinaryService(svc) {
  return Number(svc.available_quantity) === 1
}

function formatPrice(value) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(Number(value || 0))
}

function remainingFor(svc) {
  return svc.remaining
}

function quantityExceeds(svc) {
  const qty = Number(quantities[svc.service_id] || 0)
  return qty > 0 && qty > svc.remaining
}

function setBinary(svc, checked) {
  quantities[svc.service_id] = checked ? 1 : 0
}

function adjustQty(svc, delta) {
  quantities[svc.service_id] = Math.max(0, Number(quantities[svc.service_id] || 0) + delta)
}

function onQtyInput(svc, event) {
  const raw = event.target.value
  if (raw === '') {
    quantities[svc.service_id] = 0
    return
  }
  const value = Number(raw)
  quantities[svc.service_id] = Number.isFinite(value) && value >= 0 ? Math.floor(value) : 0
}

function formatHistoryTime(iso) {
  try {
    return new Date(iso).toLocaleString('de-AT', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

function historyLines(item) {
  try {
    const diff = JSON.parse(item.diff_json || '{}')
    if (Array.isArray(diff.changes) && diff.changes.length) return diff.changes
  } catch {
    /* ignore */
  }
  return item.summary ? item.summary.split(' · ') : []
}

function reset() {
  form.group_name = ''
  form.group_leader = ''
  form.start_date = ''
  form.end_date = ''
  form.pitch_ids = []
  form.notes = ''
  form.persons = []
  originalStartDate.value = ''
  originalEndDate.value = ''
  previousBookingStart.value = ''
  previousBookingEnd.value = ''
  amendDialogOpen.value = false
  amendments.value = []
  pitchSegments.value = []
  depositPaidAt.value = null
  togglingDeposit.value = false
  availablePitches.value = []
  availability.value = []
  viewServices.value = []
  Object.keys(quantities).forEach((k) => delete quantities[k])
  error.value = ''
  importWarnings.value = []
  importHint.value = ''
  pendingOverbook.value = []
  activeTab.value = 'persons'
  loadingDetail.value = false
  savedNotes.value = ''
  notesError.value = ''
  notesSavedFlash.value = false
}

function showTravelDocument(person) {
  return (person?.nationality || '').toUpperCase() !== (homeCountry.value || 'AT').toUpperCase()
}

function normalizePersonKey(name, birthDate) {
  const n = String(name || '')
    .normalize('NFKC')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
  const b = String(birthDate || '').trim()
  return `${n}|${b}`
}

function mapImportedPerson(p, fallbackStart, fallbackEnd) {
  return {
    name: p.name || '',
    birth_date: p.birth_date || '',
    nationality: p.nationality || homeCountry.value || 'AT',
    travel_document: p.travel_document || '',
    price_profile_id: defaultPriceProfileId(),
    start_date: p.start_date || fallbackStart || form.start_date || '',
    end_date: p.end_date || fallbackEnd || form.end_date || '',
  }
}

/** Neue Buchung: Kopf + Personen aus Gästeblatt übernehmen. */
function applyFullImport(draft) {
  if (!draft) return
  if (draft.group_name) form.group_name = draft.group_name
  if (draft.group_leader) form.group_leader = draft.group_leader
  if (draft.start_date) form.start_date = draft.start_date
  if (draft.end_date) form.end_date = draft.end_date
  form.persons = (draft.persons || []).map((p) =>
    mapImportedPerson(p, draft.start_date, draft.end_date),
  )
  previousBookingStart.value = form.start_date
  previousBookingEnd.value = form.end_date
}

/**
 * Bestehende Buchung vor Anreise: nur Personen mergen.
 * Abgleich über Name + Geburtsdatum; nur neue Datensätze hinzufügen.
 */
function mergeImportedPersons(draft) {
  const existingKeys = new Set(
    form.persons.map((p) => normalizePersonKey(p.name, p.birth_date)),
  )
  let added = 0
  let skipped = 0
  for (const raw of draft.persons || []) {
    const person = mapImportedPerson(raw, form.start_date, form.end_date)
    const key = normalizePersonKey(person.name, person.birth_date)
    if (!person.name || !person.birth_date) {
      skipped += 1
      continue
    }
    if (existingKeys.has(key)) {
      skipped += 1
      continue
    }
    form.persons.push(person)
    existingKeys.add(key)
    added += 1
  }
  return { added, skipped }
}

function triggerImport() {
  if (!canImportGaesteblatt.value) return
  importInput.value?.click()
}

async function onImportFile(event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  importing.value = true
  error.value = ''
  importHint.value = ''
  importWarnings.value = []
  // #region agent log
  fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'ad5dd0'},body:JSON.stringify({sessionId:'ad5dd0',runId:'repro',hypothesisId:'D',location:'BookingForm.vue:onImportFile:start',message:'import started',data:{fileName:file.name,fileSize:file.size,isExisting:isExisting.value},timestamp:Date.now()})}).catch(()=>{})
  // #endregion
  try {
    const draft = await api.parseGaesteblatt(file)
    // #region agent log
    fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'ad5dd0'},body:JSON.stringify({sessionId:'ad5dd0',runId:'repro',hypothesisId:'D',location:'BookingForm.vue:onImportFile:parsed',message:'parse response received',data:{group:draft?.group_name,persons:(draft?.persons||[]).length,start:draft?.start_date,end:draft?.end_date},timestamp:Date.now()})}).catch(()=>{})
    // #endregion
    const parseWarnings = draft.warnings || []
    if (isExisting.value) {
      const { added, skipped } = mergeImportedPersons(draft)
      activeTab.value = 'persons'
      const hints = [
        added
          ? `${added} Person(en) neu importiert.`
          : 'Keine neuen Personen zum Import gefunden.',
      ]
      if (skipped && added) {
        hints.push(`${skipped} bereits vorhandene/unvollständige Einträge übersprungen.`)
      }
      importHint.value = hints.join(' ')
      if (parseWarnings.length) {
        error.value = parseWarnings.join(' ')
      }
    } else {
      applyFullImport(draft)
      activeTab.value = 'persons'
      importHint.value = `${(draft.persons || []).length} Person(en) aus Gästeblatt übernommen.`
      if (parseWarnings.length) {
        error.value = parseWarnings.join(' ')
      }
      if (form.start_date && form.end_date) {
        // #region agent log
        fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'ad5dd0'},body:JSON.stringify({sessionId:'ad5dd0',runId:'repro',hypothesisId:'E',location:'BookingForm.vue:onImportFile:reload',message:'reloading pitches/services',data:{start:form.start_date,end:form.end_date},timestamp:Date.now()})}).catch(()=>{})
        // #endregion
        await Promise.all([
          reloadPitches({ clearSelection: true }),
          reloadServices(),
        ])
      }
    }
    // #region agent log
    fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'ad5dd0'},body:JSON.stringify({sessionId:'ad5dd0',runId:'repro',hypothesisId:'E',location:'BookingForm.vue:onImportFile:done',message:'import finished ok',data:{},timestamp:Date.now()})}).catch(()=>{})
    // #endregion
  } catch (e) {
    // #region agent log
    fetch('http://127.0.0.1:7445/ingest/e7a5a80c-ec6a-4fcb-9858-1b2fce84a5b6',{method:'POST',headers:{'Content-Type':'application/json','X-Debug-Session-Id':'ad5dd0'},body:JSON.stringify({sessionId:'ad5dd0',runId:'repro',hypothesisId:'D',location:'BookingForm.vue:onImportFile:catch',message:'import failed',data:{error:String(e?.message||e)},timestamp:Date.now()})}).catch(()=>{})
    // #endregion
    error.value = e.message
  } finally {
    importing.value = false
  }
}

function applyBookingToForm(booking) {
  form.group_name = booking.group_name
  form.group_leader = booking.group_leader || ''
  form.start_date = booking.start_date
  form.end_date = booking.end_date
  originalStartDate.value = booking.start_date
  originalEndDate.value = booking.end_date
  form.pitch_ids = [...(booking.pitch_ids || [])]
  form.notes = booking.notes || ''
  savedNotes.value = form.notes
  form.persons = (booking.persons || []).map((p) => ({
    name: p.name,
    birth_date: p.birth_date,
    nationality: p.nationality,
    travel_document: p.travel_document || '',
    price_profile_id: p.price_profile_id ?? defaultPriceProfileId(),
    start_date: p.start_date || booking.start_date,
    end_date: p.end_date || booking.end_date,
  }))
  previousBookingStart.value = booking.start_date
  previousBookingEnd.value = booking.end_date
  viewServices.value = booking.services || []
  pitchSegments.value = booking.pitch_segments || []
  amendments.value = booking.amendments || []
  depositPaidAt.value = booking.deposit_paid_at || null
  Object.keys(quantities).forEach((k) => delete quantities[k])
  const qtyByService = {}
  for (const svc of booking.services || []) {
    if (svc.end_date === booking.end_date || (svc.start_date <= todayIso() && todayIso() < svc.end_date)) {
      qtyByService[svc.service_id] = svc.quantity
    }
  }
  for (const [id, qty] of Object.entries(qtyByService)) {
    quantities[id] = qty
  }
  if (!Object.keys(qtyByService).length) {
    for (const svc of booking.services || []) {
      quantities[svc.service_id] = svc.quantity
    }
  }
}

async function onAmendSaved() {
  amendDialogOpen.value = false
  emit('saved')
  await loadBookingDetail()
}

async function loadBookingDetail() {
  loadingDetail.value = true
  error.value = ''
  try {
    const [booking, pitches] = await Promise.all([
      api.getBooking(props.bookingId),
      allPitches.value.length ? Promise.resolve(allPitches.value) : api.listPitches(),
    ])
    allPitches.value = pitches
    applyBookingToForm(booking)
    if (!(todayIso() > booking.start_date)) {
      await Promise.all([
        reloadPitches({ clearSelection: false }),
        reloadServices(),
      ])
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loadingDetail.value = false
  }
}

watch(
  () => [props.open, props.bookingId],
  async ([isOpen]) => {
    if (!isOpen) return
    reset()
    if (isExisting.value) await loadBookingDetail()
  },
)

onMounted(async () => {
  const [meta, profiles] = await Promise.all([api.getMeta(), api.listPriceProfiles()])
  countries.value = meta.countries || []
  homeCountry.value = meta.home_country || 'AT'
  priceProfiles.value = profiles
})

async function saveNotes() {
  if (!locked.value || !notesDirty.value) return
  savingNotes.value = true
  notesError.value = ''
  notesSavedFlash.value = false
  try {
    await api.updateBooking(props.bookingId, { notes: form.notes || '' })
    savedNotes.value = form.notes || ''
    notesSavedFlash.value = true
    emit('saved')
    setTimeout(() => {
      notesSavedFlash.value = false
    }, 1500)
  } catch (e) {
    notesError.value = e.message
  } finally {
    savingNotes.value = false
  }
}

async function onDatesChanged() {
  if (locked.value) return
  syncPersonDatesFromBooking()
  await Promise.all([reloadPitches({ clearSelection: true }), reloadServices()])
}

function syncPersonDatesFromBooking() {
  const prevStart = previousBookingStart.value
  const prevEnd = previousBookingEnd.value
  for (const person of form.persons) {
    if (!person.start_date || person.start_date === prevStart) person.start_date = form.start_date
    if (!person.end_date || person.end_date === prevEnd) person.end_date = form.end_date
  }
  previousBookingStart.value = form.start_date
  previousBookingEnd.value = form.end_date
}

async function reloadPitches({ clearSelection = true } = {}) {
  availablePitches.value = []
  if (clearSelection) form.pitch_ids = []
  if (!form.start_date || !form.end_date) return
  loadingPitches.value = true
  error.value = ''
  try {
    const excludeId = isExisting.value ? props.bookingId : null
    availablePitches.value = await api.availablePitches(form.start_date, form.end_date, excludeId)
    if (!clearSelection) {
      const availableIds = new Set(availablePitches.value.map((p) => p.id))
      form.pitch_ids = form.pitch_ids.filter((id) => availableIds.has(id))
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loadingPitches.value = false
  }
}

async function reloadServices() {
  availability.value = []
  if (!form.start_date || !form.end_date) return
  loadingServices.value = true
  try {
    const excludeId = isExisting.value ? props.bookingId : null
    availability.value = await api.servicesAvailability(form.start_date, form.end_date, excludeId)
    for (const svc of availability.value) {
      if (quantities[svc.service_id] == null) quantities[svc.service_id] = 0
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loadingServices.value = false
  }
}

function defaultPriceProfileId() {
  const def = priceProfiles.value.find((p) => p.is_default)
  return def?.id ?? priceProfiles.value[0]?.id ?? null
}

function addPerson() {
  form.persons.push({
    name: '',
    birth_date: '',
    nationality: homeCountry.value || 'AT',
    travel_document: '',
    price_profile_id: defaultPriceProfileId(),
    start_date: form.start_date || '',
    end_date: form.end_date || '',
  })
}

function removePerson(index) {
  form.persons.splice(index, 1)
}

function selectedServices() {
  return Object.entries(quantities)
    .map(([service_id, quantity]) => ({
      service_id: Number(service_id),
      quantity: Number(quantity) || 0,
    }))
    .filter((s) => s.quantity > 0)
}

function buildOverbookWarnings() {
  const warnings = []
  for (const svc of availability.value) {
    const qty = Number(quantities[svc.service_id] || 0)
    if (qty <= 0) continue
    if (qty > svc.remaining) {
      warnings.push(
        `${svc.name}: Bedarf ${svc.used + qty}, Bestand ${svc.available_quantity} (bereits verplant ${svc.used})`,
      )
    }
  }
  return warnings
}

function backToPlanning() {
  pendingOverbook.value = []
  activeTab.value = 'services'
  error.value = ''
}

async function confirmSaveAnyway() {
  await saveBooking()
}

async function saveBooking() {
  saving.value = true
  error.value = ''
  try {
    if (isExisting.value) {
      await api.updateBooking(props.bookingId, {
        group_name: form.group_name,
        group_leader: form.group_leader || '',
        start_date: form.start_date,
        end_date: form.end_date,
        pitch_ids: form.pitch_ids,
        persons: form.persons,
        services: selectedServices(),
        notes: form.notes || '',
      })
    } else {
      await api.createBooking({
        group_name: form.group_name,
        group_leader: form.group_leader || '',
        start_date: form.start_date,
        end_date: form.end_date,
        pitch_ids: form.pitch_ids,
        persons: form.persons,
        services: selectedServices(),
        notes: form.notes || '',
      })
    }
    pendingOverbook.value = []
    emit('saved')
    emit('close')
  } catch (e) {
    error.value = e.message
    pendingOverbook.value = []
    activeTab.value = 'services'
  } finally {
    saving.value = false
  }
}

async function submit() {
  if (locked.value) return
  error.value = ''
  if (form.pitch_ids.length === 0) {
    error.value = 'Bitte mindestens einen Zeltplatz wählen.'
    return
  }
  if (form.persons.length) {
    const incomplete = form.persons.some(
      (p) =>
        !p.name?.trim() ||
        !p.birth_date ||
        !p.nationality ||
        !p.price_profile_id ||
        !p.start_date ||
        !p.end_date,
    )
    if (incomplete) {
      activeTab.value = 'persons'
      error.value = 'Bitte alle Personenangaben vollständig ausfüllen.'
      return
    }
  }

  const overbook = buildOverbookWarnings()
  if (overbook.length) {
    pendingOverbook.value = overbook
    return
  }

  await saveBooking()
}
</script>
