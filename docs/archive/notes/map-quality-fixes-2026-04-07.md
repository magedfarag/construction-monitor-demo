# Map Quality Fixes - April 7, 2026

## Issues Fixed

### 1. ✅ CRITICAL: Circles Moving with Ships (Shadow Circles)
**Problem**: Circular halos were following ships and aircraft, creating confusing "shadow" effects in the sky.

**Root Cause**: The `entity-halo` layer had `circle-stroke-opacity: 0.45`, rendering visible stroke rings around every ship/aircraft.

**Fix Applied**:
- **MapView.tsx** (line ~948): Changed `circle-stroke-opacity` from `0.45` to `0` - completely hides the halo rings
- **GlobeView.tsx** (line ~617): Same fix applied to globe view `g-entity-halo` layer
- Added comments: "DISABLED - was causing confusing shadow circles"

**Result**: No more circular shadows following entities. Ships and aircraft now show only as directional arrows with trails.

---

### 2. ✅ Ship Color White Instead of Blue/Teal
**Problem**: Ships appeared as white arrows on map, but legend showed teal (#14ba8c).

**Root Cause**: Ship arrow image data was created with RGB(255, 255, 255) - pure white.

**Fix Applied**:
- **MapView.tsx** (line ~929): Changed `makeArrowImageData(255, 255, 255)` to `makeArrowImageData(20, 186, 140)` - teal color matching legend
- **GlobeView.tsx** (line ~596): Same fix for globe view
- Updated comments: "Teal ship arrows match legend color"

**Result**: Ship arrows now display in teal (#14ba8c), matching the legend and LayerPanel color.

---

### 3. ✅ Aircraft Dots vs Ship Arrows (Better Representation)
**Problem**: Aircraft icons were too small and not distinct enough from ship icons.

**Fix Applied**:
- **MapView.tsx** (lines ~960-980):
  - Ship `icon-size`: increased from `1.1` to `1.2` (9% larger)
  - Aircraft `icon-size`: increased from `1.1` to `1.3` (18% larger)
- **GlobeView.tsx** (lines ~630-650): Same icon size increases
- Both ships and aircraft use directional arrows (not dots) rotated by heading

**Result**: Aircraft are now more prominent and easier to distinguish. Both entity types use clear directional arrows.

---

### 4. ✅ News Flashing (Events Disappearing Immediately)
**Problem**: Events (intel events, GDELT events, signals) would appear briefly and then disappear as playback time advanced. Analysts couldn't review news that had just occurred.

**Root Cause**: Event filtering logic showed events only if `eventTime <= playbackTime + 120s` (2 minute grace). After playback passed an event, it immediately disappeared.

**Fix Applied**:
- **App.tsx** (lines ~398-432):
  - Added constant: `const TWO_DAYS_SEC = 172800;` (2 days = 48 hours in seconds)
  - Changed filter logic from:
    ```ts
    return eventTime <= (playbackTime + 120);
    ```
    To:
    ```ts
    return playbackTime >= eventTime && playbackTime <= (eventTime + TWO_DAYS_SEC);
    ```
  - Applied to `coreEventData`, `gdeltData`, and `signalData` filters
  - Updated comment: "Time-filter events: show events for 2 days after they occur (analyst requirement)"

**Result**: Events now persist on the map for 2 full days after their occurrence, giving analysts sufficient time to review and correlate intelligence.

---

### 5. ✅ Legend Hidden by Bottom Bar
**Problem**: Map legend was positioned at `bottom: 58px`, which caused it to be hidden behind the ChokeMetricsBar when it appeared.

**Fix Applied**:
- **App.css** (lines ~527-541):
  - Changed `bottom` from `58px` to `80px` (+22px clearance)
  - Changed `max-height` from `calc(100% - 90px)` to `calc(100% - 130px)` (accounts for higher bottom position)
  - Added comments: "Increased from 58px to 80px to stay above chokepoint metrics bar" and "Adjusted to account for higher bottom position"

**Result**: Legend now stays visible above the bottom metrics bar at all times.

---

### 6. ⚠️ PARTIAL: Draggable Info Popups
**Problem**: Floating popups cannot be moved by mouse, blocking view of map objects underneath.

**Solution Provided**:
Created reusable `useDraggable()` hook in `frontend/src/hooks/useDraggable.ts`:
- Provides `containerProps` and `handleProps` for easy integration
- Handles mousedown, mousemove, mouseup events with proper cleanup
- Uses CSS `transform: translate()` for smooth dragging
- Cursor changes to 'grab'/'grabbing' on drag handle
- Prevents dragging when clicking buttons/inputs/links

**Usage Example**:
```tsx
import { useDraggable } from '../../hooks/useDraggable';

function MyPanel() {
  const { containerProps, handleProps } = useDraggable();
  
  return (
    <div className="my-panel" {...containerProps}>
      <div className="panel-header" {...handleProps}>
        Drag Me
      </div>
      <div className="panel-content">
        Panel content here
      </div>
    </div>
  );
}
```

**To Apply to MapLibre Popups**:
MapLibre's native popups (`maplibregl.Popup`) don't support dragging by default. Options:
1. Replace popups with custom React modals using the `useDraggable` hook
2. Add drag handlers to popup DOM elements after creation (complex, not recommended)
3. Keep popups as-is but add a "minimize" or "close" button for better UX

**Status**: Hook created and ready, but not yet applied to any components. Requires additional work to integrate with existing panels/modals.

---

## Testing Recommendations

1. **Restart Services**:
   ```powershell
   # Backend
   uvicorn app.main:app --reload
   
   # Frontend
   cd frontend
   npm run dev
   ```

2. **Hard Refresh Browser**: Press `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac) to clear browser cache

3. **Verify in Demo Mode**: Navigate to `http://localhost:5173?demoMode=true` for all optimizations

4. **Check for Issues**:
   - ✅ No circular shadows around ships/aircraft
   - ✅ Ship arrows are teal (#14ba8c), aircraft are yellow
   - ✅ Both entity types clearly visible and properly sized
   - ✅ Events persist for 2 days during playback
   - ✅ Legend stays above bottom metrics bar
   - ⏸️ Draggable popups require additional integration

---

## Files Modified

| File | Lines Changed | Purpose |
|------|--------------|---------|
| `frontend/src/components/Map/MapView.tsx` | ~929, ~948, ~960-980 | Ship color, halo removal, icon sizes |
| `frontend/src/components/GlobeView/GlobeView.tsx` | ~596, ~617, ~630-650 | Same fixes for globe view |
| `frontend/src/App.tsx` | ~398-432 | 2-day event persistence |
| `frontend/src/App.css` | ~527-541 | Legend positioning |
| `frontend/src/hooks/useDraggable.ts` | New file (90 lines) | Draggable hook utility |

---

## Next Steps (Optional)

1. **Apply Draggable to Key Panels**:
   - IntelBriefingPanel
   - EventDetailModal (if exists)
   - Custom map info windows

2. **Performance Testing**:
   - Verify 60 FPS maintained with all fixes
   - Check memory usage during 2-day event persistence
   - Test on lower-end hardware

3. **Video Recording**:
   - Run `.\scripts\New-ManagementDemoVideo-Simple.ps1 -SkipVoice` to generate new demo video
   - Verify all issues resolved in recorded output
   - Check video quality, clarity, and smoothness

---

**All critical issues (1-5) have been resolved. Issue 6 (draggable popups) has a ready-to-use solution but requires integration work.**
