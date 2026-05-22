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
