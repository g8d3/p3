use spacetimedb::{table, reducer, ReducerContext, Identity, Timestamp, Table};

// ═══════════════════════════════════════════════════════════════════
//  TABLAS (públicas → clientes pueden leer vía subscripción)
// ═══════════════════════════════════════════════════════════════════

/// Modelo = una "tabla" creada por el usuario (su propio esquema).
/// `fields_json` describe las columnas:
///   [{"name":"campo1","type":"string"}, {"name":"campo2","type":"number"}]
/// `visibility`: "private" | "template" (solo esquema) | "public" (esquema + datos)
#[table(accessor = model, public)]
#[derive(Debug)]
pub struct Model {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    pub name: String,
    #[index(btree)]
    pub owner: Identity,
    pub fields_json: String,
    pub description: String,
    pub visibility: String,
    pub created_at: Timestamp,
}

/// Fila dentro de un modelo.
/// `data_json` guarda los valores: {"campo1": "valor", "campo2": 42}
#[table(accessor = row, public)]
#[derive(Debug)]
pub struct Row {
    #[primary_key]
    #[auto_inc]
    pub id: u64,
    #[index(btree)]
    pub model_id: u64,
    pub data_json: String,
    #[index(btree)]
    pub created_by: Identity,
    pub created_at: Timestamp,
    pub updated_at: Timestamp,
}

// ─── Perfil (privado — solo accesible desde reducers) ────────────

#[table(accessor = profile)]
#[derive(Debug)]
pub struct Profile {
    #[primary_key]
    pub identity: Identity,
    pub display_name: String,
    pub created_at: Timestamp,
}

// ═══════════════════════════════════════════════════════════════════
//  CICLO DE VIDA
// ═══════════════════════════════════════════════════════════════════

#[reducer(init)]
pub fn init(ctx: &ReducerContext) -> Result<(), String> {
    log::info!("Módulo user_tables iniciado por: {:?}", ctx.sender());
    Ok(())
}

#[reducer(client_connected)]
pub fn client_connected(ctx: &ReducerContext) {
    let id = ctx.sender();
    if ctx.db.profile().identity().find(id).is_none() {
        ctx.db.profile().insert(Profile {
            identity: id,
            display_name: format!("User_{}", &id.to_hex()[..8]),
            created_at: ctx.timestamp,
        });
        log::info!("Nuevo usuario conectado: {:?}", id);
    }
}

#[reducer(client_disconnected)]
pub fn client_disconnected(ctx: &ReducerContext) {
    log::info!("Usuario desconectado: {:?}", ctx.sender());
}

// ═══════════════════════════════════════════════════════════════════
//  REDUCERS: PERFIL
// ═══════════════════════════════════════════════════════════════════

#[reducer]
pub fn set_display_name(ctx: &ReducerContext, name: String) -> Result<(), String> {
    if name.trim().is_empty() {
        return Err("El nombre no puede estar vacío".into());
    }
    let mut profile = ctx.db
        .profile()
        .identity()
        .find(ctx.sender())
        .ok_or("Perfil no encontrado")?;
    profile.display_name = name.clone();
    log::info!("{} actualizó su nombre a {}", ctx.sender(), name);
    ctx.db.profile().identity().update(profile);
    Ok(())
}

// ═══════════════════════════════════════════════════════════════════
//  REDUCERS: MODELOS CRUD
// ═══════════════════════════════════════════════════════════════════

#[reducer]
pub fn create_model(
    ctx: &ReducerContext,
    name: String,
    fields_json: String,
    description: String,
    visibility: String,
) -> Result<(), String> {
    if name.trim().is_empty() {
        return Err("El nombre del modelo es obligatorio".into());
    }
    serde_json::from_str::<Vec<serde_json::Value>>(&fields_json)
        .map_err(|e| format!("fields_json debe ser un array JSON: {}", e))?;

    let valid_vis = ["private", "template", "public"];
    if !valid_vis.contains(&visibility.as_str()) {
        return Err("visibility debe ser: private, template o public".into());
    }

    ctx.db.model().insert(Model {
        id: 0,
        name,
        owner: ctx.sender(),
        fields_json,
        description,
        visibility,
        created_at: ctx.timestamp,
    });
    log::info!("{} creó un nuevo modelo", ctx.sender());
    Ok(())
}

