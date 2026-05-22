import api from './api'

export function getFields(params) {
  return api.get('/fields', { params }).then((res) => res.data)
}

export function getField(id) {
  return api.get(`/fields/${id}`).then((res) => res.data)
}

export function createField(data) {
  return api.post('/fields', data).then((res) => res.data)
}

export function updateField(id, data) {
  return api.put(`/fields/${id}`, data).then((res) => res.data)
}

export function deleteField(id) {
  return api.delete(`/fields/${id}`).then((res) => res.data)
}

export function importFields(file) {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/fields/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then((res) => res.data)
}

export function getImportHistory() {
  return api.get('/fields/import/history').then((res) => res.data)
}

export function getImportErrors(id) {
  return api.get(`/fields/import/${id}/errors`).then((res) => res.data)
}

export function downloadTemplate() {
  return api.get('/fields/import/template', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'field_import_template.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
  })
}

export function exportFields() {
  return api.get('/fields/export/excel', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'data_fields.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
  })
}
