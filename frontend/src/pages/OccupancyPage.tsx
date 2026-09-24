import { useEffect, useState } from "react";
import { api } from "../api/client";
type Rail = { id: number; label: string; length_cm: number; buffer_cm: number };
type Occ = { rail_id: number; label: string; length_cm: number; buffer_cm: number; segments: { ticket_code: string; garment_name: string; start_cm: number; end_cm: number }[] };
function measuredGap(segs: { start_cm: number; end_cm: number }[]) {
  const ordered = [...segs].sort((a, b) => a.start_cm - b.start_cm);
  let gap = 0;
  for (let i = 1; i < ordered.length; i++) {
    const d = ordered[i].start_cm - ordered[i - 1].end_cm;
    if (d > gap) gap = d;
  }
  return Math.round(gap * 10) / 10;
}

export default function OccupancyPage() {
  const [rails, setRails] = useState<Rail[]>([]);
  const [maps, setMaps] = useState<Occ[]>([]);
  useEffect(() => {
    api<Rail[]>("/rails").then(async rs => {
      setRails(rs);
      const all = await Promise.all(rs.map(r => api<Occ>(`/occupancy/${r.id}`)));
      setMaps(all);
    });
  }, []);
  return (<>
    <h2>占位图（横向尺线）</h2>
    {maps.map(m => (
      <div className="ruler-wrap" key={m.rail_id}>
        <div className="ruler-label">
          <span>{m.label}{m.buffer_cm > 0 && <span className="buffer-badge">缓冲 {m.buffer_cm}cm</span>}
            {m.segments.length > 1 && <span className="buffer-badge">量得间距 {measuredGap(m.segments)}cm</span>}
          </span>
          <span className="mono">0 — {m.length_cm} cm</span>
        </div>
        <div className="ruler">
          {m.segments.map((s, i) => (
            <div key={i} className="seg" style={{ left: `${(s.start_cm / m.length_cm) * 100}%`, width: `${((s.end_cm - s.start_cm) / m.length_cm) * 100}%` }}
              title={`${s.ticket_code} ${s.start_cm}-${s.end_cm}cm`}>
              {s.garment_name}
            </div>
          ))}
        </div>
      </div>
    ))}
    {!rails.length && <p>暂无挂杆</p>}
  </>);
}
