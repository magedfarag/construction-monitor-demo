import { useRef, useState, useCallback, useEffect, CSSProperties } from 'react';

interface DraggableState {
  isDragging: boolean;
  position: { x: number; y: number };
  offset: { x: number; y: number };
}

/**
 * Custom hook for making panels draggable by their header/title bar.
 * Returns props to spread on the container and header elements.
 * 
 * Usage:
 * ```tsx
 * const { containerProps, handleProps } = useDraggable();
 * return (
 *   <div {...containerProps}>
 *     <div {...handleProps}>Drag Me</div>
 *     <div>Panel content</div>
 *   </div>
 * );
 * ```
 */
export function useDraggable(initialX = 0, initialY = 0) {
  const [state, setState] = useState<DraggableState>({
    isDragging: false,
    position: { x: initialX, y: initialY },
    offset: { x: 0, y: 0 },
  });

  const dragRef = useRef<{ startX: number; startY: number }>({ startX: 0, startY: 0 });

  const handleMouseMove = useCallback((e: MouseEvent) => {
    setState(prev => {
      if (!prev.isDragging) return prev;
      return {
        ...prev,
        position: {
          x: e.clientX - prev.offset.x,
          y: e.clientY - prev.offset.y,
        },
      };
    });
  }, []);

  const handleMouseUp = useCallback(() => {
    setState(prev => ({ ...prev, isDragging: false }));
  }, []);

  // Attach/detach global listeners based on isDragging state
  useEffect(() => {
    if (state.isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [state.isDragging, handleMouseMove, handleMouseUp]);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    // Only drag if left mouse button + not clicking on interactive elements
    if (e.button !== 0) return;
    const target = e.target as HTMLElement;
    if (target.tagName === 'BUTTON' || target.tagName === 'INPUT' || target.tagName === 'A') return;

    dragRef.current = { startX: e.clientX, startY: e.clientY };
    setState(prev => ({
      ...prev,
      isDragging: true,
      offset: { x: e.clientX - prev.position.x, y: e.clientY - prev.position.y },
    }));
    e.preventDefault();
  }, []);

  const handleProps = {
    onMouseDown: handleMouseDown,
    style: { cursor: state.isDragging ? 'grabbing' : 'grab', userSelect: 'none' as const },
  };

  const containerStyle: CSSProperties = {
    transform: `translate(${state.position.x}px, ${state.position.y}px)`,
    transition: state.isDragging ? 'none' : 'transform 0.15s ease-out',
  };

  return {
    containerProps: { style: containerStyle },
    handleProps,
    isDragging: state.isDragging,
    position: state.position,
  };
}

