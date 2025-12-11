import React, { useState } from 'react'
import { Box, Container, AppBar, Toolbar, Typography, Button } from '@mui/material'
import VisualEditor from './components/VisualEditor'
import DatabaseDesigner from './components/DatabaseDesigner'
import WorkflowBuilder from './components/WorkflowBuilder'
import Settings from './components/Settings'

function App() {
  const [currentView, setCurrentView] = useState('editor')

  const renderCurrentView = () => {
    switch (currentView) {
      case 'database':
        return <DatabaseDesigner />
      case 'workflow':
        return <WorkflowBuilder />
      case 'settings':
        return <Settings />
      default:
        return <VisualEditor />
    }
  }

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            No-Code AI Platform
          </Typography>
          <Button 
            color="inherit" 
            onClick={() => setCurrentView('editor')}
            variant={currentView === 'editor' ? 'outlined' : undefined}
          >
            Editor
          </Button>
          <Button 
            color="inherit" 
            onClick={() => setCurrentView('database')}
            variant={currentView === 'database' ? 'outlined' : undefined}
          >
            Database
          </Button>
          <Button 
            color="inherit" 
            onClick={() => setCurrentView('workflow')}
            variant={currentView === 'workflow' ? 'outlined' : undefined}
          >
            Workflow
          </Button>
          <Button 
            color="inherit" 
            onClick={() => setCurrentView('settings')}
            variant={currentView === 'settings' ? 'outlined' : undefined}
          >
            Config
          </Button>
          <Button color="inherit">Deploy</Button>
        </Toolbar>
      </AppBar>
      
      <Container maxWidth="xl" sx={{ mt: 2 }}>
        {renderCurrentView()}
      </Container>
    </Box>
  )
}

export default App
