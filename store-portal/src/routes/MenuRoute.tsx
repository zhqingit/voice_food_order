import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  type MenuItemOut,
  type MenuOut,
  addItemToMenu,
  createMenu,
  createStoreItem,
  deleteMenu,
  deleteStoreItem,
  listMenuItems,
  listMenus,
  listStoreItems,
  removeItemFromMenu,
  setDefaultMenu,
  updateMenu,
  updateStoreItem,
  uploadItemsCsv,
  uploadItemsImage,
} from '../api/menuApi'

// ── CSV template ───────────────────────────────────────────
const CSV_TEMPLATE = `name,alias_name,category,price,price_small,price_medium,price_large,description,ingredient,note,tags,availability
Margherita Pizza,,Pizza,12.99,,,,"Classic tomato sauce and mozzarella",Dough; Tomato; Mozzarella,,Italian,true
Chicken Wings,Buffalo Wings,Appetizer,9.99,7.99,9.99,13.99,"Crispy fried wings with sauce",Chicken; Flour; Hot Sauce,,Spicy; Popular,true
Caesar Salad,,Salad,8.50,,,,"Romaine lettuce with Caesar dressing",Romaine; Parmesan; Croutons,,Healthy,true`

function downloadCsvTemplate() {
  const blob = new Blob([CSV_TEMPLATE], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'menu_items_template.csv'
  a.click()
  URL.revokeObjectURL(url)
}

// ── Item edit modal ────────────────────────────────────────
type ItemFormData = {
  name: string
  alias_name: string
  category: string
  price: string
  price_small: string
  price_medium: string
  price_large: string
  description: string
  ingredient: string
  note: string
  tags: string
  modifiers_json: string
  availability: boolean
}

const EMPTY_FORM: ItemFormData = {
  name: '', alias_name: '', category: '', price: '', price_small: '',
  price_medium: '', price_large: '', description: '', ingredient: '',
  note: '', tags: '', modifiers_json: '', availability: true,
}

function itemToForm(item: MenuItemOut): ItemFormData {
  return {
    name: item.name,
    alias_name: item.alias_name ?? '',
    category: item.category ?? '',
    price: String(item.price),
    price_small: item.price_small != null ? String(item.price_small) : '',
    price_medium: item.price_medium != null ? String(item.price_medium) : '',
    price_large: item.price_large != null ? String(item.price_large) : '',
    description: item.description ?? '',
    ingredient: item.ingredient ?? '',
    note: item.note ?? '',
    tags: (item.tags ?? []).join(', '),
    modifiers_json: item.modifiers ? JSON.stringify(item.modifiers, null, 2) : '',
    availability: item.availability,
  }
}

function ItemModal({
  item,
  form,
  onFormChange,
  onSave,
  onClose,
  saving,
}: {
  item: MenuItemOut | null  // null = create mode
  form: ItemFormData
  onFormChange: (f: ItemFormData) => void
  onSave: () => void
  onClose: () => void
  saving: boolean
}) {
  const set = (key: keyof ItemFormData, value: string | boolean) =>
    onFormChange({ ...form, [key]: value })

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.4)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div
        className="card"
        style={{ width: 640, maxWidth: '90vw', maxHeight: '85vh', overflow: 'auto' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="card-header">
          <h2>{item ? 'Edit Item' : 'New Item'}</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>Close</button>
        </div>
        <form className="card-body" onSubmit={(e) => { e.preventDefault(); onSave() }}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Name *</label>
              <input className="form-input" value={form.name} onChange={(e) => set('name', e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">Alias Name</label>
              <input className="form-input" value={form.alias_name} onChange={(e) => set('alias_name', e.target.value)} placeholder="Alternative name" />
            </div>
            <div className="form-group">
              <label className="form-label">Category</label>
              <input className="form-input" value={form.category} onChange={(e) => set('category', e.target.value)} placeholder="e.g. Appetizer" />
            </div>
            <div className="form-group">
              <label className="form-label">Base Price *</label>
              <input className="form-input" value={form.price} onChange={(e) => set('price', e.target.value)} inputMode="decimal" placeholder="0.00" required />
            </div>
            <div className="form-group">
              <label className="form-label">Price (Small)</label>
              <input className="form-input" value={form.price_small} onChange={(e) => set('price_small', e.target.value)} inputMode="decimal" placeholder="Optional" />
            </div>
            <div className="form-group">
              <label className="form-label">Price (Medium)</label>
              <input className="form-input" value={form.price_medium} onChange={(e) => set('price_medium', e.target.value)} inputMode="decimal" placeholder="Optional" />
            </div>
            <div className="form-group">
              <label className="form-label">Price (Large)</label>
              <input className="form-input" value={form.price_large} onChange={(e) => set('price_large', e.target.value)} inputMode="decimal" placeholder="Optional" />
            </div>
            <div className="form-group">
              <label className="form-label">Tags</label>
              <input className="form-input" value={form.tags} onChange={(e) => set('tags', e.target.value)} placeholder="Spicy, Popular" />
            </div>
            <div className="form-group grid-full">
              <label className="form-label">Description</label>
              <input className="form-input" value={form.description} onChange={(e) => set('description', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Ingredient</label>
              <input className="form-input" value={form.ingredient} onChange={(e) => set('ingredient', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Note</label>
              <input className="form-input" value={form.note} onChange={(e) => set('note', e.target.value)} />
            </div>
            <div className="form-group grid-full">
              <label className="form-label">Modifiers (JSON)</label>
              <textarea className="form-input" value={form.modifiers_json} onChange={(e) => set('modifiers_json', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-check">
                <input type="checkbox" checked={form.availability} onChange={(e) => set('availability', e.target.checked)} />
                Available
              </label>
            </div>
            <div className="flex-end">
              <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? 'Saving...' : (item ? 'Update' : 'Create')}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Rename menu modal ──────────────────────────────────────
function RenameMenuModal({
  menu,
  onSave,
  onClose,
}: {
  menu: MenuOut
  onSave: (name: string) => void
  onClose: () => void
}) {
  const [name, setName] = useState(menu.name)
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.4)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div className="card" style={{ width: 400, maxWidth: '90vw' }} onClick={(e) => e.stopPropagation()}>
        <div className="card-header">
          <h2>Rename Menu</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>Close</button>
        </div>
        <form className="card-body" onSubmit={(e) => { e.preventDefault(); onSave(name) }}>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label className="form-label">Menu Name</label>
            <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div className="flex-end">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary">Save</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main route ─────────────────────────────────────────────
export function MenuRoute(): React.JSX.Element {
  const [error, setError] = useState<string | null>(null)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'pool' | 'menus'>('pool')

  const csvInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)

  // ── Store items pool
  const [poolItems, setPoolItems] = useState<MenuItemOut[]>([])
  const [poolFilter, setPoolFilter] = useState('')
  const [poolCategoryFilter, setPoolCategoryFilter] = useState<string>('')
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [selectedMenuItemIds, setSelectedMenuItemIds] = useState<Set<string>>(new Set())

  // ── Item modal
  const [modalOpen, setModalOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<MenuItemOut | null>(null)
  const [itemForm, setItemForm] = useState<ItemFormData>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  // ── Menus
  const [menus, setMenus] = useState<MenuOut[]>([])
  const [selectedMenuId, setSelectedMenuId] = useState<string | null>(null)
  const [newMenuName, setNewMenuName] = useState('')
  const [renameMenu, setRenameMenu] = useState<MenuOut | null>(null)

  const selectedMenu = useMemo(
    () => menus.find((m) => m.id === selectedMenuId) ?? null,
    [menus, selectedMenuId],
  )

  const defaultMenuId = useMemo(
    () => menus.find((m) => m.active)?.id ?? null,
    [menus],
  )

  // ── Menu items (linked)
  const [menuItems, setMenuItems] = useState<MenuItemOut[]>([])
  const menuItemIds = useMemo(() => new Set(menuItems.map((i) => i.id)), [menuItems])

  // ── Filtered pool
  const categories = useMemo(() => {
    const cats = new Set<string>()
    poolItems.forEach((i) => { if (i.category) cats.add(i.category) })
    return Array.from(cats).sort()
  }, [poolItems])

  const filteredPool = useMemo(() => {
    let items = poolItems
    if (poolCategoryFilter) {
      items = items.filter((i) => i.category === poolCategoryFilter)
    }
    if (poolFilter) {
      const q = poolFilter.toLowerCase()
      items = items.filter((i) =>
        i.name.toLowerCase().includes(q) ||
        (i.alias_name && i.alias_name.toLowerCase().includes(q)) ||
        (i.category && i.category.toLowerCase().includes(q))
      )
    }
    return items
  }, [poolItems, poolFilter, poolCategoryFilter])

  // ── Uploading state
  const [uploading, setUploading] = useState(false)

  // ── Load data
  async function reloadPool(): Promise<void> {
    setPoolItems(await listStoreItems())
  }

  async function reloadMenus(selectId?: string): Promise<void> {
    const data = await listMenus()
    setMenus(data)
    const nextId = selectId ?? selectedMenuId ?? (data[0]?.id ?? null)
    setSelectedMenuId(nextId)
  }

  async function reloadMenuItems(menuId: string): Promise<void> {
    setMenuItems(await listMenuItems(menuId))
  }

  useEffect(() => {
    void (async () => {
      setError(null)
      try {
        await Promise.all([reloadPool(), reloadMenus()])
      } catch {
        setError('Failed to load data')
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedMenuId) { setMenuItems([]); return }
    void (async () => {
      try { await reloadMenuItems(selectedMenuId) } catch { setError('Failed to load menu items') }
    })()
  }, [selectedMenuId])

  // ── Item save
  async function handleSaveItem(): Promise<void> {
    if (!itemForm.name.trim()) return
    const parsedPrice = Number(itemForm.price)
    if (!Number.isFinite(parsedPrice) || parsedPrice < 0) {
      setError('Invalid price'); return
    }
    let modifiers: Record<string, unknown> | null = null
    const trimmed = itemForm.modifiers_json.trim()
    if (trimmed) {
      try { modifiers = JSON.parse(trimmed) } catch {
        setError('Invalid modifiers JSON'); return
      }
    }
    const tags = itemForm.tags.split(',').map((t) => t.trim()).filter(Boolean)
    const parseOpt = (v: string) => {
      const t = v.trim()
      if (!t) return null
      const n = Number(t)
      return Number.isFinite(n) && n >= 0 ? n : null
    }
    const payload: any = {
      name: itemForm.name.trim(),
      price: parsedPrice,
      price_small: parseOpt(itemForm.price_small),
      price_medium: parseOpt(itemForm.price_medium),
      price_large: parseOpt(itemForm.price_large),
      description: itemForm.description.trim() || null,
      availability: itemForm.availability,
      tags: tags.length ? tags : null,
      modifiers,
      alias_name: itemForm.alias_name.trim() || null,
      category: itemForm.category.trim() || null,
      ingredient: itemForm.ingredient.trim() || null,
      note: itemForm.note.trim() || null,
    }
    setSaving(true)
    setError(null)
    try {
      if (editingItem) {
        const updated = await updateStoreItem(editingItem.id, payload)
        setPoolItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
        if (selectedMenuId) await reloadMenuItems(selectedMenuId)
      } else {
        const created = await createStoreItem(payload)
        setPoolItems((prev) => [created, ...prev])
      }
      setModalOpen(false)
      setEditingItem(null)
      setItemForm(EMPTY_FORM)
    } catch {
      setError('Failed to save item')
    } finally {
      setSaving(false)
    }
  }

  function openCreateModal(): void {
    setEditingItem(null)
    setItemForm(EMPTY_FORM)
    setModalOpen(true)
  }

  function openEditModal(item: MenuItemOut): void {
    setEditingItem(item)
    setItemForm(itemToForm(item))
    setModalOpen(true)
  }

  async function handleDeletePoolItem(item: MenuItemOut): Promise<void> {
    if (!window.confirm(`Delete "${item.name}"? This cannot be undone.`)) return
    setError(null)
    try {
      await deleteStoreItem(item.id)
      setPoolItems((prev) => prev.filter((i) => i.id !== item.id))
      setMenuItems((prev) => prev.filter((i) => i.id !== item.id))
    } catch {
      setError('Failed to delete item')
    }
  }

  // ── Batch actions
  function toggleSelectItem(id: string): void {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleSelectAll(): void {
    if (selectedIds.size === filteredPool.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(filteredPool.map((i) => i.id)))
    }
  }

  async function batchDelete(): Promise<void> {
    if (!selectedIds.size) return
    if (!window.confirm(`Delete ${selectedIds.size} item(s)? This cannot be undone.`)) return
    setError(null)
    let failed = 0
    for (const id of selectedIds) {
      try { await deleteStoreItem(id) } catch { failed++ }
    }
    setPoolItems((prev) => prev.filter((i) => !selectedIds.has(i.id)))
    setMenuItems((prev) => prev.filter((i) => !selectedIds.has(i.id)))
    setSelectedIds(new Set())
    if (failed) setError(`Failed to delete ${failed} item(s)`)
  }

  async function batchToggleAvailability(available: boolean): Promise<void> {
    if (!selectedIds.size) return
    setError(null)
    let failed = 0
    for (const id of selectedIds) {
      try { await updateStoreItem(id, { availability: available }) } catch { failed++ }
    }
    setPoolItems((prev) => prev.map((i) =>
      selectedIds.has(i.id) ? { ...i, availability: available } : i
    ))
    setSelectedIds(new Set())
    if (failed) setError(`Failed to update ${failed} item(s)`)
  }

  async function batchAddToMenu(): Promise<void> {
    if (!selectedMenuItemIds.size || !selectedMenuId) return
    setError(null)
    let failed = 0
    for (const id of selectedMenuItemIds) {
      if (menuItemIds.has(id)) continue
      try { await addItemToMenu(selectedMenuId, id) } catch { failed++ }
    }
    await reloadMenuItems(selectedMenuId)
    setSelectedMenuItemIds(new Set())
    if (failed) setError(`Failed to add ${failed} item(s) to menu`)
  }

  // ── Menu item batch actions
  function toggleSelectMenuItem(id: string): void {
    setSelectedMenuItemIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleSelectAllMenuItems(): void {
    if (selectedMenuItemIds.size === poolItems.length) {
      setSelectedMenuItemIds(new Set())
    } else {
      setSelectedMenuItemIds(new Set(poolItems.map((i) => i.id)))
    }
  }

  async function batchRemoveFromMenu(): Promise<void> {
    if (!selectedMenuItemIds.size || !selectedMenuId) return
    if (!window.confirm(`Remove ${selectedMenuItemIds.size} item(s) from this menu?`)) return
    setError(null)
    let failed = 0
    for (const id of selectedMenuItemIds) {
      try { await removeItemFromMenu(selectedMenuId, id) } catch { failed++ }
    }
    setMenuItems((prev) => prev.filter((i) => !selectedMenuItemIds.has(i.id)))
    setSelectedMenuItemIds(new Set())
    if (failed) setError(`Failed to remove ${failed} item(s) from menu`)
  }

  // Clear menu item selection when switching menus
  useEffect(() => {
    setSelectedMenuItemIds(new Set())
  }, [selectedMenuId])

  // ── CSV upload
  async function handleCsvUpload(e: React.ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setUploadMsg(null)
    setUploading(true)
    try {
      const result = await uploadItemsCsv(file)
      await reloadPool()
      if (selectedMenuId) await reloadMenuItems(selectedMenuId)
      const parts = [`Created: ${result.created}, Updated: ${result.updated}`]
      if (result.errors.length) parts.push(`Errors: ${result.errors.slice(0, 3).join('; ')}`)
      setUploadMsg(parts.join('. '))
    } catch {
      setError('CSV upload failed')
    } finally {
      setUploading(false)
      if (csvInputRef.current) csvInputRef.current.value = ''
    }
  }

  // ── Image upload
  async function handleImageUpload(e: React.ChangeEvent<HTMLInputElement>): Promise<void> {
    const files = e.target.files
    if (!files || files.length === 0) return
    setError(null)
    setUploadMsg(null)
    setUploading(true)
    try {
      const result = await uploadItemsImage(files)
      await reloadPool()
      if (selectedMenuId) await reloadMenuItems(selectedMenuId)
      const parts = [`Created: ${result.created}, Updated: ${result.updated}`]
      if (result.errors.length) parts.push(`Errors: ${result.errors.slice(0, 3).join('; ')}`)
      setUploadMsg(parts.join('. '))
    } catch (err: any) {
      setError('Image upload failed: ' + (err?.response?.data?.detail ?? 'Make sure the image is a clear menu photo.'))
    } finally {
      setUploading(false)
      if (imageInputRef.current) imageInputRef.current.value = ''
    }
  }

  // ── Menu handlers
  async function handleCreateMenu(): Promise<void> {
    if (!newMenuName.trim()) return
    setError(null)
    try {
      const isFirst = menus.length === 0
      const created = await createMenu({ name: newMenuName.trim(), active: isFirst })
      setNewMenuName('')
      await reloadMenus(created.id)
    } catch {
      setError('Failed to create menu')
    }
  }

  async function handleSetDefault(menu: MenuOut): Promise<void> {
    setError(null)
    try {
      await setDefaultMenu(menu.id)
      await reloadMenus(menu.id)
    } catch {
      setError('Failed to set default menu')
    }
  }

  async function handleDeleteMenu(menu: MenuOut): Promise<void> {
    if (!window.confirm(`Delete menu "${menu.name}"?`)) return
    setError(null)
    try {
      await deleteMenu(menu.id)
      const next = menus.filter((m) => m.id !== menu.id)
      setMenus(next)
      setSelectedMenuId(next[0]?.id ?? null)
    } catch {
      setError('Failed to delete menu')
    }
  }

  async function handleRenameMenu(name: string): Promise<void> {
    if (!renameMenu || !name.trim()) return
    setError(null)
    try {
      await updateMenu(renameMenu.id, { name: name.trim() })
      await reloadMenus(renameMenu.id)
      setRenameMenu(null)
    } catch {
      setError('Failed to rename menu')
    }
  }

  // ── Link / unlink items
  async function handleAddToMenu(item: MenuItemOut): Promise<void> {
    if (!selectedMenuId) return
    setError(null)
    try {
      await addItemToMenu(selectedMenuId, item.id)
      await reloadMenuItems(selectedMenuId)
    } catch {
      setError('Failed to add item to menu')
    }
  }

  async function handleRemoveFromMenu(item: MenuItemOut): Promise<void> {
    if (!selectedMenuId) return
    setError(null)
    try {
      await removeItemFromMenu(selectedMenuId, item.id)
      setMenuItems((prev) => prev.filter((i) => i.id !== item.id))
    } catch {
      setError('Failed to remove item from menu')
    }
  }

  // ── Render ───────────────────────────────────────────────
  return (
    <>
      <div className="page-header">
        <h1>Menu</h1>
        <p>Manage your items pool and menus</p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
      {uploadMsg && <div className="alert alert-success" style={{ marginBottom: 16 }}>{uploadMsg}<button className="btn btn-ghost btn-sm" style={{ marginLeft: 8 }} onClick={() => setUploadMsg(null)}>dismiss</button></div>}

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--color-border)', marginBottom: 20 }}>
        <button
          className={activeTab === 'pool' ? 'auth-tab active' : 'auth-tab'}
          onClick={() => setActiveTab('pool')}
          style={{ maxWidth: 160 }}
        >
          Items Pool ({poolItems.length})
        </button>
        <button
          className={activeTab === 'menus' ? 'auth-tab active' : 'auth-tab'}
          onClick={() => setActiveTab('menus')}
          style={{ maxWidth: 160 }}
        >
          Menus ({menus.length})
        </button>
      </div>

      {/* ═══════════ Items Pool Tab ═══════════ */}
      {activeTab === 'pool' && (
        <>
          {/* Toolbar */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={openCreateModal}>+ New Item</button>

              <input
                ref={csvInputRef} type="file" accept=".csv"
                style={{ display: 'none' }}
                onChange={(e) => void handleCsvUpload(e)}
              />
              <button className="btn btn-secondary" onClick={() => csvInputRef.current?.click()} disabled={uploading} title="Bulk import or update items from a CSV file. Items are matched by name — existing items get updated, new ones are created.">
                {uploading ? 'Uploading...' : 'Upload CSV'}
              </button>

              <button className="btn btn-secondary" onClick={downloadCsvTemplate} title="Download a sample CSV file with the correct column headers and example data to use as a starting point.">
                Download CSV Template
              </button>

              <input
                ref={imageInputRef} type="file" accept="image/jpeg,image/png,image/webp,application/pdf" multiple
                style={{ display: 'none' }}
                onChange={(e) => void handleImageUpload(e)}
              />
              <button className="btn btn-secondary" onClick={() => imageInputRef.current?.click()} disabled={uploading} title="Upload photos or PDFs of your restaurant menu. AI will automatically extract item names, prices, and categories.">
                {uploading ? 'Processing...' : 'Scan Menu (Image/PDF)'}
              </button>

              <div style={{ flex: 1 }} />

              {/* Category filter */}
              <select
                className="form-select"
                value={poolCategoryFilter}
                onChange={(e) => setPoolCategoryFilter(e.target.value)}
              >
                <option value="">All Categories</option>
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>

              {/* Search */}
              <input
                className="form-input"
                style={{ width: 200 }}
                placeholder="Search items..."
                value={poolFilter}
                onChange={(e) => setPoolFilter(e.target.value)}
              />
            </div>
          </div>

          {/* Batch action bar */}
          {selectedIds.size > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{selectedIds.size} selected</span>
                <div style={{ width: 1, height: 20, background: 'var(--color-border)' }} />
                <button className="btn btn-secondary btn-sm" onClick={() => void batchToggleAvailability(true)}>Set Available</button>
                <button className="btn btn-secondary btn-sm" onClick={() => void batchToggleAvailability(false)}>Set Unavailable</button>
                <button className="btn btn-danger btn-sm" onClick={() => void batchDelete()}>Delete Selected</button>
                <div style={{ flex: 1 }} />
                <button className="btn btn-ghost btn-sm" onClick={() => setSelectedIds(new Set())}>Clear Selection</button>
              </div>
            </div>
          )}

          {/* Items table */}
          <div className="card">
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left' }}>
                    <th style={{ ...thStyle, width: 36 }}>
                      <input
                        type="checkbox"
                        checked={filteredPool.length > 0 && selectedIds.size === filteredPool.length}
                        onChange={toggleSelectAll}
                        style={{ width: 16, height: 16, accentColor: 'var(--color-primary)', cursor: 'pointer' }}
                      />
                    </th>
                    <th style={thStyle}>Name</th>
                    <th style={thStyle}>Category</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Price</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>S</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>M</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>L</th>
                    <th style={thStyle}>Status</th>
                    <th style={thStyle}>Tags</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredPool.map((item) => (
                    <tr
                      key={item.id}
                      style={{
                        borderBottom: '1px solid var(--color-border-light)',
                        cursor: 'pointer',
                        background: selectedIds.has(item.id) ? 'var(--color-primary-light)' : undefined,
                      }}
                      onDoubleClick={() => openEditModal(item)}
                      title="Double-click to edit"
                    >
                      <td style={tdStyle}>
                        <input
                          type="checkbox"
                          checked={selectedIds.has(item.id)}
                          onChange={() => toggleSelectItem(item.id)}
                          onClick={(e) => e.stopPropagation()}
                          style={{ width: 16, height: 16, accentColor: 'var(--color-primary)', cursor: 'pointer' }}
                        />
                      </td>
                      <td style={tdStyle}>
                        <div style={{ fontWeight: 600 }}>{item.name}</div>
                        {item.alias_name && <div style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{item.alias_name}</div>}
                      </td>
                      <td style={tdStyle}>{item.category && <span className="badge badge-submitted">{item.category}</span>}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>${String(item.price)}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--color-text-secondary)' }}>{item.price_small != null ? `$${item.price_small}` : '-'}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--color-text-secondary)' }}>{item.price_medium != null ? `$${item.price_medium}` : '-'}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--color-text-secondary)' }}>{item.price_large != null ? `$${item.price_large}` : '-'}</td>
                      <td style={tdStyle}>
                        <span className={`badge ${item.availability ? 'badge-active' : 'badge-inactive'}`}>
                          {item.availability ? 'Available' : 'Unavailable'}
                        </span>
                      </td>
                      <td style={tdStyle}>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {item.tags?.map((tag) => <span key={tag} className="badge badge-draft">{tag}</span>)}
                        </div>
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                          <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); openEditModal(item) }}>Edit</button>
                          <button className="btn btn-danger btn-sm" onClick={(e) => { e.stopPropagation(); void handleDeletePoolItem(item) }}>Delete</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!filteredPool.length && <div className="empty-state">No items found. Add items manually, upload a CSV, or scan a menu image.</div>}
            </div>
          </div>
        </>
      )}

      {/* ═══════════ Menus Tab ═══════════ */}
      {activeTab === 'menus' && (
        <div style={{ display: 'grid', gridTemplateColumns: '340px 1fr', gap: 20, alignItems: 'start' }}>
          {/* Left: Menus list */}
          <div className="card">
            <div className="card-header">
              <h2>Menus</h2>
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  className="form-input"
                  style={{ flex: 1 }}
                  value={newMenuName}
                  onChange={(e) => setNewMenuName(e.target.value)}
                  placeholder="New menu name"
                  onKeyDown={(e) => { if (e.key === 'Enter') void handleCreateMenu() }}
                />
                <button className="btn btn-primary" onClick={() => void handleCreateMenu()}>Add</button>
              </div>
            </div>
            <div>
              {menus.map((m) => (
                <div
                  key={m.id}
                  className={`list-item ${m.id === selectedMenuId ? 'selected' : ''}`}
                  onClick={() => setSelectedMenuId(m.id)}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: 13 }}>{m.name}</div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                      {m.id === defaultMenuId
                        ? <span className="badge badge-confirmed">Default</span>
                        : <span className="badge badge-inactive">Inactive</span>
                      }
                      <span style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>v{m.version}</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {m.id !== defaultMenuId && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={(e) => { e.stopPropagation(); void handleSetDefault(m) }}
                      >
                        Set Default
                      </button>
                    )}
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={(e) => { e.stopPropagation(); setRenameMenu(m) }}
                    >
                      Rename
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={(e) => { e.stopPropagation(); void handleDeleteMenu(m) }}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
              {!menus.length && <div className="empty-state">No menus yet. Create one above.</div>}
            </div>
          </div>

          {/* Right: All items with in-menu status */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {selectedMenu ? (
              <>
                {/* Batch action bar */}
                {selectedMenuItemIds.size > 0 && (
                  <div className="card">
                    <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{selectedMenuItemIds.size} selected</span>
                      <div style={{ width: 1, height: 20, background: 'var(--color-border)' }} />
                      {/* Show Add if any selected items are not in menu */}
                      {poolItems.filter((i) => selectedMenuItemIds.has(i.id) && !menuItemIds.has(i.id)).length > 0 && (
                        <button className="btn btn-primary btn-sm" onClick={() => void batchAddToMenu()}>Add to Menu</button>
                      )}
                      {/* Show Remove if any selected items are in menu */}
                      {poolItems.filter((i) => selectedMenuItemIds.has(i.id) && menuItemIds.has(i.id)).length > 0 && (
                        <button className="btn btn-danger btn-sm" onClick={() => void batchRemoveFromMenu()}>Remove from Menu</button>
                      )}
                      <div style={{ flex: 1 }} />
                      <button className="btn btn-ghost btn-sm" onClick={() => setSelectedMenuItemIds(new Set())}>Clear Selection</button>
                    </div>
                  </div>
                )}

                {/* All items table sorted by in-menu status */}
                <div className="card">
                  <div className="card-header">
                    <h2>{selectedMenu.name} — {menuItems.length}/{poolItems.length} items in menu</h2>
                  </div>
                  <div style={{ overflowX: 'auto' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                      <thead>
                        <tr style={{ borderBottom: '2px solid var(--color-border)', textAlign: 'left' }}>
                          <th style={{ ...thStyle, width: 36 }}>
                            <input
                              type="checkbox"
                              checked={poolItems.length > 0 && selectedMenuItemIds.size === poolItems.length}
                              onChange={toggleSelectAllMenuItems}
                              style={{ width: 16, height: 16, accentColor: 'var(--color-primary)', cursor: 'pointer' }}
                            />
                          </th>
                          <th style={thStyle}>Name</th>
                          <th style={thStyle}>Category</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>Price</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>S</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>M</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>L</th>
                          <th style={thStyle}>In Menu</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...poolItems]
                          .sort((a, b) => {
                            const aIn = menuItemIds.has(a.id) ? 0 : 1
                            const bIn = menuItemIds.has(b.id) ? 0 : 1
                            if (aIn !== bIn) return aIn - bIn
                            return a.name.localeCompare(b.name)
                          })
                          .map((item) => {
                            const inMenu = menuItemIds.has(item.id)
                            return (
                              <tr
                                key={item.id}
                                style={{
                                  borderBottom: '1px solid var(--color-border-light)',
                                  background: selectedMenuItemIds.has(item.id)
                                    ? 'var(--color-primary-light)'
                                    : !inMenu ? '#fafafa' : undefined,
                                  opacity: inMenu ? 1 : 0.7,
                                }}
                              >
                                <td style={tdStyle}>
                                  <input
                                    type="checkbox"
                                    checked={selectedMenuItemIds.has(item.id)}
                                    onChange={() => toggleSelectMenuItem(item.id)}
                                    style={{ width: 16, height: 16, accentColor: 'var(--color-primary)', cursor: 'pointer' }}
                                  />
                                </td>
                                <td style={tdStyle}>
                                  <div style={{ fontWeight: 600 }}>{item.name}</div>
                                  {item.alias_name && <div style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{item.alias_name}</div>}
                                </td>
                                <td style={tdStyle}>{item.category && <span className="badge badge-submitted">{item.category}</span>}</td>
                                <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>${String(item.price)}</td>
                                <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--color-text-secondary)' }}>{item.price_small != null ? `$${item.price_small}` : '-'}</td>
                                <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--color-text-secondary)' }}>{item.price_medium != null ? `$${item.price_medium}` : '-'}</td>
                                <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--color-text-secondary)' }}>{item.price_large != null ? `$${item.price_large}` : '-'}</td>
                                <td style={tdStyle}>
                                  {inMenu
                                    ? <span className="badge badge-confirmed">In Menu</span>
                                    : <span className="badge badge-inactive">Not in Menu</span>
                                  }
                                </td>
                                <td style={{ ...tdStyle, textAlign: 'right' }}>
                                  {inMenu ? (
                                    <button className="btn btn-danger btn-sm" onClick={() => void handleRemoveFromMenu(item)}>Remove</button>
                                  ) : (
                                    <button className="btn btn-primary btn-sm" onClick={() => void handleAddToMenu(item)}>Add</button>
                                  )}
                                </td>
                              </tr>
                            )
                          })
                        }
                      </tbody>
                    </table>
                    {!poolItems.length && <div className="empty-state">No items in pool. Go to Items Pool tab to add items first.</div>}
                  </div>
                </div>
              </>
            ) : (
              <div className="card">
                <div className="empty-state">Select a menu from the left to manage its items</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Item edit/create modal */}
      {modalOpen && (
        <ItemModal
          item={editingItem}
          form={itemForm}
          onFormChange={setItemForm}
          onSave={() => void handleSaveItem()}
          onClose={() => { setModalOpen(false); setEditingItem(null) }}
          saving={saving}
        />
      )}

      {/* Rename menu modal */}
      {renameMenu && (
        <RenameMenuModal
          menu={renameMenu}
          onSave={(name) => void handleRenameMenu(name)}
          onClose={() => setRenameMenu(null)}
        />
      )}
    </>
  )
}

// ── Table styles ───────────────────────────────────────────
const thStyle: React.CSSProperties = {
  padding: '10px 12px',
  fontSize: 11,
  fontWeight: 600,
  color: '#6b7280',
  textTransform: 'uppercase',
  letterSpacing: '0.5px',
  whiteSpace: 'nowrap',
}

const tdStyle: React.CSSProperties = {
  padding: '10px 12px',
  verticalAlign: 'middle',
}
