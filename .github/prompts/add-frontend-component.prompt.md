---
description: "Add a new React component to the construction-monitor frontend. Covers component file, TypeScript props, API wiring, styling, and accessibility. Use when: building a new UI element, adding a page section, creating a reusable widget."
name: "Add Frontend Component"
argument-hint: "Component name (PascalCase), which page or layout it belongs to, brief description of its behavior"
agent: "agent"
---

# Add a Frontend Component

You are working on the ARGUS construction-monitor frontend (React, TypeScript, Vite).

Steps to follow:
1. Check `frontend/src/components/` for an existing component in the same feature area to use as a style reference.
2. Create the component file under the appropriate subfolder. Export a named function component with explicit TypeScript props.
3. If the component fetches data, use the existing API client pattern in `frontend/src/api/`. Do not add raw `fetch` or `axios` calls outside that layer.
4. Apply existing design-system classes and tokens — do not introduce new CSS variables without checking `frontend/src/styles/` first.
5. Add `aria-label` or `role` attributes where interactive elements are present.
6. Register the component in the parent page or layout file.
7. Summarize: new file paths, changed parent files, accessibility notes, and any API contract assumptions.
