import type { Cycle } from "../../api/types";

export function CycleSelect({
  cycles,
  value,
  onChange,
}: {
  cycles: Cycle[];
  value: number | null;
  onChange: (cycleId: number) => void;
}) {
  return (
    <div className="field-inline">
      <label className="field-label" htmlFor="cycle-select">
        Ciclo
      </label>
      <select id="cycle-select" value={value ?? ""} onChange={(e) => onChange(Number(e.target.value))}>
        {cycles.map((cycle) => (
          <option key={cycle.id} value={cycle.id}>
            {String(cycle.mes).padStart(2, "0")}/{cycle.ano} ({cycle.status})
          </option>
        ))}
      </select>
    </div>
  );
}
