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
  store_id: UUID
  name: string
  alias_name?: string | null
  category?: string | null
  price: Money
  price_small?: Money | null
  price_medium?: Money | null
  price_large?: Money | null
  description: string | null
  ingredient?: string | null
  note?: string | null
  tags: string[] | null
  availability: boolean
  modifiers: Record<string, unknown> | null
}

export type MenuItemCreate = {
  name: string
  price: Money
  price_small?: Money | null
  price_medium?: Money | null
  price_large?: Money | null
  alias_name?: string | null
  category?: string | null
  description?: string | null
  ingredient?: string | null
  note?: string | null
  tags?: string[] | null
  availability?: boolean
  modifiers?: Record<string, unknown> | null
}

export type MenuItemUpdate = Partial<MenuItemCreate>

// ── Menus ───────────────────────────────────────────────

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

export async function setDefaultMenu(menuId: UUID): Promise<MenuOut> {
  const res = await apiClient.post(`/store/menus/${menuId}/set-default`)
  return res.data as MenuOut
}

export async function deleteMenu(menuId: UUID): Promise<void> {
  await apiClient.delete(`/store/menus/${menuId}`)
}

// ── Store Items (pool) ──────────────────────────────────

export async function listStoreItems(): Promise<MenuItemOut[]> {
  const res = await apiClient.get('/store/items')
  return res.data as MenuItemOut[]
}

export type CsvUploadResult = {
  created: number
  updated: number
  errors: string[]
}

export async function uploadItemsCsv(file: File): Promise<CsvUploadResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await apiClient.post('/store/items/upload-csv', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return res.data as CsvUploadResult
}

export async function uploadItemsImage(files: FileList | File[]): Promise<CsvUploadResult> {
  const form = new FormData()
  for (const file of files) {
    form.append('files', file)
  }
  const res = await apiClient.post('/store/items/upload-image', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000, // Gemini processing can take a while with multiple files
  })
  return res.data as CsvUploadResult
}

export async function createStoreItem(payload: MenuItemCreate): Promise<MenuItemOut> {
  const res = await apiClient.post('/store/items', payload)
  return res.data as MenuItemOut
}

export async function updateStoreItem(itemId: UUID, payload: MenuItemUpdate): Promise<MenuItemOut> {
  const res = await apiClient.patch(`/store/items/${itemId}`, payload)
  return res.data as MenuItemOut
}

export async function deleteStoreItem(itemId: UUID): Promise<void> {
  await apiClient.delete(`/store/items/${itemId}`)
}

// ── Menu ↔ Item links ──────────────────────────────────

export async function listMenuItems(menuId: UUID): Promise<MenuItemOut[]> {
  const res = await apiClient.get(`/store/menus/${menuId}/items`)
  return res.data as MenuItemOut[]
}

export async function addItemToMenu(menuId: UUID, itemId: UUID): Promise<void> {
  await apiClient.post(`/store/menus/${menuId}/items/${itemId}`)
}

export async function removeItemFromMenu(menuId: UUID, itemId: UUID): Promise<void> {
  await apiClient.delete(`/store/menus/${menuId}/items/${itemId}`)
}
