import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { SpacetimeDBProvider } from 'spacetimedb/react'
import { DbConnection } from './module_bindings'
import './index.css'
import App from './App'

const WS_PORT = 3000
const HOST = `ws://${window.location.hostname}:${WS_PORT}`
const DB_NAME = 'usertables'

const identityTokenKey = `${HOST}/${DB_NAME}/auth_token`

const builder = DbConnection.builder()
  .withUri(HOST)
  .withDatabaseName(DB_NAME)
  .withToken(localStorage.getItem(identityTokenKey) || undefined)
  .onConnect((_conn, identity, token) => {
    localStorage.setItem(identityTokenKey, token)
    console.log('Connected as', identity.toHexString())
  })
  .onConnectError((_ctx, error) => {
    console.error('Connection error:', error)
  })

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <SpacetimeDBProvider connectionBuilder={builder}>
      <App />
    </SpacetimeDBProvider>
  </StrictMode>,
)
