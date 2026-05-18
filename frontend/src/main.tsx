import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import App from './App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
      <Toaster
        position="top-center"
        toastOptions={{
          style: {
            background: '#FAF9F7',
            color: '#1A1A1A',
            borderRadius: '12px',
            border: '1px solid #EDE9E3',
            fontFamily: 'DM Sans, sans-serif',
          },
          success: { iconTheme: { primary: '#8FAF8F', secondary: '#fff' } },
          error: { iconTheme: { primary: '#EE9A8F', secondary: '#fff' } },
        }}
      />
    </QueryClientProvider>
  </React.StrictMode>
)
