import { apiClient } from './client'

// The platform's monthly invoices to this store (commission on orders paid at
// the store, monthly fee, adjustments). Money values are decimal strings.
export type InvoiceStatus = 'open' | 'paid' | 'void' | 'uncollectible'

export type Invoice = {
  id: string
  period: string // YYYY-MM
  status: InvoiceStatus
  overdue: boolean
  total: string
  order_count: number
  due_date: string | null
  hosted_url: string | null // Stripe page where the invoice is paid
  pdf_url: string | null
  paid_at: string | null
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

export async function listInvoices(): Promise<Invoice[]> {
  const res = await apiClient.get('/store/invoices')
  return res.data as Invoice[]
}

export async function getInvoice(id: string): Promise<InvoiceDetail> {
  const res = await apiClient.get(`/store/invoices/${id}`)
  return res.data as InvoiceDetail
}

export async function downloadInvoiceCsv(invoice: Invoice): Promise<void> {
  const res = await apiClient.get(`/store/invoices/${invoice.id}/csv`, { responseType: 'blob' })
  const url = URL.createObjectURL(res.data as Blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `voxeats-invoice-${invoice.period}.csv`
  a.click()
  URL.revokeObjectURL(url)
}
