import { apiClient } from './client'

// Money values are decimal strings ("12.50").
// gmv is pre-tax and after store discounts; discounts are store-funded promotions.
export type ChannelStats = { orders: number; gmv: string; discounts: string; commission: string }

export type StoreMonthStats = {
  store_id: string
  store_name: string
  app: ChannelStats
  phone: ChannelStats
  commission_online: string // taken through Stripe
  commission_to_invoice: string // paid at the store; billed monthly
  monthly_fee: string
  revenue: string
  ai_cost: string
  phone_calls: number
  phone_minutes: number
  telephony_cost: string // estimated
  stripe_fees: string
  invoice_fees: string // Stripe fees on this month's paid invoice
  platform_discounts: string // VoxEats promotions, given out of our commission
  costs: string
  net: string
}

export type CostCategory = 'server' | 'phone_numbers' | 'domain' | 'other'

export type PlatformCost = { id: string; month: string; category: CostCategory; amount: string; note: string | null }

export type MonthlyStats = {
  month: string // YYYY-MM
  totals: {
    orders: number
    gmv: string
    discounts: string
    commission: string
    commission_online: string
    commission_to_invoice: string
    monthly_fees: string
    revenue: string
    ai_cost: string
    telephony_cost: string
    stripe_fees: string
    invoice_fees: string
    platform_discounts: string
    fixed_costs: string
    costs: string
    net: string
    // This month's invoices to stores (sent ones).
    invoiced: string
    invoice_paid: string
    invoice_outstanding: string
    invoice_overdue: string
  }
  stores: StoreMonthStats[]
  fixed_costs: PlatformCost[]
}

export async function getMonthlyStats(month: string): Promise<MonthlyStats> {
  const res = await apiClient.get('/admin/stats/monthly', { params: { month } })
  return res.data as MonthlyStats
}

export async function downloadMonthlyCsv(month: string): Promise<void> {
  const res = await apiClient.get('/admin/stats/monthly.csv', { params: { month }, responseType: 'blob' })
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `voxeats-${month}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

export async function addPlatformCost(cost: {
  month: string
  category: CostCategory
  amount: string
  note?: string
}): Promise<PlatformCost> {
  const res = await apiClient.post('/admin/stats/costs', cost)
  return res.data as PlatformCost
}

export async function deletePlatformCost(id: string): Promise<void> {
  await apiClient.delete(`/admin/stats/costs/${id}`)
}
