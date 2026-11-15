import { apiClient } from './client'
import type { Money, UUID } from './types'

export type OrderOut = {
  id: UUID
  short_code: string
  code_day: string
  store_id: UUID
  user_id: UUID | null
  status: string
  // unpaid | partially_paid | paid | refunded
  payment_status: string
  // Net paid so far (charges minus refunds), and what is still owed.
  amount_paid: Money
  balance_due: Money
  channel: string
  subtotal: Money // before discount
  discount: Money // store promotion, taken off before tax
  tax: Money
  total: Money
  customer_name: string | null
  // Phone orders: the caller's number (E.164) for call-backs.
  customer_phone: string | null
  user_email: string | null
  notes: string | null
  fulfillment_type: string | null
  delivery_address: string | null
  created_at: string
}

export type OrderItemOut = {
  id: UUID
  order_id: UUID
  menu_item_id: UUID
  name: string | null
  quantity: number
  price_snapshot: Money
  note: string | null
  variant_name: string | null
}

export async function listOrders(): Promise<OrderOut[]> {
  const res = await apiClient.get('/store/orders')
  return res.data as OrderOut[]
}

export async function getOrder(orderId: UUID): Promise<OrderOut> {
  const res = await apiClient.get(`/store/orders/${orderId}`)
  return res.data as OrderOut
}

export async function listOrderItems(orderId: UUID): Promise<OrderItemOut[]> {
  const res = await apiClient.get(`/store/orders/${orderId}/items`)
  return res.data as OrderItemOut[]
}

export async function updateOrderStatus(orderId: UUID, status: string): Promise<OrderOut> {
  const res = await apiClient.patch(`/store/orders/${orderId}`, { status })
  return res.data as OrderOut
}

// ── Staff edits to a placed order (each returns the order with new totals) ──

export async function addOrderItem(
  orderId: UUID,
  payload: { menu_item_id: UUID; variant_id?: UUID | null; quantity: number; note?: string | null },
): Promise<OrderOut> {
  const res = await apiClient.post(`/store/orders/${orderId}/items`, payload)
  return res.data as OrderOut
}

// Leave `note` out to keep it; send "" to remove it.
export async function updateOrderItem(
  orderId: UUID,
  itemId: UUID,
  payload: { quantity?: number; note?: string },
): Promise<OrderOut> {
  const res = await apiClient.patch(`/store/orders/${orderId}/items/${itemId}`, payload)
  return res.data as OrderOut
}

export async function removeOrderItem(orderId: UUID, itemId: UUID): Promise<OrderOut> {
  const res = await apiClient.delete(`/store/orders/${orderId}/items/${itemId}`)
  return res.data as OrderOut
}

export type OrderEventOut = {
  id: UUID
  actor: string
  kind: string
  detail: string
  total_before: Money | null
  total_after: Money | null
  created_at: string
}

export async function listOrderEvents(orderId: UUID): Promise<OrderEventOut[]> {
  const res = await apiClient.get(`/store/orders/${orderId}/events`)
  return res.data as OrderEventOut[]
}

// ── Money on an order: payments, refunds, in-store collection ──

export type PaymentOut = {
  id: UUID
  kind: 'charge' | 'refund'
  method: 'card' | 'in_store' | 'dispute'
  amount: Money
  status: 'pending' | 'succeeded' | 'failed' | 'canceled'
  failure_reason: string | null
  created_at: string
}

export type OrderPaymentsOut = {
  paid: Money
  refunded: Money
  net: Money
  balance_due: Money
  // Paid more than is owed (total lowered, or the order cancelled).
  overpaid: Money
  // How much can still go back to the customer's card.
  card_refundable: Money
  payments: PaymentOut[]
}

export async function getOrderPayments(orderId: UUID): Promise<OrderPaymentsOut> {
  const res = await apiClient.get(`/store/orders/${orderId}/payments`)
  return res.data as OrderPaymentsOut
}

export async function refundOrder(orderId: UUID, amount: string, method: 'card' | 'in_store'): Promise<OrderPaymentsOut> {
  const res = await apiClient.post(`/store/orders/${orderId}/refunds`, { amount, method })
  return res.data as OrderPaymentsOut
}

export async function recordInStorePayment(orderId: UUID, amount: string): Promise<OrderPaymentsOut> {
  const res = await apiClient.post(`/store/orders/${orderId}/payments`, { amount })
  return res.data as OrderPaymentsOut
}

// ── Telling the customer about changes ──

export type CustomerNoticeOut = {
  message: string
  phone: string | null
  // Changes the customer hasn't been told about yet.
  pending: boolean
  last_notified_at: string | null
  sms_available: boolean
}

export async function getCustomerNotice(orderId: UUID): Promise<CustomerNoticeOut> {
  const res = await apiClient.get(`/store/orders/${orderId}/customer-notice`)
  return res.data as CustomerNoticeOut
}

export async function markCustomerNotified(orderId: UUID, method: 'call' | 'sms'): Promise<CustomerNoticeOut> {
  const res = await apiClient.post(`/store/orders/${orderId}/customer-notice`, { method })
  return res.data as CustomerNoticeOut
}

export type OrderUsage = {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  llm_cost: string
}

export async function getOrderUsage(orderId: UUID): Promise<OrderUsage> {
  const res = await apiClient.get(`/store/orders/${orderId}/usage`)
  return res.data as OrderUsage
}
