import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { ProgressBar } from "./ProgressBar";

interface Props {
  icon: LucideIcon;
  label: string;
  value: ReactNode;
  caption?: ReactNode;
  accent?: "primary" | "warning";
  progress?: { percent: number; variant?: "success" | "warning" | "danger" };
  progressLabel?: ReactNode;
  tooltip?: string;
}

export function SummaryCard({
  icon: Icon,
  label,
  value,
  caption,
  accent = "primary",
  progress,
  progressLabel,
  tooltip,
}: Props) {
  return (
    <div className={`summary-card summary-card-${accent}`}>
      <div className="summary-card-top">
        <div className={`summary-card-icon summary-card-icon-${accent}`}>
          <Icon size={22} strokeWidth={2} />
        </div>
        <div className="summary-card-body">
          <span className="summary-card-label" title={tooltip}>
            {label}
          </span>
          <span className="summary-card-value">{value}</span>
        </div>
      </div>
      {progress && (
        <div className="summary-card-progress">
          <ProgressBar percent={progress.percent} variant={progress.variant ?? "success"} />
          {progressLabel && <span className="summary-card-progress-label">{progressLabel}</span>}
        </div>
      )}
      {caption && !progress && <span className="summary-card-caption">{caption}</span>}
    </div>
  );
}
