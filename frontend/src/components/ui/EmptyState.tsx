import { Inbox } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({ children, icon }: { children: ReactNode; icon?: ReactNode }) {
  return (
    <div className="empty-state">
      {icon ?? <Inbox size={28} strokeWidth={1.5} />}
      <p style={{ margin: 0 }}>{children}</p>
    </div>
  );
}
