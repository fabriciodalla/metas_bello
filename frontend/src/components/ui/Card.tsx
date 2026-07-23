import type { ReactNode } from "react";

interface Props {
  title?: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function Card({ title, subtitle, actions, children, className }: Props) {
  return (
    <div className={["card", className].filter(Boolean).join(" ")}>
      {(title || actions) && (
        <div className="card-header">
          <div className="card-title-group">
            {title && <h3>{title}</h3>}
            {subtitle && <span className="card-subtitle">{subtitle}</span>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </div>
  );
}
