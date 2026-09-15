async function request(path, options = {}) {
  const response = await fetch(path, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}`
    try {
      const payload = await response.json()
      message = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail || payload)
    } catch {
      message = await response.text()
    }
    throw new Error(message)
  }

  if (response.status === 204) {
    return null
  }
  return response.json()
}

export const api = {
  session: () => request('/api/session'),
  login: (email, password) => request('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  }),
  logout: () => request('/api/auth/logout', { method: 'POST' }),
  me: () => request('/api/me'),
  bike: (id) => request(`/api/bikes/${id}`),
  syncTrips: (payload) => request('/api/sync/trips', {
    method: 'POST',
    body: JSON.stringify(payload),
  }),
  trips: () => request('/api/trips'),
  trip: (id) => request(`/api/trips/${id}`),
  heatmap: () => request('/api/heatmap/geojson'),
  roadHeatmap: ({ datePrefix = '', dateFrom = '', dateTo = '', grid = 10 } = {}) => {
    const params = new URLSearchParams({ grid_m: String(grid) })
    if (datePrefix) params.set('date_prefix', datePrefix)
    if (dateFrom) params.set('date_from', dateFrom)
    if (dateTo) params.set('date_to', dateTo)
    return request(`/api/heatmap/roads?${params.toString()}`)
  },
  overview: () => request('/api/metrics/overview'),
}
