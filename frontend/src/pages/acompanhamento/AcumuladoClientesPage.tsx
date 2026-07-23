import { Users } from "lucide-react";
import { EmptyState } from "../../components/ui/EmptyState";

export function AcumuladoClientesPage() {
  return (
    <section>
      <EmptyState icon={<Users size={28} strokeWidth={1.5} />}>Reservado para uso futuro.</EmptyState>
    </section>
  );
}
