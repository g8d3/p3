import React, { useState, useCallback } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Chip,
  Fab,
  Snackbar,
  Alert,
} from '@mui/material'
import {
  Add as AddIcon,
  Storage as DatabaseIcon,
  AccountTree as WorkflowIcon,
  Widgets as ComponentIcon,
  PlayArrow as PlayIcon,
  DragIndicator as DragIcon,
  Delete as DeleteIcon,
} from '@mui/icons-material'
import {
  DndProvider,
  useDragDrop,
  useDragOver,
  DragDropMonitor,
  useDragItem,
  Identifier,
} from 'react-dnd'

interface DraggableComponent {
  id: string
  name: string
  description: string
  type: string
  icon: React.ReactNode
  category: string
}

interface DroppedItem {
  id: string
  type: string
  x: number
  y: number
  width: number
  height: number
  data: any
}

interface CanvasItem {
  id: string
  type: string
  x: number
  y: number
  width: number
  height: number
  data: any
}

const VisualEditor: React.FC = () => {
  const [droppedItems, setDroppedItems] = useState<CanvasItem[]>([])
  const [showAlert, setShowAlert] = useState(false)
  const [alertMessage, setAlertMessage] = useState('')
  const [draggedOver, setDraggedOver] = useState(false)

  const dataComponents: DraggableComponent[] = [
    { 
      id: 'db-table',
      name: 'Database Table', 
      description: 'Create and manage database tables',
      type: 'data',
      icon: <DatabaseIcon />,
      category: 'Data'
    },
    { 
      id: 'data-grid', 
      name: 'Data Grid', 
      description: 'Interactive data display',
      type: 'data',
      icon: <DatabaseIcon />,
      category: 'Data'
    },
    { 
      id: 'form-builder',
      name: 'Form Builder', 
      description: 'AI-powered form generation',
      type: 'data',
      fontawesome 'icon: <ComponentIcon />,
      category: 'Data'
    }
  ]

  const workflowComponents: DraggableComponent[] = [
    { 
      id: 'api-connector',
      name: 'API Connector',
      description: 'Connect to external APIs',
      type: 'workflow',
      icon: <WorkflowIcon />,
      category: 'Workflow'
    },
    { 
      id: 'logic-block',
      name: 'Logic Block',
      description: 'Conditional logic and loops',
      type: 'workflow',
      icon: <WorkflowIcon />,
      category: 'Workflow'
    },
    { 
      id: 'data-transform',
      name: 'Data Transform',
      description: 'Transform and process data',
      type: 'workflow',
      icon: <WorkflowIcon />,
      category: 'Workflow'
    }
  ]

  const uiComponents: DraggableComponent[] = [
    { 
      id: 'smart-card',
      name: 'Smart Card',
      description: 'AI-adaptive UI component',
      type: 'ui',
      icon: <ComponentIcon />,
      category: 'UI'
    },
    { 
      id: 'dynamic-chart',
      name: 'Dynamic Chart',
      description: 'Data visualization',
      type: 'ui',
      icon: <ComponentIcon />,
      category: 'UI'
    },
    {
      id: 'smart-form',
      name: 'Smart Form',
      description: 'Intelligent form handling',
      type: 'ui',
      icon: <ComponentIcon />,
      category: 'UI'
    }
  ]

  const addComponentToCanvas = useCallback((component: DroppedItem) => {
    const newItem: CanvasItem = {
      id: `dropped-${Date.now()}`,
      type: component.type,
      x: Math.random() * 400 + 50,
      y: Math.random() * 300 + 50,
      width: 120,
      height: 80,
      data: component
    }
    setDroppedItems(prev => [...prev, newItem])
    setShowAlert(true)
    setAlertMessage(`${component.name} added to canvas`)
    setTimeout(() => setShowAlert(false), 3000)
  }, [setDroppedItems, setShowAlert, setAlertMessage])

  const togglePreview = useCallback(() => {
    setIsPreview(prev => !prev)
  }, [])

  const clearCanvas = useCallback(() => {
    setDroppedItems([])
    setShowAlert(true)
    setAlertMessage('Canvas cleared')
    setTimeout(() => setShowAlert(false), 3000)
  }, [setDroppedItems, setShowAlert, setAlertMessage])

  const removeItem = useCallback((id: string) => {
    setDroppedItems(prev => prev.filter(item => item.id !== id))
    setShowAlert(true)
    setAlertMessage('Component removed from canvas')
    setTimeout(() => setShowAlert(false), 3000)
  }, [])

  const moveItem = useCallback((id: string, newX: number, newY: number) => {
    setDropppedItems(prev => 
      prev.map(item => 
        item.id === id ? { ...item, x: newX, y: newY } : item
      )
    ))
  }, [])

  const [showApiKeys, setShowApiKeys] = useState<{ [key: string]: boolean }>({})

  const toggleApiKeyVisibility = (id: string) => {
    setShowApiKeys(prev => ({ ...prev, [id]: !prev[id] }))
  }

  const [{ getItem }, drag] = useDragItem({
    type: 'component',
    item: (id: string) => ({
      id: id,
      type: 'component'
    }),
    collect: (monitor: any) => ({
      id: monitor.getItem().id,
      type: 'component'
    })
  })

  const showAllApiKeys = () => {
    const allVisible = Object.entries(showApiKeys).every(([_, visible]) => visible)
    setShowApiKeys(prev => {
      const updated = Object.fromEntries(
        Object.entries(prev).map(([id, visible]) => [id, !allVisible])
      )
      return updated
    })
  }

  const [connectors] = React.useState<Array<{
    id: string
    data: any
  }>>([])

  const addConnection = () => {
    const newConnection = {
      id: `connection-${Date.now()}`,
      data: { name: 'New Connection', apiKey: '', model: '', baseUrl: '' }
    }
    setConnectors(prev => [...prev, newConnection])
  }

  const updateConnection = (id: string, data: any) => {
    setConnectors(prev => 
      prev.map(conn => 
        conn.id === id ? { ...conn, data } : conn
      )
    )
  }

  const deleteConnection = (id: string) => {
    setConnectors(prev => prev.filter(conn => conn.id !== id))
  }

  const testConnection = async (connection: any) => {
    if (!connection.data.apiKey) {
      return { success: false, message: 'API key is required' }
    }
    
    try {
      const response = await fetch(`${connection.data.baseUrl || 'https://api.openai.com/v1'}/chat/completions`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${connection.data.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: connection.data.model || 'gpt-4',
          messages: [
            {
              role: 'system',
              content: 'You are a helpful AI assistant.'
            },
            {
              role: 'user',
              content: 'Hello! Test connection.'
            }
          ],
          max_tokens: 10,
        }),
      })

      if (response.ok) {
        const data = await response.json() as any
        return { success: true, message: 'Connection successful', data }
      } else {
        return { success: false, error: 'Connection failed' }
      }
    } catch (error) {
      return { success: false, error: error instanceof Error ? error.message : 'Connection error' }
    }
  }

  return (
    <DndProvider>
      <Box sx={{ flexGrow: 1, height: 'calc(100vh - 140px)' }}>
        {/* Top Toolbar */}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ mr: 2 }}>Visual Editor</Typography>
          
          <Box>
            <Button
              variant={isPreview ? "contained" : "outlined"}
              onClick={togglePreview}
              sx={{ mr: 1 }}
            >
              {isPreview ? 'Exit Preview' : 'Preview'}
            </Button>
            <Button
              variant="outlined"
              onClick={clearCanvas}
              sx={{ mr: 1 }}
            >
              Clear Canvas
            </Button>
            <Button
              variant="outlined"
              onClick={addAllApiKeys}
              color={Object.values(showApiKeys).some(v => v) ? 'primary' : 'default'}
            >
              {Object.keys(showApiKeys).length > 0 ? 'Hide API Keys' : 'Show API Keys'}
            </Button>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', height: 'calc(100% - 60px)' }}>
          {/* Left Sidebar - Component Palette */}
          <Paper 
            elevation={2} 
            sx={{ 
              width: '280px', 
              mr: 2, 
              overflowY: 'auto',
              userSelect: 'none',
              '& .MuiPaper-root': {
                backgroundColor: '#fafafa'
              }
            }}
          >
            <Box sx={{ p: 2 }}>
              <Typography variant="subtitle1" gutterBottom>
                Component Library
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Drag components to the canvas
              </Typography>

              {/* Data Components */}
              <Typography variant="subtitle2" color="primary" sx={{ mt: 3, mb: 1 }}>
                Data Components
              </Typography>
              <Box sx={{ border: '1px solid #ddd', borderRadius: 1, p: 1, mb: 2 }}>
                {dataComponents.map((component) => (
                  <div
                    key={component.id}
                    ref={(element: any) => drag(drop(element))}
                    style={{
                      padding: '12px',
                      margin: '4px 0',
                      border: '1px dashed #ccc',
                      borderRadius: '8px',
                      cursor: 'grab',
                      background: '#fff',
                      backgroundColor: draggedOver ? '#f0f8ff' : null,
                      transition: 'all 0.2s ease',
                      '&:active': { borderStyle: 'solid', borderColor: 'primary.main' }
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <DragIcon sx={{ fontSize: 16, color: draggedOver ? 'primary.main' : 'text.secondary' }} />
                      <Box>
                        <Typography variant="body2" fontWeight="medium">
                          {component.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {component.description}
                        </Typography>
                      </Box>
                    </Box>
                  </div>
                ))}
              </Box>

              {/* Workflow Components */}
              <Typography variant="subtitle2" color="primary" sx={{ mt: 3, mb: 1 }}>
                Workflow Components
              </Typography>
              <Box sx={{ border: '1px solid #ddd', borderRadius: 1, p: 1, mb: 2 }}>
                {workflowComponents.map((component) => (
                  <div
                    key={component.id}
                    ref={(element: any) => drag(drop(element))}
                    style={{
                      padding: '12px',
                      margin: '4px 0',
                      border: '1px dashed #ccc',
                      borderRadius: '8px',
                      cursor: 'grab',
                      background: '#fff',
                      backgroundColor: dragOver ? '#f0f8ff' : null,
                      transition: 'all 0.2s ease',
                      '&:active': { borderStyle: 'solid', borderColor: 'secondary.main' }
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <DragIcon sx={{ fontSize: 16, color: dragOver ? 'secondary.main' : 'text.secondary' }} />
                      <Box>
                        <Typography variant="body2" fontWeight="medium">
                          {component.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {component.description}
                        </Typography>
                      </Box>
                    </Box>
                  </div>
                ))}
              </Box>

              {/* UI Components */}
              <Typography variant="subtitle2" color="primary" sx={{ mt: 3, mb: 1 }}>
                UI Components
              </Typography>
              <Box sx={{ border: '1px solid #ddd', borderRadius: 1, p: 1, mb: 2 }}>
                {uiComponents.map((component) => (
                  <div
                    key={component.id}
                    ref={(element: any) => drag(drop(element))}
                    style={{
                      padding: '12px',
                      margin: '4px 0',
                      border: '1px dashed #ccc',
                      borderRadius: '8px',
                      cursor: 'grab',
                      background: '#fff',
                      backgroundColor: dragOver ? '#f0f8ff' : null,
                      transition: 'all 0.2s ease',
                      '&:active': { borderStyle: 'solid', borderColor: 'info.main' }
                    }}
                  >
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                      <DragIcon sx={{ fontSize: 16, color: dragOver ? 'info.main' : 'text.secondary' }} />
                      <Box>
                        <Typography variant="body2" fontWeight="medium">
                          {component.name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {component.description}
                        </Typography>
                      </Box>
                    </Box>
                  </div>
                ))}
              </Box>

              {/* API Connections Section */}
              <Typography variant="subtitle2" color="primary" sx={{ mt: 3, mb: 2 }}>
                API Connections
              </Typography>
              <Box sx={{ mb: 2 }}>
                <Button
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={addConnection}
                  fullWidth
                  sx={{ mb: 2 }}
                >
                  Add Connection
                </Button>
                
                {connectors.map((connection) => (
                  <Paper key={connection.id} sx={{ p: 2, mb: 2 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Typography variant="body2">
                        <strong>Connection {connection.id}</strong>
                      </Typography>
                      <IconButton
                        size="small"
                        onClick={() => deleteConnection(connection.id)}
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Box>
                    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                      {connection.data.name && (
                        <Chip 
                          label={`Name: ${connection.data.name}`} 
                          size="small"
                        />
                      )}
                      {connection.data.apiKey && (
                        <Chip 
                          label={`✓ API Key Configured`} 
                          size="small" 
                          color="success"
                        />
                      )}
                      {connection.data.model && (
                        <Chip 
                          label={`Model: ${connection.data.model}`} 
                          size="small"
                        />
                      )}
                      {connection.data.baseUrl && connection.data.baseUrl !== 'https://api.openai.com/v1' && (
                        <Chip 
                          label={`Custom URL`} 
                          size="small" 
                          color="primary"
                        />
                      )}
                    </Box>
                  </Paper>
                ))}
              </Box>
            </Box>
