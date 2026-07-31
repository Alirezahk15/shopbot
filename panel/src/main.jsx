import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AppProvider } from './context/AppContext.jsx'
import { ToastProvider } from './components/Toast.jsx'
import App from './App.jsx'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30000,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <AppProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </AppProvider>
    </QueryClientProvider>
  </React.StrictMode>,
)
