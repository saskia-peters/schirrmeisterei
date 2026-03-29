import axios from 'axios'
import * as SecureStore from 'expo-secure-store'

// This URL should be changed to your backend URL in production
// For local development, use your machine's IP or localhost
const BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use(async (config) => {
  const token = await SecureStore.getItemAsync('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = await SecureStore.getItemAsync('refresh_token')
      if (refreshToken) {
        try {
          const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          })
          await SecureStore.setItemAsync('access_token', data.access_token)
          await SecureStore.setItemAsync('refresh_token', data.refresh_token)
          original.headers['Authorization'] = `Bearer ${data.access_token}`
          return apiClient(original)
        } catch {
          await SecureStore.deleteItemAsync('access_token')
          await SecureStore.deleteItemAsync('refresh_token')
        }
      }
    }
    return Promise.reject(error)
  }
)

export const mobileAuthApi = {
  login: async (email: string, password: string, totp_code?: string) => {
    const { data } = await apiClient.post('/auth/login', { email, password, totp_code })
    await SecureStore.setItemAsync('access_token', data.access_token)
    await SecureStore.setItemAsync('refresh_token', data.refresh_token)
    return data
  },
  me: () => apiClient.get('/auth/me').then((r) => r.data),
  logout: async () => {
    await SecureStore.deleteItemAsync('access_token')
    await SecureStore.deleteItemAsync('refresh_token')
  },
}

export const mobileTicketsApi = {
  getBoard: () => apiClient.get('/tickets/board').then((r) => r.data),
  list: () => apiClient.get('/tickets/').then((r) => r.data),
  get: (id: string) => apiClient.get(`/tickets/${id}`).then((r) => r.data),
  updateStatus: (id: string, status: string, note?: string) =>
    apiClient.patch(`/tickets/${id}/status`, { status, note }).then((r) => r.data),
}
