import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import ThumbView from './pages/ThumbView.tsx'

const isThumb = window.location.pathname === '/thumb'

createRoot(document.getElementById('root')!).render(
  <StrictMode>{isThumb ? <ThumbView /> : <App />}</StrictMode>,
)
