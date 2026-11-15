import { apiClient } from './client'

// VoxEats-funded promotions. They apply only when the customer pays online in
// the app, come out of our commission, and are computed by the backend.
export type PromotionKind = 'percent' | 'amount_off'
export type PromotionChannels = 'all' | 'app' | 'phone'

export type PlatformPromotion = {
  id: string
  name: string
  kind: PromotionKind
  value: string
  min_subtotal: string
  channels: PromotionChannels
  starts_on: string | null
  ends_on: string | null
  is_active: boolean
  orders_count: number
  first_order_only: boolean
  per_user_limit: number | null
  monthly_budget: string | null
  spent_this_month: string
  created_at: string
}

export type PlatformPromotionCreate = {
  name: string
  kind: PromotionKind
  value: string
  min_subtotal: string
  channels: PromotionChannels
  starts_on: string | null
  ends_on: string | null
  first_order_only: boolean
  per_user_limit: number | null
  monthly_budget: string | null
}

export type PlatformPromotionUpdate = Partial<
  Pick<PlatformPromotion, 'name' | 'is_active' | 'starts_on' | 'ends_on' | 'first_order_only' | 'per_user_limit' | 'monthly_budget'>
>

export async function listPromotions(): Promise<PlatformPromotion[]> {
  const res = await apiClient.get('/admin/promotions')
  return res.data as PlatformPromotion[]
}

export async function createPromotion(body: PlatformPromotionCreate): Promise<PlatformPromotion> {
  const res = await apiClient.post('/admin/promotions', body)
  return res.data as PlatformPromotion
}

export async function updatePromotion(id: string, patch: PlatformPromotionUpdate): Promise<PlatformPromotion> {
  const res = await apiClient.patch(`/admin/promotions/${id}`, patch)
  return res.data as PlatformPromotion
}

export async function deletePromotion(id: string): Promise<void> {
  await apiClient.delete(`/admin/promotions/${id}`)
}
