import { apiClient } from './client'
import type { Money, UUID } from './types'

export type MenuOut = {
  id: UUID
  store_id: UUID
  name: string
  active: boolean
  version: number
  updated_at: string
}

export type MenuCreate = {
  name: string
  active?: boolean
}

export type MenuUpdate = {
  name?: string
  active?: boolean
}

export type MenuItemOut = {
  id: UUID
  menu_id: UUID
  name: string
  price: Money
  description: string | null
  tags: string[] | null
  availability: boolean
  modifiers: Record<string, unknown> | null
}

export type MenuItemCreate = {
  name: string
  price: Money
  description?: string | null
  tags?: string[] | null
  availability?: boolean
  modifiers?: Record<string, unknown> | null
}

export type MenuItemUpdate = Partial<MenuItemCreate>

export async function listMenus(): Promise<MenuOut[]> {
  const res = await apiClient.get('/store/menus')
  return res.data as MenuOut[]
}

export async function createMenu(payload: MenuCreate): Promise<MenuOut> {
  const res = await apiClient.post('/store/menus', payload)
  return res.data as MenuOut
}

export async function updateMenu(menuId: UUID, payload: MenuUpdate): Promise<MenuOut> {
  const res = await apiClient.patch(`/store/menus/${menuId}`, payload)
  return res.data as MenuOut
}

export async function deleteMenu(menuId: UUID): Promise<void> {
  await apiClient.delete(`/store/menus/${menuId}`)
}

export async function listMenuItems(menuId: UUID): Promise<MenuItemOut[]> {
  const res = await apiClient.get(`/store/menus/${menuId}/items`)
  return res.data as MenuItemOut[]
}

export async function createMenuItem(menuId: UUID, payload: MenuItemCreate): Promise<MenuItemOut> {
  const res = await apiClient.post(`/store/menus/${menuId}/items`, payload)
  return res.data as MenuItemOut
}

export async function updateMenuItem(
  menuId: UUID,
  itemId: UUID,
  payload: MenuItemUpdate,
): Promise<MenuItemOut> {
  const res = await apiClient.patch(`/store/menus/${menuId}/items/${itemId}`, payload)
  return res.data as MenuItemOut
}

export async function deleteMenuItem(menuId: UUID, itemId: UUID): Promise<void> {
  await apiClient.delete(`/store/menus/${menuId}/items/${itemId}`)
}
