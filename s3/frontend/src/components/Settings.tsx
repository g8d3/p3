import React, { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Divider,
  Alert,
  Snackbar,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
} from '@mui/material'
import {
  Settings as SettingsIcon,
  Save as SaveIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Check as CheckIcon,
  Add as AddIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
} from '@mui/icons-material'

interface AIConnection {
  id: string
  name: string
  apiKey: string
  model: string
  baseUrl: string
  maxTokens: number
  temperature: number
  provider: 'openai' | 'claude' | 'custom'
}

const Settings: React.FC = () => {
  const [connections, setConnections] = useState<AIConnection[]>(() => {
    const saved = localStorage.getItem('nocode-connections')
    return saved ? JSON.parse(saved) : [{
      id: 'connection-1',
      name: 'Default Connection',
      apiKey: localStorage.getItem('nocode-api-key') || '',
      model: localStorage.getItem('nocode-model') || 'gpt-4',
      baseUrl: localStorage.getItem('nocode-base-url') || 'https://api.openai.com/v1',
      maxTokens: parseInt(localStorage.getItem('nocode-max-tokens') || '2000'),
      temperature: parseFloat(localStorage.getItem('nocode-temperature') || '0.7'),
      provider: 'openai'
    }]
  })
  
  const [activeConnectionId, setActiveConnectionId] = useState(() => {
    return localStorage.getItem('nocode-active-connection') || connections[0]?.id || ''
  })
  
  const [expandedConnections, setExpandedConnections] = useState<string[]>([connections[0]?.id || ''])

  const addConnection = () => {
    const newConnection: AIConnection = {
      id: `connection-${Date.now()}`,
      name: `Connection ${connections.length + 1}`,
      apiKey: '',
      model: 'gpt-4',
      baseUrl: 'https://api.openai.com/v1',
      maxTokens: 2000,
      temperature: 0.7,
      provider: 'openai'
    }
    setConnections([...connections, newConnection])
    setActiveConnectionId(newConnection.id)
    setExpandedConnections([...expandedConnections, newConnection.id])
  }

  const removeConnection = (id: string) => {
    if (connections.length <= 1) return
    const newConnections = connections.filter(conn => conn.id !== id)
    setConnections(newConnections)
    if (activeConnectionId === id) {
      setActiveConnectionId(newConnections[0].id)
    }
    setExpandedConnections(expandedConnections.filter(connId => connId !== id))
  }

  const updateConnection = (id: string, updates: Partial<AIConnection>) => {
    setConnections(connections.map(conn => 
      conn.id === id ? { ...conn, ...updates } : conn
    ))
  }

  const handleSave = () => {
    localStorage.setItem('nocode-connections', JSON.stringify(connections))
    localStorage.setItem('nocode-active-connection', activeConnectionId)
    setSaveSuccess(true)
  }

  const activeConnection = connections.find(conn => conn.id === activeConnectionId) || connections[0] || {
    id: 'temp',
    name: 'Default',
    apiKey: '',
    model: 'gpt-4',
    baseUrl: 'https://api.openai.com/v1',
    maxTokens: 2000,
    temperature: 0.7,
    provider: 'openai' as const
  }

  const [showApiKeys, setShowApiKeys] = useState<{ [key: string]: boolean }>({})
  const [saveSuccess, setSaveSuccess] = useState(false)

  const toggleApiKeyVisibility = (connectionId: string) => {
    setShowApiKeys(prev => ({ ...prev, [connectionId]: !prev[connectionId] }))
  }

  const handleAccordionChange = (connectionId: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
    if (isExpanded) {
      setExpandedConnections([...expandedConnections, connectionId])
    } else {
      setExpandedConnections(expandedConnections.filter(id => id !== connectionId))
    }
  }

  return (
    <Box sx={{ p: 3, maxWidth: 800, mx: 'auto' }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Typography variant="h4" sx={{ display: 'flex', alignItems: 'center' }}>
            <SettingsIcon sx={{ mr: 2 }} />
            AI Configuration
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={addConnection}
            color="primary"
          >
            Add Connection
          </Button>
        </Box>
        
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          Configure multiple AI provider connections with custom models and settings. Each connection can use a different provider, API, or model.
        </Typography>

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {connections.map((connection) => (
            <Accordion
              key={connection.id}
              expanded={expandedConnections.includes(connection.id)}
              onChange={handleAccordionChange(connection.id)}
              sx={{
                '&:before': { display: 'none' },
                boxShadow: 1,
                borderRadius: 1,
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                sx={{ 
                  '& .MuiAccordionSummary-content': { 
                    display: 'flex', 
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }
                }}
              >
                <Typography variant="h6">
                  {connection.name}
                </Typography>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Chip 
                    label={connection.provider === 'openai' ? 'OpenAI' : connection.provider === 'claude' ? 'Claude' : 'Custom'} 
                    size="small"
                    color={connection.id === activeConnectionId ? 'primary' : 'default'}
                    onClick={(e) => {
                      e.stopPropagation()
                      setActiveConnectionId(connection.id)
                    }}
                  />
                  <Chip 
                    label="Active" 
                    size="small"
                    color={connection.id === activeConnectionId ? 'success' : 'default'}
                    sx={{ opacity: connection.id === activeConnectionId ? 1 : 0.3 }}
                  />
                  {connections.length > 1 && (
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation()
                        removeConnection(connection.id)
                      }}
                    >
                      <DeleteIcon />
                    </IconButton>
                  )}
                </Box>
              </AccordionSummary>
              
              <AccordionDetails>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                  {/* Connection Name */}
                  <TextField
                    fullWidth
                    label="Connection Name"
                    value={connection.name}
                    onChange={(e) => updateConnection(connection.id, { name: e.target.value })}
                    helperText="Give your connection a descriptive name"
                  />

                  {/* Provider Selection */}
                  <FormControl fullWidth>
                    <InputLabel>Provider</InputLabel>
                    <Select
                      value={connection.provider}
                      label="Provider"
                      onChange={(e) => updateConnection(connection.id, { provider: e.target.value as any })}
                    >
                      <MenuItem value="openai">OpenAI</MenuItem>
                      <MenuItem value="claude">Anthropic Claude</MenuItem>
                      <MenuItem value="custom">Custom</MenuItem>
                    </Select>
                  </FormControl>

                  {/* API Key */}
                  <TextField
                    fullWidth
                    label="API Key"
                    type={showApiKeys[connection.id] ? 'text' : 'password'}
                    value={connection.apiKey}
                    onChange={(e) => updateConnection(connection.id, { apiKey: e.target.value })}
                    placeholder={connection.provider === 'openai' ? 'sk-...' : connection.provider === 'claude' ? 'sk-ant-' : 'your-api-key'}
                    helperText={`${connection.provider === 'openai' ? 'OpenAI' : connection.provider === 'claude' ? 'Claude' : 'Custom'} API key`}
                    InputProps={{
                      endAdornment: (
                        <IconButton
                          onClick={() => toggleApiKeyVisibility(connection.id)}
                          edge="end"
                        >
                          {showApiKeys[connection.id] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                        </IconButton>
                      ),
                    }}
                  />

                  {/* Model Field - Now supports any model name */}
                  <TextField
                    fullWidth
                    label="Model Name"
                    value={connection.model}
                    onChange={(e) => updateConnection(connection.id, { model: e.target.value })}
                    placeholder={connection.provider === 'openai' ? 'gpt-4, gpt-4-turbo, gpt-3.5-turbo' : 
                              connection.provider === 'claude' ? 'claude-3-opus-20240229, claude-3-sonnet-20240229' :
                              'any-model-name'}
                    helperText="Enter any model name supported by your provider"
                  />

                  {/* Base URL */}
                  <TextField
                    fullWidth
                    label="Base URL"
                    value={connection.baseUrl}
                    onChange={(e) => updateConnection(connection.id, { baseUrl: e.target.value })}
                    placeholder={connection.provider === 'openai' ? 'https://api.openai.com/v1' : 
                              connection.provider === 'claude' ? 'https://api.anthropic.com' :
                              'https://your-api-endpoint.com/v1'}
                    helperText="Your AI provider's API base URL (leave empty to use provider default)"
                  />

                  <Divider />

                  {/* Advanced Settings */}
                  <Typography variant="h6">Advanced Settings</Typography>
                  
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <TextField
                      sx={{ flex: 1 }}
                      label="Max Tokens"
                      type="number"
                      value={connection.maxTokens}
                      onChange={(e) => updateConnection(connection.id, { maxTokens: parseInt(e.target.value) || 2000 })}
                      helperText="Maximum response tokens"
                      inputProps={{ min: 1, max: 4000 }}
                    />

                    <TextField
                      sx={{ flex: 1 }}
                      label="Temperature"
                      type="number"
                      value={connection.temperature}
                      onChange={(e) => updateConnection(connection.id, { temperature: parseFloat(e.target.value) || 0.7 })}
                      helperText="Creativity (0-1)"
                      inputProps={{ min: 0, max: 2, step: 0.1 }}
                    />
                  </Box>
                </Box>
              </AccordionDetails>
            </Accordion>
          ))}
        </Box>

        <Divider sx={{ my: 4 }} />

        {/* Active Connection Selection */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" gutterBottom>
            Active Connection
          </Typography>
          <FormControl fullWidth>
            <InputLabel>Select Active Connection</InputLabel>
            <Select
              value={activeConnectionId}
              label="Select Active Connection"
              onChange={(e) => setActiveConnectionId(e.target.value)}
            >
              {connections.map(conn => (
                <MenuItem key={conn.id} value={conn.id}>
                  {conn.name} ({conn.provider})
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {/* Save Button */}
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 4 }}>
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            size="large"
          >
            Save All Settings
          </Button>
        </Box>
      </Paper>

      {/* Success Notification */}
      <Snackbar
        open={saveSuccess}
        autoHideDuration={3000}
        onClose={() => setSaveSuccess(false)}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={() => setSaveSuccess(false)} severity="success" icon={<CheckIcon />}>
          Settings saved successfully! {connections.length} connection(s) configured.
        </Alert>
      </Snackbar>
    </Box>
  )
}

export default Settings
