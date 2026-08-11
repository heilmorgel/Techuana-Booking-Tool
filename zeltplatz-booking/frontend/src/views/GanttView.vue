<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h1>Belegungsplan (Gantt)</h1>
        <p class="muted">Buchungen aller Zeltplätze im Überblick</p>
      </div>
      <button class="btn" type="button" @click="openNewBooking">Neue Buchung</button>
    </div>

    <div class="grid-2" style="margin-bottom: 1rem">
      <label>
        Von
        <input v-model="fromDate" type="date" @change="load" />
      </label>
      <label>
        Bis
        <input v-model="toDate" type="date" @change="load" />
      </label>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-else-if="!rows.length" class="muted">Noch keine Buchungen im gewählten Zeitraum.</p>

    <div v-else class="gantt-wrap">
      <div class="gantt-chart" :style="{ minWidth: `${labelWidth + days.length * dayWidth}px` }">
        <div class="gantt-header">
          <div class="gantt-label-col" :style="{ width: `${labelWidth}px` }">Platz</div>
          <div class="gantt-days">
            <div
              v-for="day in days"
              :key="day.key"
              class="gantt-day"
              :class="{ weekend: day.weekend, today: day.today }"
              :style="{ width: `${dayWidth}px` }"
              :title="day.label"
            >
              <span>{{ day.short }}</span>
            </div>
          </div>
        </div>

        <div v-for="row in rows" :key="row.pitchId" class="gantt-row">
          <div class="gantt-label-col" :style="{ width: `${labelWidth}px` }">{{ row.pitchName }}</div>
          <div class="gantt-track" :style="{ width: `${days.length * dayWidth}px` }">
            <div
              v-for="day in days"
              :key="`${row.pitchId}-${day.key}`"
              class="gantt-cell"
              :class="{ weekend: day.weekend, today: day.today }"
              :style="{ width: `${dayWidth}px` }"
            />
            <div
              v-for="bar in row.bars"
              :key="bar.id"
              class="gantt-bar"
              :style="barStyle(bar)"
              :title="`${bar.groupName}: ${bar.start} – ${bar.end}`"
              @click="openBooking(bar.bookingId)"
            >
              {{ bar.groupName }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <BookingForm
    :open="showForm"
    :booking-id="selectedBookingId"
    @close="closeForm"
    @saved="load"
  />
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import BookingForm from '../components/BookingForm.vue'

const showForm = ref(false)
const selectedBookingId = ref(null)
const error = ref('')
const items = ref([])
const labelWidth = 140
const dayWidth = 28

function parseDate(value) {
  const [y, m, d] = value.split('-').map(Number)
  return new Date(y, m - 1, d)
}

function formatDate(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function addDays(date, days) {
  const next = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  next.setDate(next.getDate() + days)
  return next
}

const today = new Date()
const fromDate = ref(formatDate(addDays(today, -5)))
const toDate = ref(formatDate(addDays(today, 20)))

const rangeStart = computed(() => parseDate(fromDate.value))
const rangeEnd = computed(() => parseDate(toDate.value))

const todayKey = formatDate(new Date())

const days = computed(() => {
  const result = []
  const cursor = new Date(rangeStart.value)
  const end = rangeEnd.value
  // "Bis"-Datum inklusive anzeigen (heute-5 … heute+20)
  while (cursor <= end) {
    const key = formatDate(cursor)
    const weekend = cursor.getDay() === 0 || cursor.getDay() === 6
    result.push({
      key,
      weekend,
      today: key === todayKey,
      label: key,
      short: String(cursor.getDate()),
    })
    cursor.setDate(cursor.getDate() + 1)
  }
  return result
})

const rows = computed(() => {
  const byPitch = new Map()
  for (const item of items.value) {
    if (!byPitch.has(item.pitch_id)) {
      byPitch.set(item.pitch_id, {
        pitchId: item.pitch_id,
        pitchName: item.pitch_name,
        bars: [],
      })
    }
    byPitch.get(item.pitch_id).bars.push({
      id: `${item.id}-${item.pitch_id}`,
      bookingId: item.id,
      groupName: item.group_name,
      start: item.start_date,
      end: item.end_date,
    })
  }
  return [...byPitch.values()].sort((a, b) => a.pitchName.localeCompare(b.pitchName, 'de'))
})

function openBooking(bookingId) {
  selectedBookingId.value = bookingId
  showForm.value = true
}

function openNewBooking() {
  selectedBookingId.value = null
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  selectedBookingId.value = null
}

function dayOffset(dateStr) {
  const start = rangeStart.value
  const date = parseDate(dateStr)
  return Math.round((date - start) / 86400000)
}

function barStyle(bar) {
  const startOffset = Math.max(0, dayOffset(bar.start))
  const endOffset = Math.min(days.value.length, dayOffset(bar.end))
  const widthDays = Math.max(endOffset - startOffset, 1)
  return {
    left: `${startOffset * dayWidth}px`,
    width: `${widthDays * dayWidth - 4}px`,
  }
}

async function load() {
  error.value = ''
  try {
    // API filtert halb-offen [from, to); Anzeige-Ende ist inklusiv → +1 Tag
    const apiTo = formatDate(addDays(parseDate(toDate.value), 1))
    items.value = await api.gantt(fromDate.value, apiTo)
  } catch (e) {
    error.value = e.message
    items.value = []
  }
}

onMounted(load)
</script>
