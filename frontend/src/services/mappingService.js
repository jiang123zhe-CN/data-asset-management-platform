import api from './api'

export function getMappings(params) {
  return api.get('/mappings', { params }).then((res) => res.data)
}

export function createMapping(data) {
  return api.post('/mappings', data).then((res) => res.data)
}

export function batchCreateMappings(data) {
  return api.post('/mappings/batch', data).then((res) => res.data)
}

export function deleteMapping(id) {
  return api.delete(`/mappings/${id}`).then((res) => res.data)
}

export function batchDeleteMappings(ids) {
  return api.post('/mappings/batch-delete', { mapping_ids: ids }).then((res) => res.data)
}

export function getVisualizationData() {
  return api.get('/mappings/visualization').then((res) => res.data)
}

export function getUnmappedFields() {
  return api.get('/mappings/unmapped-fields').then((res) => res.data)
}

export function getMappingStats() {
  return api.get('/mappings/stats').then((res) => res.data)
}

export function triggerAutoMap() {
  return api.post('/mappings/auto-map').then((res) => res.data)
}

export function getAutoMapStatus(taskId) {
  return api.get(`/mappings/auto-map/status/${taskId}`).then((res) => res.data)
}

export function getAiSuggestions(params) {
  return api.get('/mappings/ai-suggestions', { params }).then((res) => res.data)
}

export function exportMappings() {
  return api.get('/mappings/export', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `映射数据_${new Date().toISOString().slice(0, 10)}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  })
}
