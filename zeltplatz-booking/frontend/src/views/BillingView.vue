<template>
  <section class="panel">
    <div class="panel-header">
      <div>
        <h1>Abrechnung</h1>
        <p class="muted">Buchungen mit Summe und Rechnungs-PDF</p>
      </div>
    </div>

    <div class="grid-2" style="margin-bottom: 1rem">
      <label>
        Von
        <input v-model="fromDate" type="date" @change="loadList" />
      </label>
      <label>
        Bis
        <input v-model="toDate" type="date" @change="loadList" />
      </label>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <table class="table">
      <thead>
        <tr>
          <th>Gruppe</th>
          <th>Zeitraum</th>
          <th>Nächte</th>
          <th>Summe</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.booking_id">
          <td>{{ item.group_name }}</td>
          <td>{{ item.start_date }} – {{ item.end_date }}</td>
          <td>{{ item.nights }}</td>
          <td>{{ formatPrice(item.total) }}</td>
          <td style="display: flex; gap: 0.4rem; justify-content: flex-end">
            <button class="btn secondary" type="button" @click="openDetail(item.booking_id)">Details</button>
            <a class="btn" :href="pdfUrl(item.booking_id)" target="_blank" rel="noopener">PDF</a>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-if="!items.length" class="muted">Keine Buchungen im Zeitraum.</p>
  </section>

  <div v-if="invoice" class="modal-backdrop" @click.self="invoice = null">
    <div class="modal modal-compact" role="dialog">
      <div class="panel-header compact-header">
        <h2>Rechnung — {{ invoice.group_name }}</h2>
        <button type="button" class="btn secondary btn-sm" @click="invoice = null">Schließen</button>
      </div>

      <div v-if="hasOperatorHeader" class="invoice-letterhead">
        <img
          v-if="invoice.operator.has_logo"
          class="invoice-logo"
          :src="operatorLogoSrc"
          alt="Logo"
        />
        <div class="invoice-letterhead-text">
          <strong v-if="invoice.operator.organization_name">{{ invoice.operator.organization_name }}</strong>
          <pre v-if="invoice.operator.address" class="invoice-address">{{ invoice.operator.address }}</pre>
        </div>
      </div>

      <p class="muted tiny">
        {{ invoice.start_date }} – {{ invoice.end_date }} · {{ invoice.nights }} Nächte
      </p>
      <table class="table invoice-table">
        <thead>
          <tr>
            <th>Position</th>
            <th>Menge</th>
            <th>Tagespreis</th>
            <th>Zeitraum</th>
            <th>Nächte</th>
            <th>Betrag</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="group in invoiceGroups" :key="group.key">
            <tr class="invoice-group-header">
              <td colspan="6">{{ group.title }}</td>
            </tr>
            <tr v-for="(line, idx) in group.lines" :key="`${group.key}-${idx}`">
              <td>{{ line.label }}</td>
              <td>{{ line.quantity }}</td>
              <td>{{ formatPrice(line.unit_price) }}</td>
              <td>
                <span v-if="line.start_date && line.end_date">
                  {{ line.start_date }} – {{ line.end_date }}
                </span>
              </td>
              <td>{{ line.nights }}</td>
              <td>{{ formatPrice(line.amount) }}</td>
            </tr>
            <tr class="invoice-subtotal">
              <td colspan="5">Zwischensumme {{ group.title }}</td>
              <td>{{ formatPrice(group.subtotal) }}</td>
            </tr>
          </template>
        </tbody>
      </table>
      <p v-if="!invoice.lines.length" class="muted">Keine verrechenbaren Positionen (alle 0 €).</p>
      <div class="panel-header">
        <strong>Summe: {{ formatPrice(invoice.total) }}</strong>
        <a class="btn" :href="pdfUrl(invoice.booking_id)" target="_blank" rel="noopener">PDF exportieren</a>
      </div>
      <footer v-if="hasOperatorFooter" class="invoice-footer">
        <span v-if="invoice.operator.organization_name">{{ invoice.operator.organization_name }}</span>
        <span v-if="invoice.operator.address">{{ footerAddress }}</span>
        <span v-if="invoice.operator.iban">IBAN: {{ invoice.operator.iban }}</span>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'

const GROUP_ORDER = [
  { key: 'pitch', title: 'Zeltplätze' },
  { key: 'person', title: 'Personen' },
  { key: 'service', title: 'Zusatzdienste' },
]

const items = ref([])
const invoice = ref(null)
const error = ref('')
const year = new Date().getFullYear()
const fromDate = ref(`${year}-01-01`)
const toDate = ref(`${year}-12-31`)

const invoiceGroups = computed(() => {
  const lines = invoice.value?.lines || []
  return GROUP_ORDER.map(({ key, title }) => {
    const groupLines = lines.filter((l) => l.category === key)
    if (!groupLines.length) return null
    const subtotal = groupLines.reduce((sum, l) => sum + Number(l.amount || 0), 0)
    return { key, title, lines: groupLines, subtotal }
  }).filter(Boolean)
})

const hasOperatorHeader = computed(() => {
  const op = invoice.value?.operator
  if (!op) return false
  return Boolean(op.has_logo || op.organization_name || op.address)
})

const hasOperatorFooter = computed(() => {
  const op = invoice.value?.operator
  if (!op) return false
  return Boolean(op.organization_name || op.address || op.iban)
})

const footerAddress = computed(() =>
  (invoice.value?.operator?.address || '').split(/\r?\n/).map((s) => s.trim()).filter(Boolean).join(' · '),
)

const operatorLogoSrc = computed(() =>
  invoice.value?.operator?.has_logo
    ? `${api.operatorLogoUrl()}?booking=${invoice.value.booking_id}`
    : '',
)

function formatPrice(value) {
  return new Intl.NumberFormat('de-AT', { style: 'currency', currency: 'EUR' }).format(Number(value || 0))
}

function pdfUrl(id) {
  return `/api/v1/bookings/${id}/invoice.pdf`
}

async function loadList() {
  error.value = ''
  try {
    items.value = await api.listBilling(fromDate.value, toDate.value)
  } catch (e) {
    error.value = e.message
    items.value = []
  }
}

async function openDetail(id) {
  error.value = ''
  try {
    invoice.value = await api.getInvoice(id)
  } catch (e) {
    error.value = e.message
  }
}

onMounted(loadList)
</script>
