export function Spinner({ label = "Carregando…" }: { label?: string }) {
  return (
    <div className="loading-row">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  );
}
