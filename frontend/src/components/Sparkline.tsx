import type { MonthlyPoint } from "../api/types";

export function Sparkline({ history }: { history: MonthlyPoint[] }) {
  const values = history.map((point) => point.quantity_kg);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = max - min || 1;
  const width = 180;
  const height = 40;
  const step = width / Math.max(values.length - 1, 1);

  const points = values
    .map((value, i) => {
      const x = i * step;
      const y = height - ((value - min) / range) * height;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} className="suggestion-sparkline" role="img" aria-label="Histórico de 12 meses">
      <polyline points={points} fill="none" stroke="var(--color-primary)" strokeWidth={2} />
    </svg>
  );
}
