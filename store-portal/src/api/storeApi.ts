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
