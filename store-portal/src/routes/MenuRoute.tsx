import React, { useEffect, useMemo, useState } from 'react'
import { GlassButton, GlassCard, GlassSurface } from '@zhqingit/liquid-glass-react'
import {
  type MenuItemOut,
  type MenuOut,
  createMenu,
  createMenuItem,
  deleteMenu,
  deleteMenuItem,
  listMenuItems,
  listMenus,
  updateMenu,
  updateMenuItem,
} from '../api/menuApi'

export function MenuRoute(): React.JSX.Element {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [menus, setMenus] = useState<MenuOut[]>([])
  const [selectedMenuId, setSelectedMenuId] = useState<string | null>(null)

  const selectedMenu = useMemo(
    () => menus.find((m) => m.id === selectedMenuId) ?? null,
    [menus, selectedMenuId],
  )

  const [items, setItems] = useState<MenuItemOut[]>([])

  const [newMenuName, setNewMenuName] = useState('')

  const [editingItemId, setEditingItemId] = useState<string | null>(null)
  const [itemName, setItemName] = useState('')
  const [itemPrice, setItemPrice] = useState('')
  const [itemDesc, setItemDesc] = useState('')
  const [itemAvailable, setItemAvailable] = useState(true)
  const [itemTags, setItemTags] = useState('')
  const [itemModifiersJson, setItemModifiersJson] = useState('')

  async function reloadMenus(selectId?: string): Promise<void> {
    const data = await listMenus()
    setMenus(data)
    const nextId = selectId ?? selectedMenuId ?? (data[0]?.id ?? null)
    setSelectedMenuId(nextId)
  }

  async function reloadItems(menuId: string): Promise<void> {
    const data = await listMenuItems(menuId)
    setItems(data)
  }

  function resetItemForm(): void {
    setEditingItemId(null)
    setItemName('')
    setItemPrice('')
    setItemDesc('')
    setItemAvailable(true)
    setItemTags('')
    setItemModifiersJson('')
  }

  useEffect(() => {
    void (async () => {
      setLoading(true)
      setError(null)
      try {
        await reloadMenus()
      } catch (e) {
        setError('Failed to load menus')
      } finally {
        setLoading(false)
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!selectedMenuId) {
      setItems([])
      return
    }
    void (async () => {
      try {
        await reloadItems(selectedMenuId)
      } catch {
        setError('Failed to load menu items')
      }
    })()
  }, [selectedMenuId])

  async function handleCreateMenu(): Promise<void> {
    if (!newMenuName.trim()) return
    setError(null)
    try {
      const created = await createMenu({ name: newMenuName.trim(), active: true })
      setNewMenuName('')
      await reloadMenus(created.id)
    } catch {
      setError('Failed to create menu')
    }
  }

  async function handleToggleMenuActive(menu: MenuOut): Promise<void> {
    setError(null)
    try {
      const updated = await updateMenu(menu.id, { active: !menu.active })
      setMenus((prev) => prev.map((m) => (m.id === updated.id ? updated : m)))
    } catch {
      setError('Failed to update menu')
    }
  }

  async function handleDeleteMenu(menu: MenuOut): Promise<void> {
    if (!window.confirm(`Delete menu "${menu.name}"?`)) return
    setError(null)
    try {
      await deleteMenu(menu.id)
      const next = menus.filter((m) => m.id !== menu.id)
      setMenus(next)
      const nextSel = next[0]?.id ?? null
      setSelectedMenuId(nextSel)
    } catch {
      setError('Failed to delete menu')
    }
  }

  async function handleEditItem(item: MenuItemOut): Promise<void> {
    setEditingItemId(item.id)
    setItemName(item.name)
    setItemPrice(String(item.price))
    setItemDesc(item.description ?? '')
    setItemAvailable(item.availability)
    setItemTags((item.tags ?? []).join(', '))
    setItemModifiersJson(item.modifiers ? JSON.stringify(item.modifiers, null, 2) : '')
  }

  async function handleSubmitItem(): Promise<void> {
    if (!selectedMenuId) return
    if (!itemName.trim()) return
    const parsedPrice = Number(itemPrice)
    if (!Number.isFinite(parsedPrice) || parsedPrice < 0) {
      setError('Invalid price')
      return
    }

    let modifiers: Record<string, unknown> | null = null
    const trimmedModifiers = itemModifiersJson.trim()
    if (trimmedModifiers) {
      try {
        modifiers = JSON.parse(trimmedModifiers) as Record<string, unknown>
      } catch {
        setError('Modifiers must be valid JSON')
        return
      }
    }

    const tags = itemTags
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)

    setError(null)

    try {
      if (editingItemId) {
        const updated = await updateMenuItem(selectedMenuId, editingItemId, {
          name: itemName.trim(),
          price: parsedPrice,
          description: itemDesc.trim() ? itemDesc.trim() : null,
          availability: itemAvailable,
          tags: tags.length ? tags : null,
          modifiers,
        })
        setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
      } else {
        const created = await createMenuItem(selectedMenuId, {
          name: itemName.trim(),
          price: parsedPrice,
          description: itemDesc.trim() ? itemDesc.trim() : null,
          availability: itemAvailable,
          tags: tags.length ? tags : null,
          modifiers,
        })
        setItems((prev) => [created, ...prev])
      }

      resetItemForm()
    } catch {
      setError('Failed to save menu item')
    }
  }

  async function handleDeleteItem(item: MenuItemOut): Promise<void> {
    if (!selectedMenuId) return
    if (!window.confirm(`Delete item "${item.name}"?`)) return
    setError(null)
    try {
      await deleteMenuItem(selectedMenuId, item.id)
      setItems((prev) => prev.filter((i) => i.id !== item.id))
      if (editingItemId === item.id) resetItemForm()
    } catch {
      setError('Failed to delete item')
    }
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '320px 1fr', gap: 16 }}>
      <GlassCard preset="frosted" style={{ padding: 14 }}>
        <h2 style={{ marginTop: 0 }}>Menus</h2>

        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={newMenuName}
            onChange={(e) => setNewMenuName(e.target.value)}
            placeholder="New menu name"
            style={inputStyle}
          />
          <GlassButton style={{ padding: '8px 10px' }} onClick={handleCreateMenu}>
            Add
          </GlassButton>
        </div>

        <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {menus.map((m) => {
            const active = m.id === selectedMenuId
            return (
              <GlassSurface
                key={m.id}
                preset={active ? 'vibrant' : 'subtle'}
                interactive
                onClick={() => setSelectedMenuId(m.id)}
                style={{ padding: 10, cursor: 'pointer' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>{m.name}</div>
                    <div style={{ opacity: 0.75, fontSize: 12 }}>
                      {m.active ? 'Active' : 'Inactive'} · v{m.version}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <GlassButton
                      preset="subtle"
                      style={{ padding: '6px 8px' }}
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        void handleToggleMenuActive(m)
                      }}
                    >
                      {m.active ? 'Disable' : 'Enable'}
                    </GlassButton>
                    <GlassButton
                      preset="contrast"
                      style={{ padding: '6px 8px' }}
                      onClick={(e) => {
                        e.preventDefault()
                        e.stopPropagation()
                        void handleDeleteMenu(m)
                      }}
                    >
                      Del
                    </GlassButton>
                  </div>
                </div>
              </GlassSurface>
            )
          })}

          {!menus.length && !loading ? <div style={{ opacity: 0.7 }}>No menus yet.</div> : null}
        </div>
      </GlassCard>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        <GlassCard preset="frosted" style={{ padding: 14 }}>
          <h2 style={{ marginTop: 0 }}>Items {selectedMenu ? `· ${selectedMenu.name}` : ''}</h2>

          {selectedMenu ? (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <label style={labelStyle}>
                Name
                <input value={itemName} onChange={(e) => setItemName(e.target.value)} style={inputStyle} />
              </label>
              <label style={labelStyle}>
                Price
                <input
                  value={itemPrice}
                  onChange={(e) => setItemPrice(e.target.value)}
                  style={inputStyle}
                  inputMode="decimal"
                />
              </label>
              <label style={labelStyle}>
                Tags (comma-separated)
                <input value={itemTags} onChange={(e) => setItemTags(e.target.value)} style={inputStyle} />
              </label>
              <label style={{ ...labelStyle, display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="checkbox"
                  checked={itemAvailable}
                  onChange={(e) => setItemAvailable(e.target.checked)}
                />
                Available
              </label>
              <label style={{ ...labelStyle, gridColumn: '1 / -1' }}>
                Description
                <input value={itemDesc} onChange={(e) => setItemDesc(e.target.value)} style={inputStyle} />
              </label>
              <label style={{ ...labelStyle, gridColumn: '1 / -1' }}>
                Modifiers JSON (optional)
                <textarea
                  value={itemModifiersJson}
                  onChange={(e) => setItemModifiersJson(e.target.value)}
                  style={{ ...inputStyle, minHeight: 120, fontFamily: 'ui-monospace, SFMono-Regular' }}
                />
              </label>

              <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                {editingItemId ? (
                  <GlassButton preset="subtle" style={{ padding: '8px 12px' }} onClick={resetItemForm}>
                    Cancel
                  </GlassButton>
                ) : null}
                <GlassButton style={{ padding: '8px 12px', fontWeight: 700 }} onClick={handleSubmitItem}>
                  {editingItemId ? 'Update Item' : 'Add Item'}
                </GlassButton>
              </div>
            </div>
          ) : (
            <div style={{ opacity: 0.75 }}>Select a menu to manage items.</div>
          )}

          {error ? <div style={{ marginTop: 10, color: 'crimson' }}>{error}</div> : null}
        </GlassCard>

        <GlassCard preset="subtle" style={{ padding: 14 }}>
          <h3 style={{ marginTop: 0 }}>Current items</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {items.map((item) => (
              <GlassSurface key={item.id} preset="subtle" style={{ padding: 12 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                  <div>
                    <div style={{ fontWeight: 700 }}>
                      {item.name} <span style={{ opacity: 0.75, fontWeight: 500 }}>${String(item.price)}</span>
                    </div>
                    <div style={{ opacity: 0.75, fontSize: 12 }}>
                      {item.availability ? 'Available' : 'Unavailable'}
                      {item.tags?.length ? ` · ${item.tags.join(', ')}` : ''}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                    <GlassButton
                      preset="subtle"
                      style={{ padding: '6px 10px' }}
                      onClick={() => void handleEditItem(item)}
                    >
                      Edit
                    </GlassButton>
                    <GlassButton
                      preset="contrast"
                      style={{ padding: '6px 10px' }}
                      onClick={() => void handleDeleteItem(item)}
                    >
                      Delete
                    </GlassButton>
                  </div>
                </div>
              </GlassSurface>
            ))}
            {!items.length && selectedMenuId ? <div style={{ opacity: 0.7 }}>No items yet.</div> : null}
          </div>
        </GlassCard>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  padding: '10px 12px',
  borderRadius: 12,
  border: '1px solid rgba(255,255,255,0.22)',
  background: 'rgba(255,255,255,0.08)',
  color: 'inherit',
}

const labelStyle: React.CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: 6,
  fontSize: 13,
  opacity: 0.95,
}
