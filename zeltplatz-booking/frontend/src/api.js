const API_BASE = '/api/v1'

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })
  if (res.status === 204) return null
  const text = await res.text()
  let data = null
  try {
    data = text ? JSON.parse(text) : null
  } catch {
    data = text
  }
  if (!res.ok) {
    const detail = data?.detail
    const message = typeof detail === 'string' ? detail : JSON.stringify(detail || data || res.statusText)
    throw new Error(message)
  }
  return data
}

export const api = {
  health: () => request('/health'),
  countries: () => request('/countries'),
  listPitches: () => request('/pitches'),
  createPitch: (body) => request('/pitches', { method: 'POST', body: JSON.stringify(body) }),
  updatePitch: (id, body) => request(`/pitches/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deletePitch: (id) => request(`/pitches/${id}`, { method: 'DELETE' }),
  availablePitches: (start, end, excludeBookingId) => {
    const params = new URLSearchParams({ start, end })
    if (excludeBookingId != null && excludeBookingId !== '') {
      params.set('exclude_booking_id', String(excludeBookingId))
    }
    return request(`/pitches/available?${params}`)
  },
  pitchBookings: (id) => request(`/pitches/${id}/bookings`),
  listBookings: (fromDate, toDate) => {
    const params = new URLSearchParams()
    if (fromDate) params.set('from_date', fromDate)
    if (toDate) params.set('to_date', toDate)
    const q = params.toString()
    return request(`/bookings${q ? `?${q}` : ''}`)
  },
  gantt: (fromDate, toDate) => {
    const params = new URLSearchParams()
    if (fromDate) params.set('from_date', fromDate)
    if (toDate) params.set('to_date', toDate)
    const q = params.toString()
    return request(`/bookings/gantt${q ? `?${q}` : ''}`)
  },
  createBooking: (body) => request('/bookings', { method: 'POST', body: JSON.stringify(body) }),
  getBooking: (id) => request(`/bookings/${id}`),
  updateBooking: (id, body) => request(`/bookings/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  amendBooking: (id, body) => request(`/bookings/${id}/amend`, { method: 'POST', body: JSON.stringify(body) }),
  deleteBooking: (id) => request(`/bookings/${id}`, { method: 'DELETE' }),
  toggleBookingDeposit: (id) =>
    request(`/bookings/${id}/deposit/toggle`, { method: 'POST' }),
  listServiceGroups: () => request('/service-groups'),
  createServiceGroup: (body) => request('/service-groups', { method: 'POST', body: JSON.stringify(body) }),
  updateServiceGroup: (id, body) =>
    request(`/service-groups/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteServiceGroup: (id) => request(`/service-groups/${id}`, { method: 'DELETE' }),
  listServices: (groupId) => {
    const q = groupId != null ? `?group_id=${encodeURIComponent(groupId)}` : ''
    return request(`/services${q}`)
  },
  createService: (body) => request('/services', { method: 'POST', body: JSON.stringify(body) }),
  updateService: (id, body) => request(`/services/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deleteService: (id) => request(`/services/${id}`, { method: 'DELETE' }),
  servicesAvailability: (start, end, excludeBookingId) => {
    const params = new URLSearchParams({ start, end })
    if (excludeBookingId != null && excludeBookingId !== '') {
      params.set('exclude_booking_id', String(excludeBookingId))
    }
    return request(`/services/availability?${params}`)
  },
  listPriceProfiles: () => request('/price-profiles'),
  createPriceProfile: (body) =>
    request('/price-profiles', { method: 'POST', body: JSON.stringify(body) }),
  updatePriceProfile: (id, body) =>
    request(`/price-profiles/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deletePriceProfile: (id) => request(`/price-profiles/${id}`, { method: 'DELETE' }),
  listPersonFeeElements: (priceProfileId) => {
    const q =
      priceProfileId != null ? `?price_profile_id=${encodeURIComponent(priceProfileId)}` : ''
    return request(`/person-fee-elements${q}`)
  },
  createPersonFeeElement: (body) =>
    request('/person-fee-elements', { method: 'POST', body: JSON.stringify(body) }),
  updatePersonFeeElement: (id, body) =>
    request(`/person-fee-elements/${id}`, { method: 'PATCH', body: JSON.stringify(body) }),
  deletePersonFeeElement: (id) => request(`/person-fee-elements/${id}`, { method: 'DELETE' }),
  listBilling: (fromDate, toDate) => {
    const params = new URLSearchParams()
    if (fromDate) params.set('from_date', fromDate)
    if (toDate) params.set('to_date', toDate)
    const q = params.toString()
    return request(`/billing${q ? `?${q}` : ''}`)
  },
  getInvoice: (id) => request(`/bookings/${id}/invoice`),
  createCustomInvoiceLine: (bookingId, body) =>
    request(`/bookings/${bookingId}/invoice/custom-lines`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateCustomInvoiceLine: (bookingId, lineId, body) =>
    request(`/bookings/${bookingId}/invoice/custom-lines/${lineId}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  deleteCustomInvoiceLine: (bookingId, lineId) =>
    request(`/bookings/${bookingId}/invoice/custom-lines/${lineId}`, { method: 'DELETE' }),
  getMeta: () => request('/meta'),
  parseGaesteblatt: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const url = `${API_BASE}/bookings/parse-gaesteblatt`
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 60000)
    try {
      const res = await fetch(url, {
        method: 'POST',
        body: form,
        signal: controller.signal,
      })
      const text = await res.text()
      let data = null
      try {
        data = text ? JSON.parse(text) : null
      } catch {
        data = text
      }
      if (!res.ok) {
        const detail = data?.detail
        const message = typeof detail === 'string' ? detail : JSON.stringify(detail || data || res.statusText)
        throw new Error(message)
      }
      return data
    } catch (e) {
      if (e?.name === 'AbortError') {
        throw new Error('Import-Timeout: Backend antwortet nicht (Port 8000 prüfen / neu starten).')
      }
      throw e
    } finally {
      clearTimeout(timeoutId)
    }
  },
  getOperatorSettings: () => request('/operator-settings'),
  updateOperatorSettings: (body) =>
    request('/operator-settings', { method: 'PATCH', body: JSON.stringify(body) }),
  operatorLogoUrl: () => `${API_BASE}/operator-settings/logo`,
  uploadOperatorLogo: async (file) => {
    const form = new FormData()
    form.append('file', file)
    const url = `${API_BASE}/operator-settings/logo`
    const res = await fetch(url, {
      method: 'POST',
      body: form,
    })
    const text = await res.text()
    let data = null
    try {
      data = text ? JSON.parse(text) : null
    } catch {
      data = text
    }
    if (!res.ok) {
      const detail = data?.detail
      const message = typeof detail === 'string' ? detail : JSON.stringify(detail || data || res.statusText)
      throw new Error(message)
    }
    return data
  },
  deleteOperatorLogo: () => request('/operator-settings/logo', { method: 'DELETE' }),
}
