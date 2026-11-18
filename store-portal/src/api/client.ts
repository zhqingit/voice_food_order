import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { getAccessToken, setAccessToken } from '../auth/tokenStore'

const baseURL = (import.meta.env.VITE_STORE_API_BASE_URL as string | undefined) ?? ''

function createClient(): AxiosInstance {
  const client = axios.create({
    baseURL,
    withCredentials: true,
    headers: {
      'Content-Type': 'application/json',
    },
  })

  client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    const token = getAccessToken()
    if (token) {
      config.headers = config.headers ?? {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  })

  client.interceptors.response.use(
    (res) => res,
    async (error: AxiosError) => {
      const status = error.response?.status
      const originalRequest = error.config

      if (!originalRequest || status !== 401) {
        throw error
      }

      const url = originalRequest.url ?? ''
      if (_isAuthEndpoint(url)) {
        // If login/signup fails, do not attempt refresh.
        throw error
      }

      const alreadyRetried = (originalRequest as any).__retried === true
      if (alreadyRetried) {
        throw error
      }

      try {
        await refreshAccessToken()
        ;(originalRequest as any).__retried = true
        return client.request(originalRequest)
      } catch {
        setAccessToken(null)
        throw error
      }
    },
  )

  return client
}

export const apiClient = createClient()

let refreshInFlight: Promise<string> | null = null

// Refresh tokens are single-use: the server treats a second use as theft and
// ends the session. Every caller shares one request, so concurrent refreshes
// (React StrictMode runs the startup effect twice in dev) can't trigger that.
export function refreshAccessToken(): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = apiClient
      .post('/store/auth/refresh')
      .then((res) => {
        const token = (res.data as { access_token: string }).access_token
        setAccessToken(token)
        return token
      })
      .finally(() => {
        refreshInFlight = null
      })
  }
  return refreshInFlight
}

function _isAuthEndpoint(pathname: string): boolean {
  return (
    pathname === '/store/auth/login' ||
    pathname === '/store/auth/signup' ||
    pathname === '/store/auth/refresh' ||
    pathname === '/store/auth/logout'
  )
}
