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

export function exportTaggingResults() {
  return api.get('/tagging/export/', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    link.setAttribute('download', `tagging_results_${date}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  })
}
