import React from 'react'
import ReactDOM from 'react-dom/client'
import AmyWidget from './Widget'

declare global {
  interface Window {
    AmyWidget: typeof AmyWidget
    __amy_init__: () => void
  }
}

function init() {
  // Get embed_id from the script tag src URL
  const scripts = document.querySelectorAll('script[src*="widget.js"]')
  let embedId: string | null = null
  scripts.forEach((s) => {
    const src = (s as HTMLScriptElement).src
    const match = src.match(/embed_id=([^&]+)/)
    if (match) embedId = match[1]
  })

  // Create shadow DOM host so widget styles don't leak
  const host = document.createElement('div')
  host.id = 'amy-widget-host'
  host.style.cssText = 'position:fixed;z-index:2147483647;bottom:0;right:0;pointer-events:none;'
  document.body.appendChild(host)

  const shadow = host.attachShadow({ mode: 'open' })
  const container = document.createElement('div')
  container.style.pointerEvents = 'auto'
  shadow.appendChild(container)

  ReactDOM.createRoot(container).render(
    <React.StrictMode>
      <AmyWidget embedId={embedId} />
    </React.StrictMode>
  )
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init)
} else {
  init()
}
