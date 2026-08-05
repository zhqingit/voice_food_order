import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { getAccessToken, setAccessToken } from '../auth/tokenStore'

const baseURL = (import.meta.env.VITE_ADMIN_API_BASE_URL as string | undefined) ?? ''

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

  let refreshInFlight: Promise<string> | null = null

  async function refreshAccessToken(): Promise<string> {
    if (!refreshInFlight) {
      refreshInFlight = client
        .post('/admin/auth/refresh')
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

function _isAuthEndpoint(pathname: string): boolean {
  return (
    pathname === '/admin/auth/login' ||
    pathname === '/admin/auth/refresh' ||
    pathname === '/admin/auth/logout'
  )
}
