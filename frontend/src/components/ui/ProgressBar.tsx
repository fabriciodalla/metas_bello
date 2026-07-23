type Variant = "success" | "warning" | "danger" | "neutral";

interface Props {
  percent: number;
  variant?: Variant;
  size?: "sm" | "md";
  label?: string;
}

export function ProgressBar({ percent, variant = "success", size = "md", label }: Props) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div
      className={`progress-bar progress-bar-${size}`}
      role="progressbar"
      aria-valuenow={Math.round(percent)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div className={`progress-bar-fill progress-bar-${variant}`} style={{ width: `${clamped}%` }} />
    </div>
  );
}
