import api from './api'

export function getUsers(params) {
  return api.get('/users', { params }).then((res) => res.data)
}

export function createUser(data) {
  return api.post('/users', data).then((res) => res.data)
}

export function updateUser(id, data) {
  return api.put(`/users/${id}`, data).then((res) => res.data)
}

export function deleteUser(id) {
  return api.delete(`/users/${id}`).then((res) => res.data)
}

export function resetPassword(id) {
  return api.put(`/users/${id}/reset-password`).then((res) => res.data)
}
