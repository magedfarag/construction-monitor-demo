import { useState } from "react";
import { useAois, useCreateAoi, useDeleteAoi } from "../../hooks/useAois";
import type { Aoi } from "../../api/types";

interface Props {
  selectedAoiId: string | null;
  onSelect: (id: string | null) => void;
  drawMode: "none" | "polygon" | "bbox";
  onDrawModeChange: (mode: "none" | "polygon" | "bbox") => void;
  pendingGeometry: GeoJSON.Geometry | null;
  onClearPendingGeometry: () => void;
  viewMode?: "2d" | "3d";
  onSwitchTo2D?: () => void;
}

export function AoiPanel({ selectedAoiId, onSelect, drawMode, onDrawModeChange, pendingGeometry, onClearPendingGeometry, viewMode = "2d", onSwitchTo2D }: Props) {
  const { data: aois = [], isLoading } = useAois();
  const createAoi = useCreateAoi();
  const deleteAoi = useDeleteAoi();
  const [newName, setNewName] = useState("");

  function handleSave() {
    if (!pendingGeometry || !newName.trim()) return;
    createAoi.mutate({ name: newName.trim(), geometry: pendingGeometry as never }, {
      onSuccess: () => { setNewName(""); onClearPendingGeometry(); onDrawModeChange("none"); }
    });
  }

  return (
    <div className="panel" data-testid="aoi-panel">
      <h3 className="panel-title">Areas of Interest</h3>
      <div className="draw-tools">
        <button
          className={`btn btn-sm ${drawMode === "bbox" ? "btn-active" : ""}`}
          onClick={() => onDrawModeChange(drawMode === "bbox" ? "none" : "bbox")}
          title="Draw bounding box (click 2 corners)"
          disabled={viewMode === "3d"}
        >⬜ BBox</button>
        <button
          className={`btn btn-sm ${drawMode === "polygon" ? "btn-active" : ""}`}
          onClick={() => onDrawModeChange(drawMode === "polygon" ? "none" : "polygon")}
          title="Draw polygon (double-click to close)"
          disabled={viewMode === "3d"}
        >⬡ Polygon</button>
      </div>
      {viewMode === "3d" && (
        <p className="muted hint" style={{ marginBottom: 8 }}>
          Drawing requires 2D mode.{" "}
          <button className="btn btn-xs btn-primary" onClick={onSwitchTo2D} style={{ marginLeft: 4 }}>
            Switch to 2D
          </button>
        </p>
      )}
      {pendingGeometry && (
        <div className="save-aoi">
          <input
            type="text"
            placeholder="AOI name..."
            value={newName}
            onChange={e => setNewName(e.target.value)}
            className="input-sm"
            data-testid="aoi-name-input"
          />
          <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={!newName.trim()}>
            Save AOI
          </button>
          <button className="btn btn-sm" onClick={() => { onClearPendingGeometry(); onDrawModeChange("none"); }}>
            Cancel
          </button>
        </div>
      )}
      {isLoading ? <p className="muted">Loading…</p> : (
        <ul className="aoi-list">
          {aois.map((aoi: Aoi) => (
            <li
              key={aoi.id}
              className={`aoi-item ${aoi.id === selectedAoiId ? "aoi-item--selected" : ""}`}
              onClick={() => onSelect(aoi.id === selectedAoiId ? null : aoi.id)}
              data-testid="aoi-item"
            >
              <span className="aoi-name">{aoi.name}</span>
              <button
                className="btn btn-xs btn-danger"
                onClick={e => { e.stopPropagation(); deleteAoi.mutate(aoi.id); }}
                title="Delete AOI"
              >✕</button>
            </li>
          ))}
        </ul>
      )}
      {aois.length === 0 && !isLoading && (
        <p className="muted hint">Draw a BBox or Polygon on the map to define your area</p>
      )}
    </div>
  );
}