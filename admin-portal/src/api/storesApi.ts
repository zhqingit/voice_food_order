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
  // Commission (basis points, on the pre-tax subtotal) by order channel:
  // the store's override (null = platform default) and the rate in effect.
  commission_app_bps: number | null
  commission_phone_bps: number | null
  effective_app_bps: number
  effective_phone_bps: number
  monthly_fee: string // flat fee on the monthly invoice; "0.00" = none
  phone_ai_number: string | null // Twilio number answered by the AI (E.164)
  phone_ai_enabled: boolean // store's own on/off switch for phone ordering
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
  // Send null to clear an override (fall back to the platform default);
  // omit to leave unchanged.
  commission_app_bps?: number | null
  commission_phone_bps?: number | null
  monthly_fee?: string
  // Send null to take the number away (also turns phone ordering off).
  phone_ai_number?: string | null
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
