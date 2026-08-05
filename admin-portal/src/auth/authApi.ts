import { apiClient } from '../api/client'
import { setAccessToken } from './tokenStore'

export async function login(email: string, password: string): Promise<void> {
  const res = await apiClient.post('/admin/auth/login', { email, password })
  const token = (res.data as { access_token: string }).access_token
  setAccessToken(token)
}

export async function logout(): Promise<void> {
  try {
    await apiClient.post('/admin/auth/logout')
  } finally {
    setAccessToken(null)
  }
}

export async function refresh(): Promise<void> {
  const res = await apiClient.post('/admin/auth/refresh')
  const token = (res.data as { access_token: string }).access_token
  setAccessToken(token)
}
