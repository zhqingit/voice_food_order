import { apiClient } from './client'
import type { Money, UUID } from './types'

export type StoreMe = {
  id: UUID
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
  min_order_amount: Money | null
  tax_rate: Money
  voice_tone: string | null
  logo_url: string | null
  email: string
  created_at: string
}

export type StoreMeUpdate = Partial<
  Pick<
    StoreMe,
    | 'name'
    | 'phone'
    | 'address_line1'
    | 'address_line2'
    | 'city'
    | 'state'
    | 'postal_code'
    | 'country'
    | 'timezone'
    | 'allow_pickup'
    | 'allow_delivery'
    | 'min_order_amount'
    | 'tax_rate'
    | 'voice_tone'
    | 'logo_url'
  >
>

export async function getMe(): Promise<StoreMe> {
  const res = await apiClient.get('/store/me')
  return res.data as StoreMe
}

export async function updateMe(payload: StoreMeUpdate): Promise<StoreMe> {
  const res = await apiClient.patch('/store/me', payload)
  return res.data as StoreMe
}

// ── Store Hours ──────────────────────────────────────────────────────────────

export type DayHours = {
  day_of_week: number // 0=Mon .. 6=Sun
  open_time: string   // "HH:MM"
  close_time: string  // "HH:MM"
  is_closed: boolean
}

export async function getHours(): Promise<DayHours[]> {
  const res = await apiClient.get('/store/me/hours')
  return res.data as DayHours[]
}

export async function updateHours(hours: DayHours[]): Promise<DayHours[]> {
  const res = await apiClient.put('/store/me/hours', { hours })
  return res.data as DayHours[]
}

// ── Logo ─────────────────────────────────────────────────────────────────────

export async function uploadLogo(file: File): Promise<StoreMe> {
  const form = new FormData()
  form.append('file', file)
  const res = await apiClient.post('/store/me/logo', form, {
    headers: { 'Content-Type': undefined },
  })
  return res.data as StoreMe
}
