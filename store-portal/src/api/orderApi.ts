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
  notes: string | null
  created_at: string
}

export type OrderItemOut = {
  id: UUID
  order_id: UUID
  menu_item_id: UUID
  quantity: number
  price_snapshot: Money
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
