import { apiClient } from './client'
import type { Money, UUID } from './types'

export type OrderOut = {
  id: UUID
  store_id: UUID
  user_id: UUID | null
  status: string
  channel: string
  subtotal: Money
  tax: Money
  total: Money
  customer_name: string | null
  user_email: string | null
  notes: string | null
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
