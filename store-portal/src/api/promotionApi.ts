import { apiClient } from './client'

// Store-funded promotions, applied automatically to qualifying orders.
// Money and percent values are decimal strings.
export type PromotionKind = 'percent' | 'amount_off'
export type PromotionChannels = 'all' | 'app' | 'phone'

export type Promotion = {
  id: string
  name: string
  kind: PromotionKind
  value: string // percent off (10 = 10%) or dollars off
  min_subtotal: string // pre-tax subtotal needed; "0.00" = any order
  channels: PromotionChannels
  starts_on: string | null // YYYY-MM-DD, store-local, inclusive
  ends_on: string | null
  is_active: boolean
  orders_count: number // placed orders that used it; deletable only at 0
  created_at: string
}

export type PromotionCreate = {
  name: string
  kind: PromotionKind
  value: string
  min_subtotal: string
  channels: PromotionChannels
  starts_on: string | null
  ends_on: string | null
}

// The terms are fixed once created; only these can change.
export type PromotionUpdate = {
  name?: string
  is_active?: boolean
  starts_on?: string | null
  ends_on?: string | null
}

export async function listPromotions(): Promise<Promotion[]> {
  const res = await apiClient.get('/store/promotions')
  return res.data as Promotion[]
}

export async function createPromotion(body: PromotionCreate): Promise<Promotion> {
  const res = await apiClient.post('/store/promotions', body)
  return res.data as Promotion
}

export async function updatePromotion(id: string, patch: PromotionUpdate): Promise<Promotion> {
  const res = await apiClient.patch(`/store/promotions/${id}`, patch)
  return res.data as Promotion
}

export async function deletePromotion(id: string): Promise<void> {
  await apiClient.delete(`/store/promotions/${id}`)
}
