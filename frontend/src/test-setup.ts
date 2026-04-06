import '@testing-library/jest-dom'

/**
 * Polyfill ResizeObserver for jsdom environment.
 * Required for components using ResizeObserver (e.g., GlobeView map container resizing)
 */
if (!global.ResizeObserver) {
  global.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as any;
}
