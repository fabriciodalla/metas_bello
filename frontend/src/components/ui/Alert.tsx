import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import type { ReactNode } from "react";

type Variant = "success" | "danger" | "warning" | "info";

const ICONS: Record<Variant, ReactNode> = {
  success: <CheckCircle2 size={16} />,
  danger: <XCircle size={16} />,
  warning: <AlertTriangle size={16} />,
  info: <Info size={16} />,
};

export function Alert({
  variant = "info",
  children,
  role,
}: {
  variant?: Variant;
  children: ReactNode;
  role?: string;
}) {
  return (
    <div className={`alert alert-${variant}`} role={role}>
      {ICONS[variant]}
      <span>{children}</span>
    </div>
  );
}
