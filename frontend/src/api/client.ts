import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/store/authStore'

const BASE_URL = '/api/v1'

export const apiClient: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach access token to every request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Refresh token on 401
// The refresh token travels as an HttpOnly cookie (S-7); no body is needed.
//
// S-8: singleton refresh promise — if multiple requests fail with 401 at the
// same time, they all queue onto the one in-flight refresh call instead of each
// firing their own.  A second simultaneous refresh would consume the rotated
// cookie and leave every subsequent request with a revoked token.
let refreshPromise: Promise<string> | null = null

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as AxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        if (!refreshPromise) {
          refreshPromise = axios
            .post(`${BASE_URL}/auth/refresh`, {})
            .then(({ data }) => data.access_token as string)
            .finally(() => {
              refreshPromise = null
            })
        }
        const newAccessToken = await refreshPromise
        useAuthStore.getState().setTokens(newAccessToken)
        if (original.headers) {
          original.headers['Authorization'] = `Bearer ${newAccessToken}`
        }
        return apiClient(original)
      } catch {
        useAuthStore.getState().logout()
      }
    }
    return Promise.reject(error)
  }
)