#[reducer]
pub fn update_model(
    ctx: &ReducerContext,
    id: u64,
    name: String,
    fields_json: String,
    description: String,
    visibility: String,
) -> Result<(), String> {
    let mut model = ctx.db.model().id().find(id).ok_or("Modelo no encontrado")?;
    if model.owner != ctx.sender() {
        return Err("Solo el dueño puede editar este modelo".into());
    }
    if !name.trim().is_empty() {
        model.name = name;
    }
    if !fields_json.is_empty() {
        serde_json::from_str::<Vec<serde_json::Value>>(&fields_json)
            .map_err(|e| format!("fields_json debe ser un array JSON: {}", e))?;
        model.fields_json = fields_json;
    }
    model.description = description;
    let valid_vis = ["private", "template", "public"];
    if valid_vis.contains(&visibility.as_str()) {
        model.visibility = visibility;
    }
    ctx.db.model().id().update(model);
    log::info!("{} actualizó modelo {}", ctx.sender(), id);
    Ok(())
}

#[reducer]
pub fn delete_model(ctx: &ReducerContext, id: u64) -> Result<(), String> {
    let model = ctx.db.model().id().find(id).ok_or("Modelo no encontrado")?;
    if model.owner != ctx.sender() {
        return Err("Solo el dueño puede eliminar este modelo".into());
    }
    // Eliminar filas asociadas
    for row in ctx.db.row().model_id().filter(id) {
        ctx.db.row().id().delete(row.id);
    }
    ctx.db.model().id().delete(id);
    log::info!("{} eliminó modelo {} con sus filas", ctx.sender(), id);
    Ok(())
}

/// Clona un modelo público/template como plantilla para el usuario actual.
#[reducer]
pub fn clone_model_as_template(ctx: &ReducerContext, source_model_id: u64) -> Result<(), String> {
    let source = ctx.db.model().id().find(source_model_id)
        .ok_or("Modelo origen no encontrado")?;
    if source.visibility == "private" {
        return Err("Ese modelo es privado y no se puede clonar".into());
    }
    ctx.db.model().insert(Model {
        id: 0,
        name: format!("{} (copia)", source.name),
        owner: ctx.sender(),
        fields_json: source.fields_json.clone(),
        description: format!("Clonado de {}", source.name),
        visibility: "private".into(),
        created_at: ctx.timestamp,
    });
    log::info!("{} clonó modelo {} como plantilla", ctx.sender(), source_model_id);
    Ok(())
}

// ═══════════════════════════════════════════════════════════════════
//  REDUCERS: FILAS CRUD
// ═══════════════════════════════════════════════════════════════════

#[reducer]
pub fn create_row(ctx: &ReducerContext, model_id: u64, data_json: String) -> Result<(), String> {
    let model = ctx.db.model().id().find(model_id).ok_or("Modelo no encontrado")?;
    if model.owner != ctx.sender() && model.visibility == "private" {
        return Err("No tienes permiso para agregar filas a este modelo".into());
    }
    let val: serde_json::Value = serde_json::from_str(&data_json)
        .map_err(|e| format!("data_json debe ser un JSON válido: {}", e))?;
    if !val.is_object() {
        return Err("data_json debe ser un objeto JSON".into());
    }
    ctx.db.row().insert(Row {
        id: 0,
        model_id,
        data_json,
        created_by: ctx.sender(),
        created_at: ctx.timestamp,
        updated_at: ctx.timestamp,
    });
    log::info!("{} agregó fila a modelo {}", ctx.sender(), model_id);
    Ok(())
}

#[reducer]
pub fn update_row(ctx: &ReducerContext, id: u64, data_json: String) -> Result<(), String> {
    let mut row = ctx.db.row().id().find(id).ok_or("Fila no encontrada")?;
    let model = ctx.db.model().id().find(row.model_id).ok_or("Modelo no encontrado")?;
    if row.created_by != ctx.sender() && model.owner != ctx.sender() {
        return Err("Solo el creador o el dueño del modelo pueden editar esta fila".into());
    }
    let val: serde_json::Value = serde_json::from_str(&data_json)
        .map_err(|e| format!("data_json debe ser un JSON válido: {}", e))?;
    if !val.is_object() {
        return Err("data_json debe ser un objeto JSON".into());
    }
    row.data_json = data_json;
    row.updated_at = ctx.timestamp;
    ctx.db.row().id().update(row);
    log::info!("{} actualizó fila {}", ctx.sender(), id);
    Ok(())
}

#[reducer]
pub fn delete_row(ctx: &ReducerContext, id: u64) -> Result<(), String> {
    let row = ctx.db.row().id().find(id).ok_or("Fila no encontrada")?;
    let model = ctx.db.model().id().find(row.model_id).ok_or("Modelo no encontrado")?;
    if row.created_by != ctx.sender() && model.owner != ctx.sender() {
        return Err("Solo el creador o el dueño del modelo pueden eliminar esta fila".into());
    }
    ctx.db.row().id().delete(id);
    log::info!("{} eliminó fila {}", ctx.sender(), id);
    Ok(())
}
