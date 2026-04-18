import { useDraggable } from '../../hooks/useDraggable';

export interface MapPopupData {
  id: string;
  x: number;
  y: number;
  html: string;
}

interface MapPopupProps extends MapPopupData {
  onClose: (id: string) => void;
}

/**
 * A draggable overlay popup rendered as a React element inside the map container.
 * Replaces maplibregl.Popup so the user can freely reposition popups to unobscured
 * areas of the map. Uses the existing useDraggable hook for drag behaviour.
 */
export function MapPopup({ id, x, y, html, onClose }: MapPopupProps) {
  const { containerProps, handleProps, isDragging } = useDraggable(x, y);

  return (
    <div
      {...containerProps}
      style={{
        ...containerProps.style,
        position: 'absolute',
        left: 0,
        top: 0,
        zIndex: 20,
        background: 'rgba(14,28,48,0.97)',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: 6,
        boxShadow: '0 4px 24px rgba(0,0,0,0.72)',
        maxWidth: 340,
        minWidth: 200,
        pointerEvents: 'all',
        userSelect: isDragging ? 'none' : 'auto',
      }}
    >
      {/* Drag handle bar */}
      <div
        {...handleProps}
        style={{
          ...handleProps.style,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '3px 8px',
          background: 'rgba(0,212,255,0.07)',
          borderRadius: '5px 5px 0 0',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        <span
          style={{
            fontSize: 9,
            color: 'rgba(255,255,255,0.3)',
            letterSpacing: '0.08em',
            userSelect: 'none',
          }}
        >
          ⠿ DRAG TO MOVE
        </span>
        <button
          onClick={() => onClose(id)}
          style={{
            background: 'none',
            border: 'none',
            color: 'rgba(255,255,255,0.45)',
            cursor: 'pointer',
            fontSize: 18,
            lineHeight: 1,
            padding: '0 2px',
            fontFamily: 'inherit',
          }}
          aria-label="Close popup"
        >
          ×
        </button>
      </div>

      {/* Popup content — same HTML that was previously rendered inside maplibregl.Popup */}
      {/* eslint-disable-next-line react/no-danger */}
      <div dangerouslySetInnerHTML={{ __html: html }} />
    </div>
  );
}
