import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import type { TFunction } from 'i18next'
import {
  type MenuItemOut,
  type MenuItemVariantOut,
  type MenuOut,
  addItemToMenu,
  createItemVariant,
  createMenu,
  createStoreItem,
  deleteItemVariant,
  deleteMenu,
  deleteStoreItem,
  listItemVariants,
  listMenuItems,
  listMenus,
  listStoreItems,
  removeItemFromMenu,
  setDefaultMenu,
  updateItemVariant,
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
  const { t } = useTranslation()
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
          <h2>{item ? t('menu.editItem') : t('menu.newItem')}</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>{t('menu.close')}</button>
        </div>
        <form className="card-body" onSubmit={(e) => { e.preventDefault(); onSave() }}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">{t('menu.name')} *</label>
              <input className="form-input" value={form.name} onChange={(e) => set('name', e.target.value)} required />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.aliasName')}</label>
              <input className="form-input" value={form.alias_name} onChange={(e) => set('alias_name', e.target.value)} placeholder={t('menu.aliasPlaceholder')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.category')}</label>
              <input className="form-input" value={form.category} onChange={(e) => set('category', e.target.value)} placeholder={t('menu.categoryPlaceholder')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.basePrice')} *</label>
              <input className="form-input" value={form.price} onChange={(e) => set('price', e.target.value)} inputMode="decimal" placeholder="0.00" required />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.priceSmall')}</label>
              <input className="form-input" value={form.price_small} onChange={(e) => set('price_small', e.target.value)} inputMode="decimal" placeholder={t('menu.optional')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.priceMedium')}</label>
              <input className="form-input" value={form.price_medium} onChange={(e) => set('price_medium', e.target.value)} inputMode="decimal" placeholder={t('menu.optional')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.priceLarge')}</label>
              <input className="form-input" value={form.price_large} onChange={(e) => set('price_large', e.target.value)} inputMode="decimal" placeholder={t('menu.optional')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.tags')}</label>
              <input className="form-input" value={form.tags} onChange={(e) => set('tags', e.target.value)} placeholder={t('menu.tagsPlaceholder')} />
            </div>
            <div className="form-group grid-full">
              <label className="form-label">{t('menu.description')}</label>
              <input className="form-input" value={form.description} onChange={(e) => set('description', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.ingredient')}</label>
              <input className="form-input" value={form.ingredient} onChange={(e) => set('ingredient', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.note')}</label>
              <input className="form-input" value={form.note} onChange={(e) => set('note', e.target.value)} />
            </div>
            <div className="form-group grid-full">
              <label className="form-label">{t('menu.modifiersJson')}</label>
              <textarea className="form-input" value={form.modifiers_json} onChange={(e) => set('modifiers_json', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-check">
                <input type="checkbox" checked={form.availability} onChange={(e) => set('availability', e.target.checked)} />
                {t('common.available')}
              </label>
            </div>
            {item && (
              <div className="form-group grid-full">
                <label className="form-label">{t('menu.variants')}</label>
                <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '0 0 8px' }}>
                  {t('menu.variantsHint')}
                </p>
                <VariantsEditor itemId={item.id} />
              </div>
            )}
            {!item && (
              <div className="form-group grid-full">
                <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: 0, fontStyle: 'italic' }}>
                  {t('menu.variantsHintNew')}
                </p>
              </div>
            )}
            <div className="flex-end">
              <button type="button" className="btn btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
              <button type="submit" className="btn btn-primary" disabled={saving}>
                {saving ? t('menu.saving') : (item ? t('menu.update') : t('menu.create'))}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Variants editor (sub-panel in the Item modal) ─────────────
function VariantsEditor({ itemId }: { itemId: string }): React.JSX.Element {
  const { t } = useTranslation()
  const [variants, setVariants] = useState<MenuItemVariantOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [newName, setNewName] = useState('')
  const [newPrice, setNewPrice] = useState('')
  const [busy, setBusy] = useState(false)

  async function load(): Promise<void> {
    setLoading(true)
    setError(null)
    try {
      setVariants(await listItemVariants(itemId))
    } catch {
      setError(t('menu.variantsLoadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [itemId])

  async function handleAdd(): Promise<void> {
    const name = newName.trim()
    const price = Number(newPrice)
    if (!name) { setError(t('menu.nameRequired')); return }
    if (!Number.isFinite(price) || price < 0) { setError(t('menu.priceNonNegative')); return }
    setBusy(true)
    setError(null)
    try {
      await createItemVariant(itemId, { name, price })
      setNewName('')
      setNewPrice('')
      await load()
    } catch {
      setError(t('menu.variantAddFailed'))
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(id: string): Promise<void> {
    if (!window.confirm(t('menu.variantDeleteConfirm'))) return
    setBusy(true)
    try {
      await deleteItemVariant(itemId, id)
      await load()
    } catch {
      setError(t('menu.variantDeleteFailed'))
    } finally {
      setBusy(false)
    }
  }

  async function handleUpdate(id: string, patch: { name?: string; price?: number; availability?: boolean; is_default?: boolean }): Promise<void> {
    setBusy(true)
    try {
      await updateItemVariant(itemId, id, patch)
      await load()
    } catch {
      setError(t('menu.variantUpdateFailed'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ border: '1px solid var(--color-border)', borderRadius: 8, padding: 10, background: '#fafafa' }}>
      {error && <div className="alert alert-error" style={{ marginBottom: 8 }}>{error}</div>}

      {loading ? (
        <div style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>{t('common.loading')}</div>
      ) : (
        <>
          {variants.length === 0 && (
            <div style={{ fontSize: 12, color: 'var(--color-text-secondary)', marginBottom: 8, fontStyle: 'italic' }}>
              {t('menu.noVariants')}
            </div>
          )}

          {variants.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px 70px 70px 60px', gap: 8, fontSize: 12, fontWeight: 600, color: 'var(--color-text-secondary)', marginBottom: 4 }}>
              <div>{t('menu.colName')}</div>
              <div style={{ textAlign: 'right' }}>{t('menu.colPrice')}</div>
              <div style={{ textAlign: 'center' }}>{t('menu.colDefault')}</div>
              <div style={{ textAlign: 'center' }}>{t('menu.colAvailable')}</div>
              <div></div>
            </div>
          )}

          {variants.map((v) => (
            <div key={v.id} style={{ display: 'grid', gridTemplateColumns: '1fr 100px 70px 70px 60px', gap: 8, alignItems: 'center', paddingBottom: 6 }}>
              <input
                className="form-input"
                defaultValue={v.name}
                style={{ fontSize: 13 }}
                onBlur={(e) => {
                  const next = e.target.value.trim()
                  if (next && next !== v.name) void handleUpdate(v.id, { name: next })
                }}
              />
              <input
                className="form-input"
                defaultValue={String(v.price)}
                inputMode="decimal"
                style={{ fontSize: 13, textAlign: 'right' }}
                onBlur={(e) => {
                  const next = Number(e.target.value)
                  if (Number.isFinite(next) && next >= 0 && next !== Number(v.price)) {
                    void handleUpdate(v.id, { price: next })
                  }
                }}
              />
              <label style={{ display: 'flex', justifyContent: 'center' }}>
                <input
                  type="radio"
                  name={`default-${itemId}`}
                  checked={v.is_default}
                  onChange={() => void handleUpdate(v.id, { is_default: true })}
                  style={{ cursor: 'pointer' }}
                />
              </label>
              <label style={{ display: 'flex', justifyContent: 'center' }}>
                <input
                  type="checkbox"
                  checked={v.availability}
                  onChange={(e) => void handleUpdate(v.id, { availability: e.target.checked })}
                  style={{ cursor: 'pointer' }}
                />
              </label>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => void handleDelete(v.id)}
                disabled={busy}
                title={t('menu.variantDeleteTitle')}
              >
                ✕
              </button>
            </div>
          ))}

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 100px auto', gap: 8, alignItems: 'center', marginTop: 8, paddingTop: 8, borderTop: '1px dashed var(--color-border)' }}>
            <input
              className="form-input"
              placeholder={t('menu.variantNamePlaceholder')}
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              style={{ fontSize: 13 }}
            />
            <input
              className="form-input"
              placeholder="0.00"
              inputMode="decimal"
              value={newPrice}
              onChange={(e) => setNewPrice(e.target.value)}
              style={{ fontSize: 13, textAlign: 'right' }}
            />
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => void handleAdd()}
              disabled={busy || !newName.trim() || !newPrice}
            >
              {t('menu.addBtn')}
            </button>
          </div>
        </>
      )}
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
  const { t } = useTranslation()
  const [name, setName] = useState(menu.name)
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.4)', display: 'flex',
      alignItems: 'center', justifyContent: 'center',
    }} onClick={onClose}>
      <div className="card" style={{ width: 400, maxWidth: '90vw' }} onClick={(e) => e.stopPropagation()}>
        <div className="card-header">
          <h2>{t('menu.renameMenuTitle')}</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>{t('menu.close')}</button>
        </div>
        <form className="card-body" onSubmit={(e) => { e.preventDefault(); onSave(name) }}>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label className="form-label">{t('menu.menuName')}</label>
            <input className="form-input" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div className="flex-end">
            <button type="button" className="btn btn-secondary" onClick={onClose}>{t('common.cancel')}</button>
            <button type="submit" className="btn btn-primary">{t('common.save')}</button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main route ─────────────────────────────────────────────
export function MenuRoute(): React.JSX.Element {
  const { t } = useTranslation()
  const [error, setError] = useState<string | null>(null)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'pool' | 'menus'>('pool')

  const csvInputRef = useRef<HTMLInputElement>(null)
  const imageInputRef = useRef<HTMLInputElement>(null)

  // ── Store items pool
  const [poolItems, setPoolItems] = useState<MenuItemOut[]>([])
  const [poolFilter, setPoolFilter] = useState('')
  const [poolCategoryFilter, setPoolCategoryFilter] = useState<string>('')
  const [poolAvailabilityFilter, setPoolAvailabilityFilter] = useState<'all' | 'available' | 'unavailable'>('all')
  const [poolSortKey, setPoolSortKey] = useState<'name' | 'category' | 'price' | 'availability'>('name')
  const [poolSortDir, setPoolSortDir] = useState<'asc' | 'desc'>('asc')
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
  // Dedupe categories case-insensitively (treat "Beverages" and "beverages" as
  // one bucket). Keep the first-seen casing as the display label.
  const categories = useMemo(() => {
    const byKey = new Map<string, string>()
    for (const i of poolItems) {
      const raw = (i.category ?? '').trim()
      if (!raw) continue
      const key = raw.toLowerCase()
      if (!byKey.has(key)) byKey.set(key, raw)
    }
    return Array.from(byKey.values()).sort((a, b) => a.localeCompare(b))
  }, [poolItems])

  const filteredPool = useMemo(() => {
    let items = poolItems
    if (poolCategoryFilter) {
      const want = poolCategoryFilter.trim().toLowerCase()
      items = items.filter((i) => (i.category ?? '').trim().toLowerCase() === want)
    }
    if (poolAvailabilityFilter !== 'all') {
      const want = poolAvailabilityFilter === 'available'
      items = items.filter((i) => Boolean(i.availability) === want)
    }
    if (poolFilter) {
      const q = poolFilter.toLowerCase()
      items = items.filter((i) =>
        i.name.toLowerCase().includes(q) ||
        (i.alias_name && i.alias_name.toLowerCase().includes(q)) ||
        (i.category && i.category.toLowerCase().includes(q))
      )
    }
    const dir = poolSortDir === 'asc' ? 1 : -1
    const sorted = [...items].sort((a, b) => {
      switch (poolSortKey) {
        case 'price': {
          const pa = Number(a.price ?? 0)
          const pb = Number(b.price ?? 0)
          return (pa - pb) * dir
        }
        case 'category': {
          const ca = (a.category ?? '').toLowerCase()
          const cb = (b.category ?? '').toLowerCase()
          if (ca !== cb) return ca.localeCompare(cb) * dir
          return a.name.localeCompare(b.name)
        }
        case 'availability': {
          const av = (a.availability ? 1 : 0) - (b.availability ? 1 : 0)
          if (av !== 0) return av * dir
          return a.name.localeCompare(b.name)
        }
        case 'name':
        default:
          return a.name.localeCompare(b.name) * dir
      }
    })
    return sorted
  }, [poolItems, poolFilter, poolCategoryFilter, poolAvailabilityFilter, poolSortKey, poolSortDir])

  function togglePoolSort(key: 'name' | 'category' | 'price' | 'availability'): void {
    if (poolSortKey === key) {
      setPoolSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setPoolSortKey(key)
      setPoolSortDir('asc')
    }
  }

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
        setError(t('menu.failedLoadData'))
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedMenuId) { setMenuItems([]); return }
    void (async () => {
      try { await reloadMenuItems(selectedMenuId) } catch { setError(t('menu.failedLoadMenuItems')) }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedMenuId])

  // ── Item save
  async function handleSaveItem(): Promise<void> {
    if (!itemForm.name.trim()) return
    const parsedPrice = Number(itemForm.price)
    if (!Number.isFinite(parsedPrice) || parsedPrice < 0) {
      setError(t('menu.invalidPrice')); return
    }
    let modifiers: Record<string, unknown> | null = null
    const trimmed = itemForm.modifiers_json.trim()
    if (trimmed) {
      try { modifiers = JSON.parse(trimmed) } catch {
        setError(t('menu.invalidModifiers')); return
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
      setError(t('menu.failedSaveItem'))
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
    if (!window.confirm(t('menu.deletePoolItemConfirm', { name: item.name }))) return
    setError(null)
    try {
      await deleteStoreItem(item.id)
      setPoolItems((prev) => prev.filter((i) => i.id !== item.id))
      setMenuItems((prev) => prev.filter((i) => i.id !== item.id))
    } catch {
      setError(t('menu.failedDeleteItem'))
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
    if (!window.confirm(t('menu.deleteCountConfirm', { count: selectedIds.size }))) return
    setError(null)
    let failed = 0
    for (const id of selectedIds) {
      try { await deleteStoreItem(id) } catch { failed++ }
    }
    setPoolItems((prev) => prev.filter((i) => !selectedIds.has(i.id)))
    setMenuItems((prev) => prev.filter((i) => !selectedIds.has(i.id)))
    setSelectedIds(new Set())
    if (failed) setError(t('menu.failedDeleteCount', { count: failed }))
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
    if (failed) setError(t('menu.failedUpdateCount', { count: failed }))
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
    if (failed) setError(t('menu.failedAddCount', { count: failed }))
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
    if (!window.confirm(t('menu.removeCountConfirm', { count: selectedMenuItemIds.size }))) return
    setError(null)
    let failed = 0
    for (const id of selectedMenuItemIds) {
      try { await removeItemFromMenu(selectedMenuId, id) } catch { failed++ }
    }
    setMenuItems((prev) => prev.filter((i) => !selectedMenuItemIds.has(i.id)))
    setSelectedMenuItemIds(new Set())
    if (failed) setError(t('menu.failedRemoveCount', { count: failed }))
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
      const parts = [t('menu.uploadCreatedUpdated', { created: result.created, updated: result.updated })]
      if (result.errors.length) parts.push(t('menu.uploadErrorList', { details: result.errors.slice(0, 3).join('; ') }))
      setUploadMsg(parts.join('. '))
    } catch {
      setError(t('menu.uploadFailed'))
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
      const parts = [t('menu.uploadCreatedUpdated', { created: result.created, updated: result.updated })]
      if (result.errors.length) parts.push(t('menu.uploadErrorList', { details: result.errors.slice(0, 3).join('; ') }))
      setUploadMsg(parts.join('. '))
    } catch (err: any) {
      setError(t('menu.imageUploadFailed', { detail: err?.response?.data?.detail ?? t('menu.imageUploadHint') }))
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
      setError(t('menu.failedCreateMenu'))
    }
  }

  async function handleSetDefault(menu: MenuOut): Promise<void> {
    setError(null)
    try {
      await setDefaultMenu(menu.id)
      await reloadMenus(menu.id)
    } catch {
      setError(t('menu.failedSetDefault'))
    }
  }

  async function handleDeleteMenu(menu: MenuOut): Promise<void> {
    if (!window.confirm(t('menu.deleteMenuConfirm', { name: menu.name }))) return
    setError(null)
    try {
      await deleteMenu(menu.id)
      const next = menus.filter((m) => m.id !== menu.id)
      setMenus(next)
      setSelectedMenuId(next[0]?.id ?? null)
    } catch {
      setError(t('menu.failedDeleteMenu'))
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
      setError(t('menu.failedRenameMenu'))
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
      setError(t('menu.failedAddToMenu'))
    }
  }

  async function handleRemoveFromMenu(item: MenuItemOut): Promise<void> {
    if (!selectedMenuId) return
    setError(null)
    try {
      await removeItemFromMenu(selectedMenuId, item.id)
      setMenuItems((prev) => prev.filter((i) => i.id !== item.id))
    } catch {
      setError(t('menu.failedRemoveFromMenu'))
    }
  }

  // ── Render ───────────────────────────────────────────────
  return (
    <>
      <div className="page-header">
        <h1>{t('menu.header')}</h1>
        <p>{t('menu.headerSubtitle')}</p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
      {uploadMsg && <div className="alert alert-success" style={{ marginBottom: 16 }}>{uploadMsg}<button className="btn btn-ghost btn-sm" style={{ marginLeft: 8 }} onClick={() => setUploadMsg(null)}>{t('menu.dismiss')}</button></div>}

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--color-border)', marginBottom: 20 }}>
        <button
          className={activeTab === 'pool' ? 'auth-tab active' : 'auth-tab'}
          onClick={() => setActiveTab('pool')}
          style={{ maxWidth: 160 }}
        >
          {filteredPool.length === poolItems.length
            ? t('menu.itemsPoolCount', { count: poolItems.length })
            : t('menu.tabPoolFiltered', { shown: filteredPool.length, total: poolItems.length })}
        </button>
        <button
          className={activeTab === 'menus' ? 'auth-tab active' : 'auth-tab'}
          onClick={() => setActiveTab('menus')}
          style={{ maxWidth: 160 }}
        >
          {t('menu.tabMenusCount', { count: menus.length })}
        </button>
      </div>

      {/* ═══════════ Items Pool Tab ═══════════ */}
      {activeTab === 'pool' && (
        <>
          {/* Toolbar */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <button className="btn btn-primary" onClick={openCreateModal}>{t('menu.newItemBtn')}</button>

              <input
                ref={csvInputRef} type="file" accept=".csv"
                style={{ display: 'none' }}
                onChange={(e) => void handleCsvUpload(e)}
              />
              <button className="btn btn-secondary" onClick={() => csvInputRef.current?.click()} disabled={uploading} title={t('menu.uploadCsvTitle')}>
                {uploading ? t('menu.uploading') : t('menu.uploadCsv')}
              </button>

              <button className="btn btn-secondary" onClick={downloadCsvTemplate} title={t('menu.downloadCsvTemplateTitle')}>
                {t('menu.downloadCsvTemplate')}
              </button>

              <input
                ref={imageInputRef} type="file" accept="image/jpeg,image/png,image/webp,application/pdf" multiple
                style={{ display: 'none' }}
                onChange={(e) => void handleImageUpload(e)}
              />
              <button className="btn btn-secondary" onClick={() => imageInputRef.current?.click()} disabled={uploading} title={t('menu.scanMenuTitle')}>
                {uploading ? t('menu.processing') : t('menu.scanMenu')}
              </button>

              <div style={{ flex: 1 }} />

              {/* Category filter */}
              <select
                className="form-select"
                value={poolCategoryFilter}
                onChange={(e) => setPoolCategoryFilter(e.target.value)}
                title={t('menu.filterCategoryTitle')}
              >
                <option value="">{t('menu.allCategories')}</option>
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>

              {/* Availability filter */}
              <select
                className="form-select"
                value={poolAvailabilityFilter}
                onChange={(e) => setPoolAvailabilityFilter(e.target.value as 'all' | 'available' | 'unavailable')}
                title={t('menu.filterAvailabilityTitle')}
              >
                <option value="all">{t('menu.allItems')}</option>
                <option value="available">{t('common.available')}</option>
                <option value="unavailable">{t('common.unavailable')}</option>
              </select>

              {/* Search */}
              <input
                className="form-input"
                style={{ width: 220 }}
                placeholder={t('menu.searchPlaceholder')}
                value={poolFilter}
                onChange={(e) => setPoolFilter(e.target.value)}
              />

              {(poolFilter || poolCategoryFilter || poolAvailabilityFilter !== 'all') && (
                <button
                  className="btn btn-ghost btn-sm"
                  onClick={() => {
                    setPoolFilter('')
                    setPoolCategoryFilter('')
                    setPoolAvailabilityFilter('all')
                  }}
                  title={t('menu.clearFiltersTitle')}
                >
                  {t('menu.clearFilters')}
                </button>
              )}
            </div>
          </div>

          {/* Batch action bar */}
          {selectedIds.size > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="card-body" style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <span style={{ fontWeight: 600, fontSize: 13 }}>{t('menu.selectedCount', { count: selectedIds.size })}</span>
                <div style={{ width: 1, height: 20, background: 'var(--color-border)' }} />
                <button className="btn btn-secondary btn-sm" onClick={() => void batchToggleAvailability(true)}>{t('menu.setAvailable')}</button>
                <button className="btn btn-secondary btn-sm" onClick={() => void batchToggleAvailability(false)}>{t('menu.setUnavailable')}</button>
                <button className="btn btn-danger btn-sm" onClick={() => void batchDelete()}>{t('menu.deleteSelected')}</button>
                <div style={{ flex: 1 }} />
                <button className="btn btn-ghost btn-sm" onClick={() => setSelectedIds(new Set())}>{t('menu.clearSelection')}</button>
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
                    <SortableTh label={t('menu.colName')} sortKey="name" active={poolSortKey} dir={poolSortDir} onToggle={togglePoolSort} t={t} />
                    <SortableTh label={t('menu.category')} sortKey="category" active={poolSortKey} dir={poolSortDir} onToggle={togglePoolSort} t={t} />
                    <SortableTh label={t('menu.colPrice')} sortKey="price" active={poolSortKey} dir={poolSortDir} onToggle={togglePoolSort} align="right" t={t} />
                    <th style={{ ...thStyle, textAlign: 'right' }}>S</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>M</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>L</th>
                    <SortableTh label={t('menu.colStatus')} sortKey="availability" active={poolSortKey} dir={poolSortDir} onToggle={togglePoolSort} t={t} />
                    <th style={thStyle}>{t('menu.colTags')}</th>
                    <th style={{ ...thStyle, textAlign: 'right' }}>{t('menu.colActions')}</th>
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
                      title={t('menu.doubleClickEdit')}
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
                        <div style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 6 }}>
                          {item.name}
                          {item.variants && item.variants.length > 0 && (
                            <span
                              className="badge badge-draft"
                              title={item.variants.map((v) => `${v.name}: $${v.price}`).join(' · ')}
                              style={{ fontSize: 10 }}
                            >
                              {t(item.variants.length === 1 ? 'menu.optionsOne' : 'menu.optionsMany', { count: item.variants.length })}
                            </span>
                          )}
                        </div>
                        {item.alias_name && <div style={{ fontSize: 11, color: 'var(--color-text-secondary)' }}>{item.alias_name}</div>}
                      </td>
                      <td style={tdStyle}>{item.category && <span className="badge badge-submitted">{item.category}</span>}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', fontWeight: 600 }}>${String(item.price)}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--color-text-secondary)' }}>{item.price_small != null ? `$${item.price_small}` : '-'}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--color-text-secondary)' }}>{item.price_medium != null ? `$${item.price_medium}` : '-'}</td>
                      <td style={{ ...tdStyle, textAlign: 'right', color: 'var(--color-text-secondary)' }}>{item.price_large != null ? `$${item.price_large}` : '-'}</td>
                      <td style={tdStyle}>
                        <span className={`badge ${item.availability ? 'badge-active' : 'badge-inactive'}`}>
                          {item.availability ? t('common.available') : t('common.unavailable')}
                        </span>
                      </td>
                      <td style={tdStyle}>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {item.tags?.map((tag) => <span key={tag} className="badge badge-draft">{tag}</span>)}
                        </div>
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                          <button className="btn btn-secondary btn-sm" onClick={(e) => { e.stopPropagation(); openEditModal(item) }}>{t('common.edit')}</button>
                          <button className="btn btn-danger btn-sm" onClick={(e) => { e.stopPropagation(); void handleDeletePoolItem(item) }}>{t('common.delete')}</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!filteredPool.length && <div className="empty-state">{t('menu.noItemsFound')}</div>}
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
              <h2>{t('menu.menus')}</h2>
            </div>
            <div className="card-body">
              <div style={{ display: 'flex', gap: 8 }}>
                <input
                  className="form-input"
                  style={{ flex: 1 }}
                  value={newMenuName}
                  onChange={(e) => setNewMenuName(e.target.value)}
                  placeholder={t('menu.newMenuName')}
                  onKeyDown={(e) => { if (e.key === 'Enter') void handleCreateMenu() }}
                />
                <button className="btn btn-primary" onClick={() => void handleCreateMenu()}>{t('common.add')}</button>
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
                        ? <span className="badge badge-confirmed">{t('common.default')}</span>
                        : <span className="badge badge-inactive">{t('common.inactive')}</span>
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
                        {t('menu.setDefault')}
                      </button>
                    )}
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={(e) => { e.stopPropagation(); setRenameMenu(m) }}
                    >
                      {t('menu.rename')}
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={(e) => { e.stopPropagation(); void handleDeleteMenu(m) }}
                    >
                      {t('common.delete')}
                    </button>
                  </div>
                </div>
              ))}
              {!menus.length && <div className="empty-state">{t('menu.noMenusYet')}</div>}
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
                      <span style={{ fontWeight: 600, fontSize: 13 }}>{t('menu.selectedCount', { count: selectedMenuItemIds.size })}</span>
                      <div style={{ width: 1, height: 20, background: 'var(--color-border)' }} />
                      {/* Show Add if any selected items are not in menu */}
                      {poolItems.filter((i) => selectedMenuItemIds.has(i.id) && !menuItemIds.has(i.id)).length > 0 && (
                        <button className="btn btn-primary btn-sm" onClick={() => void batchAddToMenu()}>{t('menu.addToMenu')}</button>
                      )}
                      {/* Show Remove if any selected items are in menu */}
                      {poolItems.filter((i) => selectedMenuItemIds.has(i.id) && menuItemIds.has(i.id)).length > 0 && (
                        <button className="btn btn-danger btn-sm" onClick={() => void batchRemoveFromMenu()}>{t('menu.removeFromMenuBtn')}</button>
                      )}
                      <div style={{ flex: 1 }} />
                      <button className="btn btn-ghost btn-sm" onClick={() => setSelectedMenuItemIds(new Set())}>{t('menu.clearSelection')}</button>
                    </div>
                  </div>
                )}

                {/* All items table sorted by in-menu status */}
                <div className="card">
                  <div className="card-header">
                    <h2>{t('menu.menuItemsHeader', { name: selectedMenu.name, count: menuItems.length, total: poolItems.length })}</h2>
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
                          <th style={thStyle}>{t('menu.colName')}</th>
                          <th style={thStyle}>{t('menu.category')}</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>{t('menu.colPrice')}</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>S</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>M</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>L</th>
                          <th style={thStyle}>{t('menu.inMenuLabel')}</th>
                          <th style={{ ...thStyle, textAlign: 'right' }}>{t('menu.colActions')}</th>
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
                                    ? <span className="badge badge-confirmed">{t('menu.inMenuLabel')}</span>
                                    : <span className="badge badge-inactive">{t('menu.notInMenuLabel')}</span>
                                  }
                                </td>
                                <td style={{ ...tdStyle, textAlign: 'right' }}>
                                  {inMenu ? (
                                    <button className="btn btn-danger btn-sm" onClick={() => void handleRemoveFromMenu(item)}>{t('common.remove')}</button>
                                  ) : (
                                    <button className="btn btn-primary btn-sm" onClick={() => void handleAddToMenu(item)}>{t('common.add')}</button>
                                  )}
                                </td>
                              </tr>
                            )
                          })
                        }
                      </tbody>
                    </table>
                    {!poolItems.length && <div className="empty-state">{t('menu.noItemsInPool')}</div>}
                  </div>
                </div>
              </>
            ) : (
              <div className="card">
                <div className="empty-state">{t('menu.selectMenuPrompt')}</div>
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

type PoolSortKey = 'name' | 'category' | 'price' | 'availability'

function SortableTh({
  label,
  sortKey,
  active,
  dir,
  onToggle,
  align,
  t,
}: {
  label: string
  sortKey: PoolSortKey
  active: PoolSortKey
  dir: 'asc' | 'desc'
  onToggle: (key: PoolSortKey) => void
  align?: 'left' | 'right'
  t: TFunction
}): React.JSX.Element {
  const isActive = active === sortKey
  const arrow = isActive ? (dir === 'asc' ? '▲' : '▼') : '↕'
  return (
    <th
      style={{
        ...thStyle,
        textAlign: align ?? 'left',
        cursor: 'pointer',
        userSelect: 'none',
        color: isActive ? 'var(--color-primary)' : thStyle.color,
      }}
      onClick={() => onToggle(sortKey)}
      title={t('menu.sortByTitle', { field: label.toLowerCase() })}
    >
      {label}
      <span style={{ marginLeft: 4, fontSize: 10, opacity: isActive ? 1 : 0.4 }}>{arrow}</span>
    </th>
  )
}

const tdStyle: React.CSSProperties = {
  padding: '10px 12px',
  verticalAlign: 'middle',
}
