import { apiClient } from '../api/client'
import { setAccessToken } from './tokenStore'

export type StoreMe = {
  id: string
  name: string
  phone: string | null
  address_line1: string | null
  address_line2: string | null
  city: string | null
  state: string | null
  postal_code: string | null
  country: string | null
  timezone: string | null
  allow_pickup: boolean | null
  allow_delivery: boolean | null
  min_order_amount: string | number | null
  email: string
  created_at: string
}

export async function login(email: string, password: string): Promise<void> {
  const res = await apiClient.post('/store/auth/login', { email, password })
  const token = (res.data as { access_token: string }).access_token
  setAccessToken(token)
}

export async function signup(payload: {
  email: string
  password: string
  name: string
  phone?: string
}): Promise<void> {
  const res = await apiClient.post('/store/auth/signup', payload)
  const token = (res.data as { access_token: string }).access_token
  setAccessToken(token)
}

export async function logout(): Promise<void> {
  try {
    await apiClient.post('/store/auth/logout')
  } finally {
    setAccessToken(null)
  }
}

export async function refresh(): Promise<void> {
  const res = await apiClient.post('/store/auth/refresh')
  const token = (res.data as { access_token: string }).access_token
  setAccessToken(token)
}

export async function getMe(): Promise<StoreMe> {
  const res = await apiClient.get('/store/me')
  return res.data as StoreMe
}
