import api from './api'

export function getTaggingStats() {
  return api.get('/tagging/stats/').then(res => res.data)
}

export function getTaggingResults(params) {
  return api.get('/tagging/results/', { params }).then(res => res.data)
}

export function triggerTagging(mode = 'full', fieldIds = null) {
  return api.post('/tagging/run', { mode, field_ids: fieldIds }).then(res => res.data)
}

export function getTaggingTaskStatus(taskId) {
  return api.get(`/tagging/run/${taskId}/status`).then(res => res.data)
}

export function manualUpdateTagging(fieldId, data) {
  return api.put(`/tagging/results/${fieldId}`, data).then(res => res.data)
}

export function batchUpdateTagging(data) {
  return api.put('/tagging/results/batch', data).then(res => res.data)
}

export function getTaggingHistory(fieldId) {
  return api.get(`/tagging/results/${fieldId}/history`).then(res => res.data)
}
