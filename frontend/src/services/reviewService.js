import api from './api'

export function getReviews(params) {
  return api.get('/reviews', { params }).then((res) => res.data)
}

export function getReview(id) {
  return api.get(`/reviews/${id}`).then((res) => res.data)
}

export function submitReview(id, data) {
  return api.put(`/reviews/${id}`, data).then((res) => res.data)
}

export function triggerAnomalyDetection() {
  return api.post('/reviews/auto-detect').then((res) => res.data)
}

export function getReviewStats() {
  return api.get('/reviews/stats').then((res) => res.data)
}
