import { useState } from "react";
import { exportsApi } from "../../api/client";

interface Props {
  aoiId: string | null;
  startTime: string;
  endTime: string;
}

export function ExportPanel({ aoiId, startTime, endTime }: Props) {
  const [format, setFormat] = useState<"csv" | "geojson" | "parquet">("csv");
  const [status, setStatus] = useState<string>("");
  const [downloading, setDownloading] = useState(false);

  async function handleExport() {
    setDownloading(true);
    setStatus("Submitting…");
    try {
      const job = await exportsApi.create({
        search: {
          ...(aoiId ? { aoi_id: aoiId } : {}),
          start_time: startTime,
          end_time: endTime,
        },
        format,
      });
      // Export is synchronous — job is always completed when create() returns.
      if (job.status === "completed") {
        setStatus(`Done — ${job.event_count ?? "?"} rows`);
        if (job.download_url) window.open(job.download_url, "_blank");
      } else if (job.status === "failed") {
        setStatus(`Export failed${job.error ? `: ${job.error}` : ""}`);
      } else {
        setStatus("Unexpected job state: " + job.status);
      }
    } catch (e) {
      setStatus(`Error: ${e}`);
    } finally { setDownloading(false); }
  }

  return (
    <div className="panel" data-testid="export-panel">
      <h3 className="panel-title">Export</h3>
      <div className="export-controls">
        <select className="input-sm" value={format} onChange={e => setFormat(e.target.value as "csv" | "geojson" | "parquet")}>
          <option value="csv">CSV</option>
          <option value="geojson">GeoJSON</option>
          <option value="parquet">Parquet</option>
        </select>
        <button className="btn btn-primary btn-sm" onClick={handleExport} disabled={downloading} data-testid="export-btn">
          {downloading ? "Exporting…" : "Export"}
        </button>
      </div>
      {status && <p className="muted">{status}</p>}
    </div>
  );
}