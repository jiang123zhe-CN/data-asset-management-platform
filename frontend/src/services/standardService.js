import api from './api'

// ── Classification Categories ──

export function getCategoryTree() {
  return api.get('/standards/categories/tree').then(res => res.data)
}

export function getCategories(params) {
  return api.get('/standards/categories/', { params }).then(res => res.data)
}

export function getCategory(id) {
  return api.get(`/standards/categories/${id}`).then(res => res.data)
}

export function createCategory(data) {
  return api.post('/standards/categories/', data).then(res => res.data)
}

export function updateCategory(id, data) {
  return api.put(`/standards/categories/${id}`, data).then(res => res.data)
}

export function deleteCategory(id) {
  return api.delete(`/standards/categories/${id}`).then(res => res.data)
}

export function exportCategories() {
  return api.get('/standards/categories/export', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'classification_categories.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  })
}

export function importCategories(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/standards/categories/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(res => res.data)
}

// ── Tiering Rules ──

export function getTiers(params) {
  return api.get('/standards/tiers/', { params }).then(res => res.data)
}

export function getTier(id) {
  return api.get(`/standards/tiers/${id}`).then(res => res.data)
}

export function createTier(data) {
  return api.post('/standards/tiers/', data).then(res => res.data)
}

export function updateTier(id, data) {
  return api.put(`/standards/tiers/${id}`, data).then(res => res.data)
}

export function deleteTier(id) {
  return api.delete(`/standards/tiers/${id}`).then(res => res.data)
}

export function exportTiers() {
  return api.get('/standards/tiers/export', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'tiering_rules.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  })
}

export function importTiers(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/standards/tiers/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(res => res.data)
}

// ── Finance Compliance Categories (国信办通字〔2026〕2号) ──

export function getFinanceCategoryTree() {
  return api.get('/compliance/categories/tree').then(res => res.data)
}

export function getFinanceCategories(params) {
  return api.get('/compliance/categories/', { params }).then(res => res.data)
}

export function getFinanceCategory(id) {
  return api.get(`/compliance/categories/${id}`).then(res => res.data)
}

export function updateFinanceCategory(id, data) {
  return api.put(`/compliance/categories/${id}`, data).then(res => res.data)
}

// ── Finance Grading Matrix ──

export function getGradingMatrix() {
  return api.get('/compliance/grading-rules/matrix').then(res => res.data)
}

export function getGradingRules() {
  return api.get('/compliance/grading-rules/').then(res => res.data)
}

// ── Compliance Classification ──

export function runComplianceClassify(fieldIds) {
  return api.post('/compliance/classify', fieldIds ? { field_ids: fieldIds } : {}).then(res => res.data)
}

export function getThresholdCheck() {
  return api.get('/compliance/threshold').then(res => res.data)
}

export function getTableLevel(tableName) {
  return api.get('/compliance/table-level', { params: { table_name: tableName } }).then(res => res.data)
}

// ── Compliance Export ──

export function exportComplianceInventory() {
  return api.get('/compliance/export/inventory', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    const date = new Date().toISOString().slice(0, 10).replace(/-/g, '')
    link.setAttribute('download', `compliance_inventory_${date}.xlsx`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  })
}

// ── Threshold Snapshots ──

export function createThresholdSnapshot() {
  return api.post('/compliance/threshold/snapshot').then(res => res.data)
}

export function getThresholdSnapshots() {
  return api.get('/compliance/threshold/snapshots').then(res => res.data)
}
