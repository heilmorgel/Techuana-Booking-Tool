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
          <th>Rechnungsnr.</th>
          <th>Gruppe</th>
          <th>Zeitraum</th>
          <th>Nächte</th>
          <th>Summe</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.booking_id">
          <td>{{ item.invoice_number || '—' }}</td>
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

  <div v-if="invoice" class="modal-backdrop" @click.self="closeDetail">
    <div class="modal modal-compact" role="dialog">
      <div class="panel-header compact-header">
        <h2>Rechnung — {{ invoice.group_name }}</h2>
        <button type="button" class="btn secondary btn-sm" @click="closeDetail">Schließen</button>
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
        <span v-if="invoice.invoice_number">Rechnungsnr. {{ invoice.invoice_number }} · </span>
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
            <th></th>
          </tr>
        </thead>
        <tbody>
          <template v-for="group in invoiceGroups" :key="group.key">
            <tr class="invoice-group-header">
              <td colspan="7">{{ group.title }}</td>
            </tr>
            <tr v-for="(line, idx) in group.lines" :key="`${group.key}-${line.id ?? idx}`">
              <td>{{ line.label }}</td>
              <td>{{ line.category === 'custom' || line.category === 'deposit' ? '—' : line.quantity }}</td>
              <td>{{ line.category === 'custom' || line.category === 'deposit' ? '—' : formatPrice(line.unit_price) }}</td>
              <td>
                <span v-if="line.start_date && line.end_date">
                  {{ formatPeriod(line.start_date, line.end_date) }}
                </span>
              </td>
              <td>{{ line.category === 'custom' || line.category === 'deposit' ? '—' : line.nights }}</td>
              <td>{{ formatPrice(line.amount) }}</td>
              <td>
                <button
                  v-if="line.category === 'custom' && line.id != null"
                  type="button"
                  class="btn secondary btn-sm"
                  :disabled="savingCustom"
                  @click="removeCustomLine(line.id)"
                >
                  Entfernen
                </button>
              </td>
            </tr>
            <tr class="invoice-subtotal">
              <td colspan="5">Zwischensumme {{ group.title }}</td>
              <td>{{ formatPrice(group.subtotal) }}</td>
              <td></td>
            </tr>
          </template>
        </tbody>
      </table>
      <p v-if="!invoice.lines.length" class="muted">Keine verrechenbaren Positionen (alle 0 €).</p>

      <div class="custom-line-form">
        <h3 class="tiny" style="margin: 0.75rem 0 0.4rem">Sonstige Position</h3>
        <p class="muted tiny" style="margin-top: 0">
          Zusatzkosten (positiv), Rabatte (negativ) oder Notiz (0 € — nur dann erscheint eine 0-Position).
        </p>
        <div class="grid-2" style="align-items: end; gap: 0.5rem">
          <label>
            Bezeichnung
            <input v-model="customLabel" type="text" maxlength="500" placeholder="z. B. Sonderrabatt" />
          </label>
          <label>
            Betrag (€)
            <input v-model.number="customAmount" type="number" step="0.01" />
          </label>
        </div>
        <div style="margin-top: 0.5rem">
          <button
            type="button"
            class="btn secondary"
            :disabled="savingCustom || !customLabel.trim()"
            @click="addCustomLine"
          >
            Position hinzufügen
          </button>
          <span v-if="customError" class="error" style="margin-left: 0.75rem">{{ customError }}</span>
        </div>
      </div>

      <div class="panel-header">
        <strong>Summe: {{ formatPrice(invoice.total) }}</strong>
        <a class="btn" :href="pdfUrl(invoice.booking_id)" target="_blank" rel="noopener">PDF exportieren</a>
      </div>
      <div class="invoice-signatures">
        <div class="invoice-signature">
          <div class="invoice-signature-line" aria-hidden="true"></div>
          <span>Bestätigung Gruppenleiter</span>
        </div>
        <div class="invoice-signature">
          <div class="invoice-signature-line" aria-hidden="true"></div>
          <span>Unterschrift Quartermaster</span>
        </div>
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
import { api, apiBasePath } from '../api'

const GROUP_ORDER = [
  { key: 'pitch', title: 'Zeltplätze' },
  { key: 'person', title: 'Personen' },
  { key: 'service', title: 'Zusatzdienste' },
  { key: 'deposit', title: 'Kaution' },
  { key: 'custom', title: 'Sonstige Positionen' },
]

const items = ref([])
const invoice = ref(null)
const error = ref('')
const customLabel = ref('')
const customAmount = ref(0)
const customError = ref('')
const savingCustom = ref(false)
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

/** Day+month only — year is shown in the invoice header. */
function formatPeriod(start, end) {
  const fmt = (iso) => {
    const [, m, d] = String(iso).split('-')
    return `${d}.${m}.`
  }
  return `${fmt(start)} – ${fmt(end)}`
}

function pdfUrl(id) {
  return `${apiBasePath()}/bookings/${id}/invoice.pdf`
}

function closeDetail() {
  invoice.value = null
  customLabel.value = ''
  customAmount.value = 0
  customError.value = ''
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
  customError.value = ''
  customLabel.value = ''
  customAmount.value = 0
  try {
    invoice.value = await api.getInvoice(id)
  } catch (e) {
    error.value = e.message
  }
}

async function refreshInvoice() {
  if (!invoice.value) return
  invoice.value = await api.getInvoice(invoice.value.booking_id)
  await loadList()
}

async function addCustomLine() {
  if (!invoice.value) return
  const label = customLabel.value.trim()
  if (!label) return
  savingCustom.value = true
  customError.value = ''
  try {
    await api.createCustomInvoiceLine(invoice.value.booking_id, {
      label,
      amount: Number(customAmount.value) || 0,
    })
    customLabel.value = ''
    customAmount.value = 0
    await refreshInvoice()
  } catch (e) {
    customError.value = e.message
  } finally {
    savingCustom.value = false
  }
}

async function removeCustomLine(lineId) {
  if (!invoice.value) return
  savingCustom.value = true
  customError.value = ''
  try {
    await api.deleteCustomInvoiceLine(invoice.value.booking_id, lineId)
    await refreshInvoice()
  } catch (e) {
    customError.value = e.message
  } finally {
    savingCustom.value = false
  }
}

onMounted(loadList)
</script>
