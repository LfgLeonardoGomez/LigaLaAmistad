import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'

import { appRoutes } from './App'
import './index.css'

const container = document.getElementById('root')
if (!container) throw new Error('Missing #root element')

const router = createBrowserRouter(appRoutes)

createRoot(container).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
