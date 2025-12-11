import React, { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  Grid,
  TextField,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
} from '@mui/material'
import {
  Add as AddIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Bolt as GenerateIcon,
} from '@mui/icons-material'

interface Field {
  id: string
  name: string
  type: string
  required: boolean
  description: string
}

interface Table {
  id: string
  name: string
  fields: Field[]
  relationships: Array<{ type: string; target: string; field: string }>
}

const fieldTypes = [
  'String',
  'Number',
  'Boolean',
  'Date',
  'DateTime',
  'Text',
  'Email',
  'URL',
  'Image',
  'JSON',
  'Reference',
]

const DatabaseDesigner: React.FC = () => {
  const [tables, setTables] = useState<Table[]>([])
  const [selectedTable, setSelectedTable] = useState<Table | null>(null)
  const [aiSuggestionDialog, setAiSuggestionDialog] = useState(false)
  const [naturalLanguageInput, setNaturalLanguageInput] = useState('')

  const addTable = async () => {
    const newTable: Table = {
      id: `table_${Date.now()}`,
      name: 'New Table',
      fields: [
        { id: 'id', name: 'id', type: 'String', required: true, description: 'Primary key' },
        { id: 'created_at', name: 'created_at', type: 'DateTime', required: true, description: 'Creation timestamp' },
        { id: 'updated_at', name: 'updated_at', type: 'DateTime', required: true, description: 'Last update timestamp' },
      ],
      relationships: [],
    }
    
    // Add to backend
    try {
      const response = await fetch('http://localhost:4000/api/tables', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newTable)
      })
      
      if (response.ok) {
        setTables([...tables, newTable])
        setSelectedTable(newTable)
      } else {
        console.error('Failed to create table')
      }
    } catch (error) {
      console.error('Error creating table:', error)
      // Fallback to local state for demo
      setTables([...tables, newTable])
      setSelectedTable(newTable)
    }
  }

  const addField = (tableId: string) => {
    if (!selectedTable) return

    const newField: Field = {
      id: `field_${Date.now()}`,
      name: 'new_field',
      type: 'String',
      required: false,
      description: '',
    }

    const updatedTables = tables.map(table =>
      table.id === tableId
        ? { ...table, fields: [...table.fields, newField] }
        : table
    )
    setTables(updatedTables)
    setSelectedTable({ ...selectedTable, fields: [...selectedTable.fields, newField] })
  }

  const updateField = (tableId: string, fieldId: string, updates: Partial<Field>) => {
    const updatedTables = tables.map(table =>
      table.id === tableId
        ? {
            ...table,
            fields: table.fields.map(field =>
              field.id === fieldId ? { ...field, ...updates } : field
            ),
          }
        : table
    )
    setTables(updatedTables)
    if (selectedTable && selectedTable.id === tableId) {
      setSelectedTable(
        updatedTables.find(t => t.id === tableId) || null
      )
    }
  }

  const deleteField = (tableId: string, fieldId: string) => {
    const updatedTables = tables.map(table =>
      table.id === tableId
        ? {
            ...table,
            fields: table.fields.filter(field => field.id !== fieldId),
          }
        : table
    )
    setTables(updatedTables)
    if (selectedTable && selectedTable.id === tableId) {
      setSelectedTable(
        updatedTables.find(t => t.id === tableId) || null
      )
    }
  }

  const generateFromNaturalLanguage = async () => {
    if (naturalLanguageInput.trim()) {
      try {
        // Get AI settings from localStorage
        const apiKey = localStorage.getItem('nocode-api-key')
        const model = localStorage.getItem('nocode-model') || 'gpt-4'
        const baseUrl = localStorage.getItem('nocode-base-url') || 'https://api.openai.com/v1'
        
        if (!apiKey) {
          alert('Please configure your AI API key in the Settings page first')
          return
        }

        const response = await fetch(`${baseUrl}/chat/completions`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${apiKey}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: model,
            messages: [
              {
                role: 'system',
                content: 'You are a database schema expert. Based on the user\'s description, generate an optimal database schema in JSON format. Return a response with this structure: {"name": "table_name", "description": "description", "fields": [{"id": "field_id", "name": "field_name", "type": "field_type", "required": true/false, "description": "field_description"}]}. Use common field types like String, Number, Boolean, Email, DateTime, Text, URL, Image. Always include id, created_at, and updated_at fields.'
              },
              {
                role: 'user',
                content: naturalLanguageInput
              }
            ],
            max_tokens: 1000,
            temperature: 0.7,
          }),
        })

        if (response.ok) {
          const data = await response.json()
          const content = data.choices[0].message.content
          
          // Try to parse the AI response as JSON
          let aiTable
          try {
            aiTable = JSON.parse(content)
            // Ensure required fields
            if (!aiTable.fields || !Array.isArray(aiTable.fields)) {
              throw new Error('Invalid schema format')
            }
            
            // Add standard fields if not present
            const standardFields = [
              { id: 'id', name: 'id', type: 'String', required: true, description: 'Primary key' },
              { id: 'created_at', name: 'created_at', type: 'DateTime', required: true, description: 'Creation timestamp' },
              { id: 'updated_at', name: 'updated_at', type: 'DateTime', required: true, description: 'Last update timestamp' }
            ]
            
            // Check if standard fields are already present
            standardFields.forEach((standardField) => {
              if (!aiTable.fields.find((field: any) => field.name === standardField.name)) {
                aiTable.fields.unshift(standardField)
              }
            })
            
          } catch (parseError) {
            // Fallback to mock table if JSON parsing fails
            console.error('Failed to parse AI response, using mock table')
            aiTable = {
              name: 'users',
              description: 'Generated from your description',
              fields: [
                { id: 'id', name: 'id', type: 'String', required: true, description: 'Primary key' },
                { id: 'email', name: 'email', type: 'Email', required: true, description: 'User email address' },
                { id: 'name', name: 'name', type: 'String', required: true, description: 'Full name' },
                { id: 'created_at', name: 'created_at', type: 'DateTime', required: true, description: 'Creation timestamp' },
                { id: 'updated_at', name: 'updated_at', type: 'DateTime', required: true, description: 'Last update timestamp' }
              ]
            }
          }

          const newTable: Table = {
            id: `table_${Date.now()}`,
            name: aiTable.name || 'Auto Generated Table',
            fields: aiTable.fields.map((field: any, index: number) => ({
              ...field,
              id: field.id || `field_${index}`
            })),
            relationships: [],
          }

          // Save to backend
          const backendResponse = await fetch('http://localhost:4000/api/tables', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(newTable)
          })

          if (backendResponse.ok) {
            setTables([...tables, newTable])
            setSelectedTable(newTable)
            setAiSuggestionDialog(false)
            setNaturalLanguageInput('')
          } else {
            throw new Error('Failed to save table to backend')
          }
        } else {
          throw new Error('AI request failed')
        }
      } catch (error) {
        console.error('Error generating schema:', error)
        // Fallback to mock table
        const mockTable: Table = {
          id: `table_${Date.now()}`,
          name: 'Mock Table',
          fields: [
            { id: 'id', name: 'id', type: 'String', required: true, description: 'Primary key' },
            { id: 'name', name: 'name', type: 'String', required: true, description: 'Name field' },
            { id: 'created_at', name: 'created_at', type: 'DateTime', required: true, description: 'Creation timestamp' },
            { id: 'updated_at', name: 'updated_at', type: 'DateTime', required: true, description: 'Last update timestamp' }
          ],
          relationships: [],
        }

        setTables([...tables, mockTable])
        setSelectedTable(mockTable)
        setAiSuggestionDialog(false)
        setNaturalLanguageInput('')
      }
    }
  }

  return (
    <Box sx={{ flexGrow: 1, p: 2 }}>
      <Grid container spacing={2}>
        {/* Left Panel - Tables List */}
        <Grid item xs={3}>
          <Paper elevation={2} sx={{ p: 2, height: 'calc(100vh - 200px)' }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
              <Typography variant="h6">Database Tables</Typography>
              <IconButton onClick={addTable} color="primary">
                <AddIcon />
              </IconButton>
            </Box>
            
            <List>
              {tables.map(table => (
                <ListItem
                  key={table.id}
                  button
                  selected={selectedTable?.id === table.id}
                  onClick={() => setSelectedTable(table)}
                >
                  <ListItemText 
                    primary={table.name}
                    secondary={`${table.fields.length} fields`}
                  />
                  <ListItemSecondaryAction>
                    <IconButton size="small">
                      <EditIcon />
                    </IconButton>
                    <IconButton size="small">
                      <DeleteIcon />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>

            <Divider sx={{ my: 2 }} />
            
            <Button
              fullWidth
              variant="outlined"
              startIcon={<GenerateIcon />}
              onClick={() => setAiSuggestionDialog(true)}
            >
              AI Generate from Description
            </Button>
          </Paper>
        </Grid>

        {/* Main Panel - Table Editor */}
        <Grid item xs={6}>
          <Paper elevation={2} sx={{ p: 2, height: 'calc(100vh - 200px)', overflowY: 'auto' }}>
            {selectedTable ? (
              <Box>
                {/* Table Header */}
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
                  <Typography variant="h6" sx={{ flexGrow: 1 }}>
                    {selectedTable.name}
                  </Typography>
                  <IconButton color="primary">
                    <SaveIcon />
                  </IconButton>
                </Box>

                {/* Fields Section */}
                <Box sx={{ mb: 3 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
                    <Typography variant="subtitle1">Fields</Typography>
                    <Button
                      size="small"
                      startIcon={<AddIcon />}
                      onClick={() => addField(selectedTable.id)}
                    >
                      Add Field
                    </Button>
                  </Box>

                  {selectedTable.fields.map((field, index) => (
                    <Box key={field.id} sx={{ mb: 2, p: 2, border: 1, borderColor: 'divider', borderRadius: 1 }}>
                      <Grid container spacing={2}>
                        <Grid item xs={4}>
                          <TextField
                            fullWidth
                            label="Field Name"
                            value={field.name}
                            onChange={(e) => updateField(selectedTable.id, field.id, { name: e.target.value })}
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={3}>
                          <FormControl fullWidth size="small">
                            <InputLabel>Type</InputLabel>
                            <Select
                              value={field.type}
                              label="Type"
                              onChange={(e) => updateField(selectedTable.id, field.id, { type: e.target.value })}
                            >
                              {fieldTypes.map(type => (
                                <MenuItem key={type} value={type}>{type}</MenuItem>
                              ))}
                            </Select>
                          </FormControl>
                        </Grid>
                        <Grid item xs={4}>
                          <TextField
                            fullWidth
                            label="Description"
                            value={field.description}
                            onChange={(e) => updateField(selectedTable.id, field.id, { description: e.target.value })}
                            size="small"
                          />
                        </Grid>
                        <Grid item xs={1}>
                          <Box sx={{ display: 'flex', alignItems: 'center' }}>
                            <IconButton
                              size="small"
                              color="error"
                              onClick={() => deleteField(selectedTable.id, field.id)}
                            >
                              <DeleteIcon />
                            </IconButton>
                          </Box>
                        </Grid>
                      </Grid>
                    </Box>
                  ))}
                </Box>

                {/* Relationships Section */}
                <Box>
                  <Typography variant="subtitle1" gutterBottom>
                    Relationships
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    No relationships defined yet
                  </Typography>
                </Box>
              </Box>
            ) : (
              <Box
                sx={{
                  height: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  textAlign: 'center'
                }}
              >
                <Box>
                  <Typography variant="h6" gutterBottom color="text.secondary">
                Select a table or create a new one
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Start by designing your database structure
                  </Typography>
                </Box>
              </Box>
            )}
          </Paper>
        </Grid>

        {/* Right Panel - AI Assistant */}
        <Grid item xs={3}>
          <Paper elevation={2} sx={{ p: 2, height: 'calc(100vh - 200px)' }}>
            <Typography variant="h6" gutterBottom>
              AI Database Assistant
            </Typography>
            <Typography variant="body2" color="text.secondary">
              I'll help you design optimal database schemas and relationships.
            </Typography>
            
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Suggestions:
              </Typography>
              <Button variant="outlined" size="small" fullWidth sx={{ mb: 1 }}>
                Optimize Field Types
              </Button>
              <Button variant="outlined" size="small" fullWidth sx={{ mb: 1 }}>
                Suggest Relationships
              </Button>
              <Button variant="outlined" size="small" fullWidth sx={{ mb: 1 }}>
                Generate Sample Data
              </Button>
              <Button variant="outlined" size="small" fullWidth>
                Validate Schema
              </Button>
            </Box>

            {selectedTable && (
              <Box sx={{ mt: 3 }}>
                <Typography variant="subtitle2" gutterBottom>
                  Current Table Insights:
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  • {selectedTable.fields.length} fields defined
                  • 0 relationships established  
                  • Estimated storage: ~{selectedTable.fields.length * 100} bytes/record
                </Typography>
              </Box>
            )}
          </Paper>
        </Grid>
      </Grid>

      {/* AI Generation Dialog */}
      <Dialog open={aiSuggestionDialog} onClose={() => setAiSuggestionDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>Generate Database Schema with AI</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Describe your database structure in natural language, and I'll generate an optimized schema for you.
          </Typography>
          <TextField
            fullWidth
            multiline
            rows={4}
            placeholder="Example: I need a user management system with user profiles, roles, and permissions. Users should have basic info, profile pictures, and role assignments."
            value={naturalLanguageInput}
            onChange={(e) => setNaturalLanguageInput(e.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAiSuggestionDialog(false)}>
            Cancel
          </Button>
          <Button onClick={generateFromNaturalLanguage} variant="contained" color="primary">
            Generate Schema
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default DatabaseDesigner
