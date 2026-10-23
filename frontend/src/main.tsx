import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Dashboard from './pages/Dashboard'
import './styles/global.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Dashboard />
  </StrictMode>,
)
