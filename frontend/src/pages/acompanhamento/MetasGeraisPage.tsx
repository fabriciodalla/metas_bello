import { Target } from "lucide-react";
import { EmptyState } from "../../components/ui/EmptyState";

export function MetasGeraisPage() {
  return (
    <section>
      <EmptyState icon={<Target size={28} strokeWidth={1.5} />}>Reservado para uso futuro.</EmptyState>
    </section>
  );
}
