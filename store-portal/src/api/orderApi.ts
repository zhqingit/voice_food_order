import { apiClient } from './client'
import type { Money, UUID } from './types'

export type OrderOut = {
  id: UUID
  short_code: string
  code_day: string
  store_id: UUID
  user_id: UUID | null
  status: string
  payment_status: string
  channel: string
  subtotal: Money
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
