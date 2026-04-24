import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App'
import TrainingSimulator from './pages/TrainingSimulator'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/training/link/:token" element={<TrainingSimulator />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
