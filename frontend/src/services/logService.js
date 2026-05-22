import api from './api'

export function getLogs(params) {
  return api.get('/logs', { params }).then((res) => res.data)
}
