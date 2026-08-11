<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h1>Kalender pro Zeltplatz</h1>
        <p class="muted">Belegungen eines einzelnen Platzes</p>
      </div>
      <button class="btn" type="button" @click="openNewBooking">Neue Buchung</button>
    </div>

    <div class="calendar-toolbar">
      <label style="min-width: 220px">
        Zeltplatz
        <select v-model="selectedPitchId" @change="loadEvents">
          <option disabled value="">Bitte wählen</option>
          <option v-for="p in pitches" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
        </select>
      </label>
    </div>

    <p v-if="error" class="error">{{ error }}</p>
    <FullCalendar
      v-if="selectedPitchId"
      :key="`cal-${selectedPitchId}`"
      :options="calendarOptions"
    />
    <p v-else class="muted">Bitte einen Zeltplatz auswählen.</p>
  </section>

  <BookingForm
    :open="showForm"
    :booking-id="selectedBookingId"
    @close="closeForm"
    @saved="onSaved"
  />
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import FullCalendar from '@fullcalendar/vue3'
import dayGridPlugin from '@fullcalendar/daygrid'
import interactionPlugin from '@fullcalendar/interaction'
import deLocale from '@fullcalendar/core/locales/de'
import { api } from '../api'
import BookingForm from '../components/BookingForm.vue'

const pitches = ref([])
const selectedPitchId = ref('')
const events = ref([])
const error = ref('')
const showForm = ref(false)
const selectedBookingId = ref(null)

const calendarOptions = computed(() => ({
  plugins: [dayGridPlugin, interactionPlugin],
  initialView: 'dayGridMonth',
  initialDate: new Date(),
  locale: deLocale,
  height: 'auto',
  headerToolbar: {
    left: 'prev,next today',
    center: 'title',
    right: 'dayGridMonth,dayGridWeek',
  },
  events: events.value,
  eventClick: (info) => {
    openBooking(Number(info.event.id))
  },
}))

function openNewBooking() {
  selectedBookingId.value = null
  showForm.value = true
}

function openBooking(bookingId) {
  selectedBookingId.value = bookingId
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  selectedBookingId.value = null
}

async function loadPitches() {
  pitches.value = await api.listPitches()
  if (!selectedPitchId.value && pitches.value.length) {
    selectedPitchId.value = String(pitches.value[0].id)
    await loadEvents()
  }
}

async function loadEvents() {
  error.value = ''
  events.value = []
  if (!selectedPitchId.value) return
  try {
    const bookings = await api.pitchBookings(selectedPitchId.value)
    events.value = bookings.map((b) => ({
      id: String(b.id),
      title: b.group_name,
      start: b.start_date,
      end: b.end_date,
      allDay: true,
    }))
  } catch (e) {
    error.value = e.message
  }
}

async function onSaved() {
  await loadPitches()
  await loadEvents()
}

onMounted(async () => {
  try {
    await loadPitches()
  } catch (e) {
    error.value = e.message
  }
})
</script>
