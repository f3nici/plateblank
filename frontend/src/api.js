import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail || error.message || 'An error occurred'
    // Dispatch a custom event for toast notifications
    window.dispatchEvent(
      new CustomEvent('api-error', { detail: { message } })
    )
    return Promise.reject(error)
  }
)

export default api
