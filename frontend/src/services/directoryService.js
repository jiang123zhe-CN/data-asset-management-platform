import api from './api'

export function getDirectoryTree() {
  return api.get('/directories/tree').then((res) => res.data)
}

export function getDirectory(id) {
  return api.get(`/directories/${id}`).then((res) => res.data)
}

export function createDirectory(data) {
  return api.post('/directories', data).then((res) => res.data)
}

export function updateDirectory(id, data) {
  return api.put(`/directories/${id}`, data).then((res) => res.data)
}

export function deleteDirectory(id) {
  return api.delete(`/directories/${id}`).then((res) => res.data)
}

export function moveDirectory(id, data) {
  return api.put(`/directories/${id}/move`, data).then((res) => res.data)
}
