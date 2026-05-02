import React, { useState } from 'react'
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Menu,
  MenuItem,
  Divider,
  Fab,
} from '@mui/material'
import {
  Add as AddIcon,
  MoreVert as MoreIcon,
  PlayArrow as PlayIcon,
  Save as SaveIcon,
  FlashOn as AIIcon,
} from '@mui/icons-material'
import ReactFlow, {
  Node,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  MiniMap,
  Background,
  BackgroundVariant,
} from 'reactflow'
import 'reactflow/dist/style.css'

interface WorkflowNode extends Node {
  data: {
    label: string
    type: string
    description?: string
    config?: Record<string, any>
  }
}

const nodeTypes = {
  // Custom node types can be added here
}

const WorkflowBuilder: React.FC = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNode[]>([
    {
      id: '1',
      type: 'default',
      position: { x: 250, y: 50 },
      data: { label: 'Start', type: 'trigger', description: 'Workflow trigger point' },
    },
  ])
  
  const [edges, setEdges, onEdgesChange] = useEdgesState([
    {
      id: 'e1-2',
      source: '1',
      target: '2',
      animated: true,
    },
  ])

  const [nodeMenuAnchor, setNodeMenuAnchor] = useState<null | HTMLElement>(null)
  const [isPreview, setIsPreview] = useState(false)

  const workflowComponents = [
    {
      category: 'Triggers',
      items: [
        { id: 'webhook', name: 'Webhook', description: 'Trigger on HTTP request' },
        { id: 'schedule', name: 'Schedule', description: 'Trigger on time-based schedule' },
        { id: 'db_change', name: 'Database Change', description: 'Trigger on data modifications' },
      ]
    },
    {
      category: 'Data Operations',
      items: [
        { id: 'query', name: 'Query Data', description: 'Fetch data from database' },
        { id: 'create', name: 'Create Record', description: 'Add new record' },
        { id: 'update', name: 'Update Record', description: 'Modify existing record' },
        { id: 'delete', name: 'Delete Record', description: 'Remove record' },
      ]
    },
    {
      category: 'Logic & Control',
      items: [
        { id: 'condition', name: 'Condition', description: 'Branch based on conditions' },
        { id: 'loop', name: 'Loop', description: 'Iterate over items' },
        { id: 'switch', name: 'Switch', description: 'Multiple conditional branches' },
      ]
    },
    {
      category: 'Integrations',
      items: [
        { id: 'api_call', name: 'API Call', description: 'Make HTTP request' },
        { id: 'email', name: 'Send Email', description: 'Send email notification' },
        { id: 'webhook', name: 'Send Webhook', description: 'Call external webhook' },
      ]
    },
    {
      category: 'AI & ML',
      items: [
        { id: 'text_gen', name: 'Text Generation', description: 'Generate text with AI' },
        { id: 'classification', name: 'Classification', description: 'Categorize data' },
        { id: 'sentiment', name: 'Sentiment Analysis', description: 'Analyze sentiment' },
      ]
    }
  ]

  const onConnect = (params: Connection) => setEdges((eds) => addEdge(params, eds))

  const addNode = (componentConfig: any) => {
    const newNode: WorkflowNode = {
      id: `node_${Date.now()}`,
      type: 'default',
      position: { x: 250, y: 150 },
      data: {
        label: componentConfig.name,
        type: componentConfig.id,
        description: componentConfig.description,
      },
    }
    setNodes((nds) => nds.concat(newNode))
  }

  const handleNodeMenuClose = () => {
    setNodeMenuAnchor(null)
  }

  const handleNodeMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    setNodeMenuAnchor(event.currentTarget)
  }

  return (
    <Box sx={{ flexGrow: 1, height: 'calc(100vh - 140px)' }}>
      {/* Top Toolbar */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">Workflow Builder</Typography>
        
        <Box>
          <Button
            variant="outlined"
            startIcon={<AIIcon />}
            onClick={() => {/* AI suggestions */}}
            sx={{ mr: 1 }}
          >
            AI Suggestions
          </Button>
          <Button
            variant="outlined"
            startIcon={<SaveIcon />}
            onClick={() => {/* Save workflow */}}
            sx={{ mr: 1 }}
          >
            Save
          </Button>
          <Button
            variant={isPreview ? "contained" : "outlined"}
            startIcon={<PlayIcon />}
            onClick={() => setIsPreview(!isPreview)}
          >
            {isPreview ? 'Exit Preview' : 'Preview'}
          </Button>
        </Box>
      </Box>

      <Box sx={{ display: 'flex', height: 'calc(100% - 60px)' }}>
        {/* Left Sidebar - Component Palette */}
        <Paper elevation={2} sx={{ width: '280px', mr: 2, overflowY: 'auto' }}>
          <Box sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
              <Typography variant="subtitle1">Components</Typography>
              <IconButton size="small" onClick={handleNodeMenuClick}>
                <MoreIcon />
              </IconButton>
            </Box>

            {/* Component Categories */}
            {workflowComponents.map((category, catIndex) => (
              <Box key={catIndex} sx={{ mb: 3 }}>
                <Typography variant="subtitle2" color="primary" sx={{ mb: 1 }}>
                  {category.category}
                </Typography>
                {category.items.map((item, itemIndex) => (
                  <Box
                    key={itemIndex}
                    sx={{
                      p: 1,
                      mb: 1,
                      border: 1,
                      borderColor: 'divider',
                      borderRadius: 1,
                      cursor: 'pointer',
                      '&:hover': {
                        backgroundColor: 'action.hover',
                        borderColor: 'primary.main',
                      }
                    }}
                    onClick={() => addNode(item)}
                  >
                    <Typography variant="body2" fontWeight="medium">
                      {item.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {item.description}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ))}
          </Box>
        </Paper>

        {/* Main Canvas - React Flow */}
        <Paper elevation={1} sx={{ flex: 1, position: 'relative' }}>
          <Box sx={{ width: '100%', height: '100%' }}>
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              fitView
            >
              <Controls />
              <MiniMap />
              <Background variant={BackgroundVariant.Dots} />
            </ReactFlow>
          </Box>
        </Paper>

        {/* Right Sidebar - Properties Panel */}
        <Paper elevation={2} sx={{ width: '300px', ml: 2, overflowY: 'auto' }}>
          <Box sx={{ p: 2 }}>
            <Typography variant="subtitle1" gutterBottom>
              Component Properties
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Select a node to configure its properties
            </Typography>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle1" gutterBottom>
              AI Assistant
            </Typography>
            <Typography variant="body2" color="text.secondary">
              I'll help you build optimal workflows!
            </Typography>
            
            <Box sx={{ mt: 2 }}>
              <Button variant="outlined" size="small" fullWidth sx={{ mb: 1 }}>
                Suggest Next Connection
              </Button>
              <Button variant="outlined" size="small" fullWidth sx={{ mb: 1 }}>
                Optimize Flow
              </Button>
              <Button variant="outlined" size="small" fullWidth sx={{ mb: 1 }}>
                Test Workflow
              </Button>
              <Button variant="outlined" size="small" fullWidth>
                Generate Documentation
              </Button>
            </Box>

            <Divider sx={{ my: 2 }} />

            <Typography variant="subtitle2" gutterBottom>
              Workflow Info
            </Typography>
            <Typography variant="body2" color="text.secondary">
              • {nodes.length} components<br/>
              • {edges.length} connections<br/>
              • Ready to test
            </Typography>
          </Box>
        </Paper>
      </Box>

      {/* Component Menu */}
      <Menu
        anchorEl={nodeMenuAnchor}
        open={Boolean(nodeMenuAnchor)}
        onClose={handleNodeMenuClose}
      >
        <MenuItem onClick={handleNodeMenuClose}>Import Template</MenuItem>
        <MenuItem onClick={handleNodeMenuClose}>Export Workflow</MenuItem>
        <Divider />
        <MenuItem onClick={handleNodeMenuClose}>Clear Canvas</MenuItem>
      </Menu>
    </Box>
  )
}

export default WorkflowBuilder
