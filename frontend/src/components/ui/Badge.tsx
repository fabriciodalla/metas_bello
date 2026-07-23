import type { ReactNode } from "react";

type Variant = "success" | "danger" | "warning" | "neutral" | "accent";

export function Badge({ variant = "neutral", children }: { variant?: Variant; children: ReactNode }) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}
