import React, { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
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
} from '../api/menuApi'

export function MenuRoute(): React.JSX.Element {
  const { t } = useTranslation()
  const [error, setError] = useState<string | null>(null)
  const [uploadMsg, setUploadMsg] = useState<string | null>(null)
  const csvInputRef = useRef<HTMLInputElement>(null)

  // ── Store items pool ──────────────────────────────────
  const [poolItems, setPoolItems] = useState<MenuItemOut[]>([])
  const [editingItemId, setEditingItemId] = useState<string | null>(null)
  const [itemName, setItemName] = useState('')
  const [itemAliasName, setItemAliasName] = useState('')
  const [itemCategory, setItemCategory] = useState('')
  const [itemPrice, setItemPrice] = useState('')
  const [itemPriceSmall, setItemPriceSmall] = useState('')
  const [itemPriceMedium, setItemPriceMedium] = useState('')
  const [itemPriceLarge, setItemPriceLarge] = useState('')
  const [itemDesc, setItemDesc] = useState('')
  const [itemIngredient, setItemIngredient] = useState('')
  const [itemNote, setItemNote] = useState('')
  const [itemAvailable, setItemAvailable] = useState(true)
  const [itemTags, setItemTags] = useState('')
  const [itemModifiersJson, setItemModifiersJson] = useState('')

  // ── Menus ─────────────────────────────────────────────
  const [menus, setMenus] = useState<MenuOut[]>([])
  const [selectedMenuId, setSelectedMenuId] = useState<string | null>(null)
  const [newMenuName, setNewMenuName] = useState('')

  const selectedMenu = useMemo(
    () => menus.find((m) => m.id === selectedMenuId) ?? null,
    [menus, selectedMenuId],
  )

  // The default menu is the first active one (matches voice pipeline behavior)
  const defaultMenuId = useMemo(
    () => menus.find((m) => m.active)?.id ?? null,
    [menus],
  )

  // ── Menu items (linked) ───────────────────────────────
  const [menuItems, setMenuItems] = useState<MenuItemOut[]>([])
  const menuItemIds = useMemo(() => new Set(menuItems.map((i) => i.id)), [menuItems])

  // ── Load data ─────────────────────────────────────────

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
  }, [selectedMenuId])

  // ── Item form helpers ─────────────────────────────────

  function resetItemForm(): void {
    setEditingItemId(null)
    setItemName('')
    setItemAliasName('')
    setItemCategory('')
    setItemPrice('')
    setItemPriceSmall('')
    setItemPriceMedium('')
    setItemPriceLarge('')
    setItemDesc('')
    setItemIngredient('')
    setItemNote('')
    setItemAvailable(true)
    setItemTags('')
    setItemModifiersJson('')
  }

  function handleEditItem(item: MenuItemOut): void {
    setEditingItemId(item.id)
    setItemName(item.name)
    setItemAliasName(item.alias_name ?? '')
    setItemCategory(item.category ?? '')
    setItemPrice(String(item.price))
    setItemPriceSmall(item.price_small != null ? String(item.price_small) : '')
    setItemPriceMedium(item.price_medium != null ? String(item.price_medium) : '')
    setItemPriceLarge(item.price_large != null ? String(item.price_large) : '')
    setItemDesc(item.description ?? '')
    setItemIngredient(item.ingredient ?? '')
    setItemNote(item.note ?? '')
    setItemAvailable(item.availability)
    setItemTags((item.tags ?? []).join(', '))
    setItemModifiersJson(item.modifiers ? JSON.stringify(item.modifiers, null, 2) : '')
  }

  async function handleSubmitItem(e: React.FormEvent): Promise<void> {
    e.preventDefault()
    if (!itemName.trim()) return
    const parsedPrice = Number(itemPrice)
    if (!Number.isFinite(parsedPrice) || parsedPrice < 0) {
      setError(t('menu.invalidPrice')); return
    }

    let modifiers: Record<string, unknown> | null = null
    const trimmed = itemModifiersJson.trim()
    if (trimmed) {
      try { modifiers = JSON.parse(trimmed) } catch {
        setError(t('menu.invalidModifiers')); return
      }
    }

    const tags = itemTags.split(',').map((t) => t.trim()).filter(Boolean)
    setError(null)

    const parseOptionalPrice = (v: string) => {
      const trimmed = v.trim()
      if (!trimmed) return null
      const n = Number(trimmed)
      return Number.isFinite(n) && n >= 0 ? n : null
    }

    try {
      const payload: any = {
        name: itemName.trim(),
        price: parsedPrice,
        price_small: parseOptionalPrice(itemPriceSmall),
        price_medium: parseOptionalPrice(itemPriceMedium),
        price_large: parseOptionalPrice(itemPriceLarge),
        description: itemDesc.trim() || null,
        availability: itemAvailable,
        tags: tags.length ? tags : null,
        modifiers,
        alias_name: itemAliasName.trim() || null,
        category: itemCategory.trim() || null,
        ingredient: itemIngredient.trim() || null,
        note: itemNote.trim() || null,
      }

      if (editingItemId) {
        const updated = await updateStoreItem(editingItemId, payload)
        setPoolItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
        // Also refresh menu items list in case name/price changed
        if (selectedMenuId) await reloadMenuItems(selectedMenuId)
      } else {
        const created = await createStoreItem(payload)
        setPoolItems((prev) => [created, ...prev])
      }
      resetItemForm()
    } catch {
      setError(t('menu.failedSaveItem'))
    }
  }

  async function handleDeletePoolItem(item: MenuItemOut): Promise<void> {
    if (!window.confirm(t('menu.deleteItemConfirm', { name: item.name }))) return
    setError(null)
    try {
      await deleteStoreItem(item.id)
      setPoolItems((prev) => prev.filter((i) => i.id !== item.id))
      setMenuItems((prev) => prev.filter((i) => i.id !== item.id))
      if (editingItemId === item.id) resetItemForm()
    } catch {
      setError(t('menu.failedDeleteItem'))
    }
  }

  // ── Menu handlers ─────────────────────────────────────

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

  // ── Link / unlink items ───────────────────────────────

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

  // ── CSV upload ────────────────────────────────────────

  async function handleCsvUpload(e: React.ChangeEvent<HTMLInputElement>): Promise<void> {
    const file = e.target.files?.[0]
    if (!file) return
    setError(null)
    setUploadMsg(null)
    try {
      const result = await uploadItemsCsv(file)
      await reloadPool()
      if (selectedMenuId) await reloadMenuItems(selectedMenuId)
      const parts = [t('menu.uploadResult', { created: result.created, updated: result.updated })]
      if (result.errors.length) parts.push(t('menu.uploadErrors', { count: result.errors.length, details: result.errors.slice(0, 3).join('; ') }))
      setUploadMsg(parts.join('. '))
    } catch {
      setError(t('menu.uploadFailed'))
    } finally {
      if (csvInputRef.current) csvInputRef.current.value = ''
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>{t('menu.title')}</h1>
        <p>{t('menu.subtitle')}</p>
      </div>

      {error && <div className="alert alert-error" style={{ marginBottom: 16 }}>{error}</div>}
      {uploadMsg && <div className="alert alert-success" style={{ marginBottom: 16 }}>{uploadMsg}</div>}

      {/* ── Item form ─────────────────────────────────── */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header">
          <h2>{editingItemId ? t('menu.editItem') : t('menu.addItemToPool')}</h2>
          {editingItemId && (
            <button className="btn btn-ghost btn-sm" onClick={resetItemForm}>{t('common.cancel')}</button>
          )}
        </div>
        <form className="card-body" onSubmit={(e) => void handleSubmitItem(e)}>
          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">{t('menu.name')}</label>
              <input className="form-input" value={itemName} onChange={(e) => setItemName(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.aliasName')}</label>
              <input className="form-input" value={itemAliasName} onChange={(e) => setItemAliasName(e.target.value)} placeholder={t('menu.aliasNamePlaceholder')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.category')}</label>
              <input className="form-input" value={itemCategory} onChange={(e) => setItemCategory(e.target.value)} placeholder={t('menu.categoryPlaceholder')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.basePrice')}</label>
              <input className="form-input" value={itemPrice} onChange={(e) => setItemPrice(e.target.value)} inputMode="decimal" placeholder="0.00" />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.priceSmall')}</label>
              <input className="form-input" value={itemPriceSmall} onChange={(e) => setItemPriceSmall(e.target.value)} inputMode="decimal" placeholder={t('menu.optional')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.priceMedium')}</label>
              <input className="form-input" value={itemPriceMedium} onChange={(e) => setItemPriceMedium(e.target.value)} inputMode="decimal" placeholder={t('menu.optional')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.priceLarge')}</label>
              <input className="form-input" value={itemPriceLarge} onChange={(e) => setItemPriceLarge(e.target.value)} inputMode="decimal" placeholder={t('menu.optional')} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.tags')}</label>
              <input className="form-input" value={itemTags} onChange={(e) => setItemTags(e.target.value)} placeholder={t('menu.tagsPlaceholder')} />
            </div>
            <div className="form-group grid-full">
              <label className="form-label">{t('menu.description')}</label>
              <input className="form-input" value={itemDesc} onChange={(e) => setItemDesc(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.ingredient')}</label>
              <input className="form-input" value={itemIngredient} onChange={(e) => setItemIngredient(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">{t('menu.note')}</label>
              <input className="form-input" value={itemNote} onChange={(e) => setItemNote(e.target.value)} />
            </div>
            <div className="form-group grid-full">
              <label className="form-label">{t('menu.modifiersJson')}</label>
              <textarea className="form-input" value={itemModifiersJson} onChange={(e) => setItemModifiersJson(e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-check">
                <input type="checkbox" checked={itemAvailable} onChange={(e) => setItemAvailable(e.target.checked)} />
                {t('common.available')}
              </label>
            </div>
            <div className="flex-end">
              <button type="submit" className="btn btn-primary">
                {editingItemId ? t('menu.updateItem') : t('menu.addItem')}
              </button>
            </div>
          </div>
        </form>
      </div>

      {/* ── Two-column layout ────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, alignItems: 'start' }}>

        {/* Left: Items pool */}
        <div className="card">
          <div className="card-header">
            <h2>{t('menu.itemsPoolCount', { count: poolItems.length })}</h2>
            <div style={{ display: 'flex', gap: 6 }}>
              <input
                ref={csvInputRef}
                type="file"
                accept=".csv"
                style={{ display: 'none' }}
                onChange={(e) => void handleCsvUpload(e)}
              />
              <button className="btn btn-secondary btn-sm" onClick={() => csvInputRef.current?.click()}>
                {t('menu.uploadCsv')}
              </button>
            </div>
          </div>
          <div>
            {poolItems.map((item) => {
              const inMenu = menuItemIds.has(item.id)
              const hasSizes = item.price_small != null || item.price_medium != null || item.price_large != null
              return (
                <div key={item.id} className="list-item">
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{ fontWeight: 600 }}>{item.name}</span>
                      {item.alias_name && (
                        <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>({item.alias_name})</span>
                      )}
                      {hasSizes ? (
                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-primary)' }}>
                          {[
                            item.price_small != null && `S $${item.price_small}`,
                            item.price_medium != null && `M $${item.price_medium}`,
                            item.price_large != null && `L $${item.price_large}`,
                          ].filter(Boolean).join(' / ')}
                        </span>
                      ) : (
                        <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>${String(item.price)}</span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                      {item.category && <span className="badge badge-submitted">{item.category}</span>}
                      <span className={`badge ${item.availability ? 'badge-active' : 'badge-inactive'}`}>
                        {item.availability ? t('common.available') : t('common.unavailable')}
                      </span>
                      {inMenu && <span className="badge badge-confirmed">{t('common.inMenu')}</span>}
                      {item.tags?.map((tag) => (
                        <span key={tag} className="badge badge-draft">{tag}</span>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 4 }}>
                    {selectedMenuId && !inMenu && (
                      <button className="btn btn-primary btn-sm" onClick={() => void handleAddToMenu(item)} title={t('menu.addToMenuTitle')}>+</button>
                    )}
                    <button className="btn btn-secondary btn-sm" onClick={() => handleEditItem(item)}>{t('common.edit')}</button>
                    <button className="btn btn-danger btn-sm" onClick={() => void handleDeletePoolItem(item)}>{t('common.delete')}</button>
                  </div>
                </div>
              )
            })}
            {!poolItems.length && <div className="empty-state">{t('menu.noItemsYet')}</div>}
          </div>
        </div>

        {/* Right: Menus + Menu Items stacked */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* Menus list */}
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
                        {t('common.default')}
                      </button>
                    )}
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

          {/* Menu items (linked) */}
          <div className="card">
            <div className="card-header">
              <h2>{selectedMenu ? t('menu.menuItems', { name: selectedMenu.name, count: menuItems.length }) : t('menu.menuItemsDefault', { count: menuItems.length })}</h2>
            </div>
            <div>
              {selectedMenu ? (
                menuItems.length ? (
                  menuItems.map((item) => {
                    const hasSizes = item.price_small != null || item.price_medium != null || item.price_large != null
                    return (
                    <div key={item.id} className="list-item">
                      <div style={{ flex: 1 }}>
                        <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, flexWrap: 'wrap' }}>
                          <span style={{ fontWeight: 600 }}>{item.name}</span>
                          {item.alias_name && (
                            <span style={{ fontSize: 12, color: 'var(--color-text-secondary)' }}>({item.alias_name})</span>
                          )}
                          {hasSizes ? (
                            <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-primary)' }}>
                              {[
                                item.price_small != null && `S $${item.price_small}`,
                                item.price_medium != null && `M $${item.price_medium}`,
                                item.price_large != null && `L $${item.price_large}`,
                              ].filter(Boolean).join(' / ')}
                            </span>
                          ) : (
                            <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>${String(item.price)}</span>
                          )}
                        </div>
                        <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                          {item.category && <span className="badge badge-submitted">{item.category}</span>}
                          {item.tags?.map((tag) => (
                            <span key={tag} className="badge badge-draft">{tag}</span>
                          ))}
                        </div>
                      </div>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => void handleRemoveFromMenu(item)}
                        title={t('menu.removeFromMenu')}
                      >
                        {t('common.remove')}
                      </button>
                    </div>
                  )})
                ) : (
                  <div className="empty-state">{t('menu.noMenuItems')}</div>
                )
              ) : (
                <div className="empty-state">{t('menu.selectMenu')}</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  )
}
