import { apiClient } from './client'

export type AdminStore = {
  id: string
  name: string
  email: string
  phone: string | null
  is_published: boolean
  is_approved: boolean
  is_active: boolean
  stripe_account_id: string | null
  stripe_charges_enabled: boolean
  platform_fee_bps: number | null // store override; null = platform default
  effective_fee_bps: number // resolved commission actually applied
  created_at: string
}

export type AdminStoreDetail = AdminStore & {
  // Live Stripe status, best-effort (null when not connected or fetch failed).
  stripe_details_submitted: boolean | null
  stripe_payouts_enabled: boolean | null
}

export type AdminStoreUpdate = {
  is_approved?: boolean
  is_active?: boolean
  // Send null to clear the override (fall back to the platform default);
  // omit to leave unchanged.
  platform_fee_bps?: number | null
}

export async function listStores(): Promise<AdminStore[]> {
  const res = await apiClient.get('/admin/stores')
  return res.data as AdminStore[]
}

export async function getStore(id: string): Promise<AdminStoreDetail> {
  const res = await apiClient.get(`/admin/stores/${id}`)
  return res.data as AdminStoreDetail
}

export async function updateStore(id: string, patch: AdminStoreUpdate): Promise<AdminStoreDetail> {
  const res = await apiClient.patch(`/admin/stores/${id}`, patch)
  return res.data as AdminStoreDetail
}
