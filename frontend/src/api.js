import axios from 'axios'

function getSessionToken() {
  let token = localStorage.getItem('plateblank_session')
  if (!token) {
    token = crypto.randomUUID()
    localStorage.setItem('plateblank_session', token)
  }
  return token
}

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  config.headers['X-Session-Token'] = getSessionToken()
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail || error.message || 'An error occurred'
    window.dispatchEvent(
      new CustomEvent('api-error', { detail: { message } })
    )
    return Promise.reject(error)
  }
)

export { getSessionToken }
export default api
