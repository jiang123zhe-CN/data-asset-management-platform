import api from './api'

export function getReportSummary() {
  return api.get('/reports/summary').then((res) => res.data)
}

export function getReportByDirectory() {
  return api.get('/reports/by-directory').then((res) => res.data)
}

export function getReportBySensitivity() {
  return api.get('/reports/by-sensitivity').then((res) => res.data)
}

export function exportFieldsReport() {
  return api.get('/reports/export/fields', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'data_fields_report.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
  })
}

export function exportMappingsReport() {
  return api.get('/reports/export/mappings', { responseType: 'blob' }).then((res) => {
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', 'mappings_report.xlsx')
    document.body.appendChild(link)
    link.click()
    link.remove()
  })
}
