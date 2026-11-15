import { apiClient } from './client'

export type InvoiceStatus = 'draft' | 'open' | 'paid' | 'void' | 'uncollectible'

export type Invoice = {
  id: string
  store_id: string
  store_name: string
  period: string // YYYY-MM
  status: InvoiceStatus
  overdue: boolean
  total: string
  order_count: number
  due_date: string | null
  hosted_url: string | null
  pdf_url: string | null
  paid_out_of_band: boolean
  sent_at: string | null
  paid_at: string | null
  created_at: string
}

export type InvoiceLine = {
  id: string
  kind: 'order' | 'monthly_fee' | 'adjustment'
  description: string
  amount: string
  order_code: string | null
  order_day: string | null
  channel: string | null
  subtotal: string | null
  commission_bps: number | null
  commission: string | null
  collected_online: string | null
}

export type InvoiceDetail = Invoice & { lines: InvoiceLine[] }

export async function listInvoices(period: string): Promise<Invoice[]> {
  const res = await apiClient.get('/admin/invoices', { params: { period } })
  return res.data as Invoice[]
}

export async function generateInvoices(period: string): Promise<Invoice[]> {
  const res = await apiClient.post('/admin/invoices/generate', { period })
  return res.data as Invoice[]
}

export async function getInvoice(id: string): Promise<InvoiceDetail> {
  const res = await apiClient.get(`/admin/invoices/${id}`)
  return res.data as InvoiceDetail
}

export async function addAdjustment(id: string, description: string, amount: string): Promise<InvoiceDetail> {
  const res = await apiClient.post(`/admin/invoices/${id}/adjustments`, { description, amount })
  return res.data as InvoiceDetail
}

export async function removeAdjustment(id: string, lineId: string): Promise<InvoiceDetail> {
  const res = await apiClient.delete(`/admin/invoices/${id}/adjustments/${lineId}`)
  return res.data as InvoiceDetail
}

export async function invoiceAction(id: string, action: 'send' | 'void' | 'mark-paid'): Promise<InvoiceDetail> {
  const res = await apiClient.post(`/admin/invoices/${id}/${action}`)
  return res.data as InvoiceDetail
}

export async function deleteDraft(id: string): Promise<void> {
  await apiClient.delete(`/admin/invoices/${id}`)
}
