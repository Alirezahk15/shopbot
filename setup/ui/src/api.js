// Thin fetch wrapper around the wizard's Python JSON API.
// No axios: the wizard bundle must stay small and build fast on a fresh server.

async function request(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  let data = null
  try {
    data = await res.json()
  } catch {
    data = null
  }
  if (!res.ok) {
    const err = new Error((data && data.detail) || `HTTP ${res.status}`)
    err.status = res.status
    err.data = data
    throw err
  }
  return data
}

const api = {
  get: (path) => request(path),
  post: (path, body) =>
    request(path, { method: 'POST', body: JSON.stringify(body || {}) }),
}

export default api

export const getServerInfo = () => api.get('/api/server-info')
export const getState = () => api.get('/api/state')
export const validateToken = (token) => api.post('/api/validate-token', { token })
export const checkDomain = (domain) => api.post('/api/check-domain', { domain })
export const saveConfig = (config) => api.post('/api/save', config)
export const startInstall = () => api.post('/api/install', {})
export const resumeInstall = () => api.post('/api/resume', {})
export const retryStep = () => api.post('/api/retry-step', {})
export const retrySsl = () => api.post('/api/retry-ssl', {})
export const restartClean = () => api.post('/api/restart-clean', {})
