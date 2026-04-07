// useTimelineSync — Track E cross-layer synchronization hook.
// Provides a shared time window and per-layer filter helpers so that
// GlobeView, MapView, and all panel components stay temporally consistent.

import { useState, useCallback, useMemo } from 'react';
import type { GpsJammingEvent, StrikeEvent, AirspaceRestriction } from '../../types/operationalLayers';

// ── Public types ──────────────────────────────────────────────────────────────

export interface TimelineState {
  currentTime: Date;
  windowStart: Date;
  windowEnd: Date;
}

const WINDOW_MS = 24 * 60 * 60 * 1000; // 24 h

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useTimelineSync(): {
  timelineState: TimelineState;
  setCurrentTime: (t: Date) => void;
  currentTimeUnix: number;
  isEventVisible: (eventTime: string) => boolean;
  filteredJammingEvents: (events: GpsJammingEvent[]) => GpsJammingEvent[];
  filteredStrikes: (events: StrikeEvent[]) => StrikeEvent[];
  filteredAirspaceRestrictions: (restrictions: AirspaceRestriction[]) => AirspaceRestriction[];
} {
  const [currentTime, setCurrentTimeState] = useState<Date>(() => new Date());

  // Memoize window calculations to prevent infinite re-renders
  const windowEnd = useMemo(() => currentTime, [currentTime]);
  const windowStart = useMemo(() => new Date(currentTime.getTime() - WINDOW_MS), [currentTime]);
  const windowStartMs = useMemo(() => windowStart.getTime(), [windowStart]);
  const windowEndMs = useMemo(() => windowEnd.getTime(), [windowEnd]);

  const timelineState: TimelineState = { currentTime, windowStart, windowEnd };

  const currentTimeUnix = currentTime.getTime() / 1000;

  const setCurrentTime = useCallback((t: Date) => {
    setCurrentTimeState(t);
  }, []);

  const isEventVisible = useCallback(
    (eventTime: string): boolean => {
      const t = new Date(eventTime).getTime();
      return t >= windowStartMs && t <= windowEndMs;
    },
    [windowStartMs, windowEndMs],
  );

  const filteredJammingEvents = useCallback(
    (events: GpsJammingEvent[]): GpsJammingEvent[] =>
      events.filter(e => isEventVisible(e.detected_at)),
    [isEventVisible],
  );

  const filteredStrikes = useCallback(
    (events: StrikeEvent[]): StrikeEvent[] =>
      events.filter(e => isEventVisible(e.occurred_at)),
    [isEventVisible],
  );

  const filteredAirspaceRestrictions = useCallback(
    (restrictions: AirspaceRestriction[]): AirspaceRestriction[] =>
      restrictions.filter(r => {
        const from = new Date(r.valid_from).getTime();
        const to = r.valid_to ? new Date(r.valid_to).getTime() : Infinity;
        // Include restriction if its validity window overlaps with [windowStart, windowEnd]
        return from <= windowEndMs && to >= windowStartMs;
      }),
    [windowStartMs, windowEndMs],
  );

  return {
    timelineState,
    setCurrentTime,
    currentTimeUnix,
    isEventVisible,
    filteredJammingEvents,
    filteredStrikes,
    filteredAirspaceRestrictions,
  };
}
