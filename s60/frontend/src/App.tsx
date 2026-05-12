import { useState, useCallback, useRef } from 'react'
import { useSpacetimeDB, useTable } from 'spacetimedb/react'
import { DbConnection, tables, reducers } from './module_bindings'
import type { Model, Row } from './module_bindings/types'

type View = 'models' | 'rows'

function App() {
  const ctx = useSpacetimeDB()
  const conn = ctx.getConnection() as DbConnection | null
  const identity = conn?.identity
  const identityHex = identity?.toHexString()

  const [view, setView] = useState<View>('models')
  const [selectedModel, setSelectedModel] = useState<Model | null>(null)
  const [showForm, setShowForm] = useState<'model' | 'row' | 'name' | null>(null)
  const [editItem, setEditItem] = useState<Model | Row | null>(null)
  const [message, setMessage] = useState('')

  // Ref for form (reads values directly from DOM, works with automation)
  const modelFormRef = useRef<HTMLFormElement>(null)
  const rowFormRef = useRef<HTMLFormElement>(null)

  // Subscribe to tables
  const [allModels] = useTable(tables.model)
  const [allRows] = useTable(tables.row)

  const myModels = allModels.filter(m => m.owner.toHexString() === identityHex)
  const publicModels = allModels.filter(
    m => m.owner.toHexString() !== identityHex && m.visibility !== 'private'
  )
  const modelRows = selectedModel
    ? allRows.filter(r => r.modelId === selectedModel.id)
    : []

  const notify = useCallback((msg: string) => {
    setMessage(msg)
    setTimeout(() => setMessage(''), 3000)
  }, [])

  // ─── Reducer calls ──────────────────────────────────────────────

  const openNewModelForm = useCallback(() => {
    setEditItem(null)
    setShowForm('model')
    setTimeout(() => modelFormRef.current?.reset(), 0)
  }, [])

  const openEditModelForm = useCallback((m: Model) => {
    setEditItem(m)
    setShowForm('model')
    // Values are set via defaultValue in the form
  }, [])

  const createModel = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const name = (fd.get('name') as string || '').trim()
    const fieldsInput = (fd.get('fields') as string || '').trim()
    const desc = fd.get('description') as string || ''
    const vis = fd.get('visibility') as string || 'private'
    if (!name) { notify('El nombre es obligatorio'); return }
    const fields = fieldsInput.split(',').map(f => f.trim()).filter(Boolean).map(f => {
      const [n, t = 'string'] = f.split(':').map(s => s.trim())
      return { name: n, type: t }
    })
    if (fields.length === 0) { notify('Agrega al menos un campo'); return }
    const fieldsJson = JSON.stringify(fields)
    try {
      await conn?.reducers.createModel({ name, fieldsJson, description: desc, visibility: vis })
      setShowForm(null)
      notify('Modelo creado')
    } catch (e: any) {
      notify(`Error: ${e.message ?? e}`)
    }
  }, [conn, notify])

  const updateModel = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!editItem) return
    const fd = new FormData(e.currentTarget)
    const name = (fd.get('name') as string || '').trim()
    const fieldsInput = (fd.get('fields') as string || '').trim()
    const desc = fd.get('description') as string || ''
    const vis = fd.get('visibility') as string || 'private'
    const m = editItem as Model
    try {
      await conn?.reducers.updateModel({
        id: m.id,
        name: name || m.name,
        fieldsJson: fieldsInput || m.fieldsJson,
        description: desc || m.description,
        visibility: vis || m.visibility,
      })
      setShowForm(null)
      setEditItem(null)
      notify('Modelo actualizado')
    } catch (e: any) {
      notify(`Error: ${e.message ?? e}`)
    }
  }, [conn, editItem, notify])

  const deleteModel = useCallback(async (id: number) => {
    if (!confirm('¿Eliminar este modelo y todas sus filas?')) return
    try {
      await conn?.reducers.deleteModel({ id })
      if (selectedModel?.id === id) {
        setSelectedModel(null)
        setView('models')
      }
      notify('Modelo eliminado')
    } catch (e: any) {
      notify(`Error: ${e.message ?? e}`)
    }
  }, [conn, selectedModel, notify])

  const createRow = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!selectedModel) return
    const fd = new FormData(e.currentTarget)
    const parsed = JSON.parse(selectedModel.fieldsJson) as { name: string }[]
    const fields: Record<string, string> = {}
    for (const f of parsed) {
      fields[f.name] = (fd.get(f.name) as string) ?? ''
    }
    try {
      await conn?.reducers.createRow({ modelId: selectedModel.id, dataJson: JSON.stringify(fields) })
      setShowForm(null)
      notify('Fila agregada')
    } catch (e: any) {
      notify(`Error: ${e.message ?? e}`)
    }
  }, [conn, selectedModel, notify])

  const updateRow = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    if (!editItem || !selectedModel) return
    const fd = new FormData(e.currentTarget)
    const parsed = JSON.parse(selectedModel.fieldsJson) as { name: string }[]
    const fields: Record<string, string> = {}
    for (const f of parsed) {
      fields[f.name] = (fd.get(f.name) as string) ?? ''
    }
    const row = editItem as Row
    try {
      await conn?.reducers.updateRow({ id: row.id, dataJson: JSON.stringify(fields) })
      setShowForm(null)
      setEditItem(null)
      notify('Fila actualizada')
    } catch (e: any) {
      notify(`Error: ${e.message ?? e}`)
    }
  }, [conn, editItem, selectedModel, notify])

  const deleteRow = useCallback(async (id: number) => {
    if (!confirm('¿Eliminar esta fila?')) return
    try {
      await conn?.reducers.deleteRow({ id })
      notify('Fila eliminada')
    } catch (e: any) {
      notify(`Error: ${e.message ?? e}`)
    }
  }, [conn, notify])

  const cloneModel = useCallback(async (modelId: number) => {
    try {
      await conn?.reducers.cloneModelAsTemplate({ sourceModelId: modelId })
      notify('Modelo clonado como plantilla')
    } catch (e: any) {
      notify(`Error: ${e.message ?? e}`)
    }
  }, [conn, notify])

  const setDisplayName = useCallback(async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const fd = new FormData(e.currentTarget)
    const name = fd.get('name') as string
    try {
      await conn?.reducers.setDisplayName({ name })
      setShowForm(null)
      notify('Nombre actualizado')
    } catch (e: any) {
      notify(`Error: ${e.message ?? e}`)
    }
  }, [conn, notify])

  // ─── Helpers ────────────────────────────────────────────────────

  const parseFields = (fieldsJson: string): { name: string; type: string }[] => {
    try { return JSON.parse(fieldsJson) } catch { return [] }
  }

  const parseRowData = (dataJson: string): Record<string, string> => {
    try { return JSON.parse(dataJson) } catch { return {} }
  }

  const visibilityLabel = (v: string) => {
    if (v === 'public') return '🌍 Público'
    if (v === 'template') return '📐 Plantilla'
    return '🔒 Privado'
  }

  // ─── Render ─────────────────────────────────────────────────────

  const isConnected = ctx.isActive && conn !== null

  if (!isConnected) {
    return (
      <div className="loading">
        <h1>UserTables</h1>
        <p>Conectando a SpaceTimeDB... {ctx.connectionError ? `Error: ${ctx.connectionError.message}` : ''}</p>
      </div>
    )
  }

  return (
    <div className="app">
      <header>
        <div className="header-left">
          <h1>📊 UserTables</h1>
          <span className={`status ${isConnected ? 'connected' : ''}`}>
            {isConnected ? '🟢 Conectado' : '🔴 Desconectado'}
          </span>
        </div>
        <div className="header-right">
          <span className="identity" title={identityHex}>
            {identityHex?.slice(0, 12)}...
          </span>
          <button onClick={() => setShowForm('name')} className="btn-small">
            ✏️ Nombre
          </button>
        </div>
      </header>

      {message && <div className="toast">{message}</div>}

      {/* ─── Display name form ─────────────────────────────────── */}
      {showForm === 'name' && (
        <div className="modal-overlay" onClick={() => setShowForm(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>Tu nombre</h3>
            <form onSubmit={setDisplayName}>
              <input name="name" placeholder="Nombre visible" required />
              <div className="form-actions">
                <button type="submit">Guardar</button>
                <button type="button" onClick={() => setShowForm(null)}>Cancelar</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── Model list view ───────────────────────────────────── */}
      {view === 'models' && (
        <main>
          <section>
            <div className="section-header">
              <h2>Mis modelos</h2>
              <button onClick={openNewModelForm}>
                + Nuevo modelo
              </button>
            </div>
            {myModels.length === 0 ? (
              <p className="empty">No tienes modelos todavía. ¡Crea uno!</p>
            ) : (
              <div className="model-grid">
                {myModels.map(m => (
                  <div key={m.id.toString()} className="card">
                    <div className="card-header">
                      <strong>{m.name}</strong>
                      <span className="vis-badge">{visibilityLabel(m.visibility)}</span>
                    </div>
                    <p className="card-desc">{m.description || 'Sin descripción'}</p>
                    <p className="card-meta">
                      {parseFields(m.fieldsJson).length} campos · {allRows.filter(r => r.modelId === m.id).length} filas
                    </p>
                    <div className="card-actions">
                      <button onClick={() => { setSelectedModel(m); setView('rows') }}>
                        📋 Ver datos
                      </button>
                      <button onClick={() => openEditModelForm(m)}>
                        ✏️
                      </button>
                      <button className="danger" onClick={() => deleteModel(m.id)}>
                        🗑️
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section>
            <div className="section-header">
              <h2>Modelos públicos / plantillas</h2>
            </div>
            {publicModels.length === 0 ? (
              <p className="empty">No hay modelos públicos aún.</p>
            ) : (
              <div className="model-grid">
                {publicModels.map(m => (
                  <div key={m.id.toString()} className="card">
                    <div className="card-header">
                      <strong>{m.name}</strong>
                      <span className="vis-badge">{visibilityLabel(m.visibility)}</span>
                    </div>
                    <p className="card-desc">{m.description || 'Sin descripción'}</p>
                    <p className="card-meta">
                      {parseFields(m.fieldsJson).length} campos · Dueño: {m.owner.toHexString().slice(0, 8)}...
                    </p>
                    <div className="card-actions">
                      {m.visibility !== 'private' && (
                        <>
                          <button onClick={() => { setSelectedModel(m); setView('rows') }}>
                            👁️ Ver
                          </button>
                          <button onClick={() => cloneModel(m.id)}>
                            📋 Clonar
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        </main>
      )}

      {/* ─── Create / Edit model form ──────────────────────────── */}
      {showForm === 'model' && (
        <div className="modal-overlay" onClick={() => { setShowForm(null); setEditItem(null) }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>{editItem ? 'Editar modelo' : 'Nuevo modelo'}</h3>
            <form ref={modelFormRef} onSubmit={editItem ? updateModel : createModel}>
              <label>Nombre *</label>
              <input name="name" defaultValue={editItem ? (editItem as Model).name : ''} required />

              <label>Campos (ej: título:string, edad:number, activo:boolean)</label>
              <input name="fields" defaultValue={
                editItem ? parseFields((editItem as Model).fieldsJson).map(f => `${f.name}:${f.type}`).join(', ') : ''
              } required />

              <label>Descripción</label>
              <input name="description" defaultValue={editItem ? (editItem as Model).description : ''} />

              <label>Visibilidad</label>
              <select name="visibility" defaultValue={editItem ? (editItem as Model).visibility : 'private'}>
                <option value="private">🔒 Privado</option>
                <option value="template">📐 Plantilla (solo esquema)</option>
                <option value="public">🌍 Público (esquema + datos)</option>
              </select>

              <div className="form-actions">
                <button type="submit">{editItem ? 'Guardar' : 'Crear'}</button>
                <button type="button" onClick={() => { setShowForm(null); setEditItem(null) }}>
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── Row list view (model detail) ──────────────────────── */}
      {view === 'rows' && selectedModel && (
        <main>
          <div className="section-header">
            <button className="btn-small" onClick={() => { setView('models'); setSelectedModel(null) }}>
              ← Volver
            </button>
            <h2>{selectedModel.name}</h2>
            <button onClick={() => { setShowForm('row'); setEditItem(null) }}>
              + Nueva fila
            </button>
          </div>

          <div className="model-info">
            <p>{selectedModel.description}</p>
            <p>Campos: {parseFields(selectedModel.fieldsJson).map(f => `${f.name} (${f.type})`).join(', ')}</p>
            <p>Visibilidad: {visibilityLabel(selectedModel.visibility)}</p>
          </div>

          {modelRows.length === 0 ? (
            <p className="empty">No hay datos en este modelo.</p>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    {parseFields(selectedModel.fieldsJson).map(f => (
                      <th key={f.name}>{f.name}</th>
                    ))}
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {modelRows.map(r => {
                    const data = parseRowData(r.dataJson)
                    return (
                      <tr key={r.id.toString()}>
                        {parseFields(selectedModel.fieldsJson).map(f => (
                          <td key={f.name}>{data[f.name] ?? '-'}</td>
                        ))}
                        <td className="cell-actions">
                          {(r.createdBy.toHexString() === identityHex || selectedModel.owner.toHexString() === identityHex) && (
                            <>
                              <button onClick={() => { setEditItem(r); setShowForm('row') }}>✏️</button>
                              <button className="danger" onClick={() => deleteRow(r.id)}>🗑️</button>
                            </>
                          )}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </main>
      )}

      {/* ─── Create / Edit row form ────────────────────────────── */}
      {showForm === 'row' && selectedModel && (
        <div className="modal-overlay" onClick={() => { setShowForm(null); setEditItem(null) }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>{editItem ? 'Editar fila' : 'Nueva fila'} en {selectedModel.name}</h3>
            <form ref={rowFormRef} onSubmit={editItem ? updateRow : createRow}>
              {parseFields(selectedModel.fieldsJson).map(f => {
                const existingData = editItem ? parseRowData((editItem as Row).dataJson) : {}
                return (
                  <div key={f.name} className="field-group">
                    <label>{f.name} ({f.type})</label>
                    <input
                      name={f.name}
                      type={f.type === 'number' ? 'number' : 'text'}
                      defaultValue={existingData[f.name] ?? ''}
                      required
                    />
                  </div>
                )
              })}
              <div className="form-actions">
                <button type="submit">{editItem ? 'Guardar' : 'Crear'}</button>
                <button type="button" onClick={() => { setShowForm(null); setEditItem(null) }}>
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default App
