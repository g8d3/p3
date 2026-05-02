import sqlite3 from 'sqlite3'
import Database from 'sqlite3'
import { v4 as uuidv4 } from 'uuid'

interface Project {
  id: string
  name: string
  description?: string
  createdAt: Date
  updatedAt: Date
}

interface CreateProjectInput {
  name: string
  description?: string
}

interface TableRow {
  id: string
  name: string
  description: string | null
  created_at: string
  updated_at: string
}

class ProjectDataSource {
  private db: any = null
  
  async initialize() {
    if (!this.db) {
      return new Promise((resolve, reject) => {
        this.db = new Database('./data/data.db', (err) => {
          if (err) {
            reject(err)
            return
          }
          
          this.db.run(`
            CREATE TABLE IF NOT EXISTS projects (
              id TEXT PRIMARY KEY,
              name TEXT NOT NULL,
              description TEXT,
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
          `, (createErr: any) => {
            if (createErr) {
              reject(createErr)
              return
            }
            resolve(this.db)
          })
        })
      })
    }
    return this.db
  }

  async getAll(): Promise<Project[]> {
    await this.initialize()
    const db = this.db!
    
    const rows: TableRow[] = await db.all(
      'SELECT * FROM projects ORDER BY created_at DESC'
    )
    
    return rows.map((row: TableRow) => ({
      id: row.id,
      name: row.name,
      description: row.description || undefined,
      createdAt: new Date(row.created_at),
      updatedAt: new Date(row.updated_at)
    }))
  }

  async getById(id: string): Promise<Project | null> {
    await this.initialize()
    const db = this.db!
    
    const row: TableRow | undefined = await db.get(
      'SELECT * FROM projects WHERE id = ?',
      [id]
    )
    
    if (!row) return null
    
    return {
      id: row.id,
      name: row.name,
      description: row.description || undefined,
      createdAt: new Date(row.created_at),
      updatedAt: new Date(row.updated_at)
    }
  }

  async create(input: CreateProjectInput): Promise<Project> {
    await this.initialize()
    const db = this.db!
    
    const id = uuidv4()
    const now = new Date().toISOString()
    
    await db.run(
      'INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)',
      [id, input.name, input.description || null, now, now]
    )
    
    return {
      id,
      name: input.name,
      description: input.description,
      createdAt: new Date(now),
      updatedAt: new Date(now)
    }
  }

  async update(id: string, updates: Partial<CreateProjectInput>): Promise<Project | null> {
    await this.initialize()
    const db = this.db!
    
    const existing = await this.getById(id)
    if (!existing) return null
    
    const updateFields = []
    const updateValues = []
    
    if (updates.name !== undefined) {
      updateFields.push('name = ?')
      updateValues.push(updates.name)
      existing.name = updates.name
    }
    
    if (updates.description !== undefined) {
      updateFields.push('description = ?')
      updateValues.push(updates.description)
      existing.description = updates.description
    }
    
    if (updateFields.length > 0) {
      updateFields.push('updated_at = ?')
      updateValues.push(new Date().toISOString())
      updateValues.push(id)
      
      await db.run(
        `UPDATE projects SET ${updateFields.join(', ')} WHERE id = ?`,
        updateValues
      )
      
      existing.updatedAt = new Date()
    }
    
    return existing
  }

  async delete(id: string): Promise<Project | null> {
    await this.initialize()
    const db = this.db!
    
    const existing = await this.getById(id)
    if (!existing) return null
    
    await db.run('DELETE FROM projects WHERE id = ?', [id])
    
    return existing
  }
}

export default ProjectDataSource
