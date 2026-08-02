import axios from 'axios'

// 15s was far too short for backups, restores, CSV exports and mass
// broadcasts: the browser gave up while the server kept working, the admin
// saw an error and retried -- sending the same broadcast twice.
const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// Pass as { timeout: LONG_TIMEOUT } for operations known to be slow.
export const LONG_TIMEOUT = 300000

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Redirect to login on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthRequest = (error.config?.url || '').includes('/auth/login')
    if (error.response?.status === 401 && !isAuthRequest && window.location.pathname !== '/login') {
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Download a file through the authenticated API client, because
// window.open() does not attach the Authorization header.
export async function downloadFile(path, filename) {
  try {
    const res = await api.get(path, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (e) {
    // errors (e.g. 401) are already handled by the response interceptor
  }
}

export default api
