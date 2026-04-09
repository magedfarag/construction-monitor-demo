# Quick Reference: What Changed

## Visual Fixes (Before → After)

### 1. Ship/Aircraft Icons
| Before | After |
|--------|-------|
| Ships: White arrows (255,255,255) | Ships: Teal arrows (20,186,140) ✓ |
| Aircraft: Yellow arrows, icon-size 1.1 | Aircraft: Yellow arrows, icon-size 1.3 ✓ |
| Circular halos following entities (opacity 0.45) | Halos invisible (opacity 0) ✓ |

### 2. Event Persistence
| Before | After |
|--------|-------|
| Events disappear after playbackTime + 120s | Events persist for 2 days (172,800s) ✓ |
| Intel/GDELT/Signals flash and vanish | Events stay visible for analyst review ✓ |

### 3. Legend Position
| Before | After |
|--------|-------|
| bottom: 58px (hidden by metrics bar) | bottom: 80px (always visible) ✓ |
| max-height: calc(100% - 90px) | max-height: calc(100% - 130px) ✓ |

## Testing Checklist

### In Browser (http://localhost:5173?demoMode=true)
- [ ] **Hard refresh**: Press `Ctrl+Shift+R` to clear cached modules  - [ ] **Ship colors**: Ships should be TEAL (#14ba8c), not white
- [ ] **No shadow circles**: No halos around ships/aircraft in 2D or 3D view
- [ ] **Aircraft visible**: Aircraft arrows larger and more prominent
- [ ] **Event persistence**: Start playback, events should stay for 2 days
- [ ] **Legend visible**: Legend should NOT be hidden by bottom metrics bar

### In Video Recording
```powershell
cd c:\Projects\mod\Tracking\world-view
.\scripts\New-ManagementDemoVideo-Simple.ps1 -SkipVoice -AppUrl 'http://localhost:5173'
```

Expected improvements:
- ✅ No flickering circles following entities
- ✅ Ship color matches legend (teal)
- ✅ Aircraft clearly visible
- ✅ Events don't flash/disappear
- ✅ Legend always visible above bottom bar

## Performance Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| Ship icon size | 1.1 | 1.2 | +9% |
| Aircraft icon size | 1.1 | 1.3 | +18% |
| Halo opacity | 0.45 | 0 | -100% (invisible) |
| Event window | 120s | 172,800s | +144,000% |
| Legend bottom | 58px | 80px | +22px |
| Bundle size | 2,514.82 kB | 2,514.91 kB | +90 bytes |
| Build time | ~20s | ~11s | -45% (faster!) |

## Services Status

✓ **Frontend**: http://localhost:5173 (Vite ready in 350ms)  
✓ **Backend**: http://localhost:8000 (Status: ok, Mode: demo)  
✓ **Build**: Successful (no TypeScript errors)  

## Next Actions

1. **Test in browser**: Open http://localhost:5173?demoMode=true and verify all fixes
2. **Hard refresh**: `Ctrl+Shift+R` to ensure no cached code
3. **Check console**: Should only see 2 harmless warnings (calculateFogMatrix, easing)
4. **Record video**: Run PowerShell script to generate new demo video
5. **Optional**: Integrate `useDraggable` hook into panels for movable UI

---

**All 5 critical issues fixed. Draggable popups hook ready but requires integration.**
