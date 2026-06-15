import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('dam_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // Add trailing slash (last segment is resource name, not ID or extension)
  if (config.url && !config.url.includes('?') && !config.url.endsWith('/')) {
    const segments = config.url.split('/').filter(Boolean)
    const last = segments[segments.length - 1] || ''
    if (last && !/^\d+$/.test(last) && !last.includes('.')) {
      config.url = config.url + '/'
    }
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('dam_token')
    }
    return Promise.reject(error)
  },
)

export function getHealth() {
  return api.get('/health').then((res) => res.data)
}

export default api
