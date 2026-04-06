import '@testing-library/jest-dom'

// Polyfill ResizeObserver — not implemented in jsdom but used by GlobeView/MapView
if (typeof globalThis.ResizeObserver === 'undefined') {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
}
