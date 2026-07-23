import { RefreshCw } from "lucide-react";
import { useState } from "react";
import { api, ApiError } from "../../api/client";
import type { SyncResult } from "../../api/types";
import { Button } from "../../components/ui/Button";
import { Alert } from "../../components/ui/Alert";
import { Card } from "../../components/ui/Card";

export function PreProcessamentoPage() {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<SyncResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSync() {
    setSyncing(true);
    setError(null);
    setResult(null);
    try {
      const data = await api.post<SyncResult>("/sales-history/sync/");
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Falha ao sincronizar os dados.");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <section>
      <Card>
        <p>
          Sincroniza o acumulado de vendas e a carteira de clientes do ERP (últimos 12 meses) e
          reconstrói a base usada na sugestão automática de metas. Rode antes de abrir a
          distribuição do ciclo.
        </p>
        <Button onClick={() => void handleSync()} disabled={syncing}>
          <RefreshCw size={16} />
          {syncing ? "Sincronizando…" : "Sincronizar dados agora"}
        </Button>
        {error && (
          <div style={{ marginTop: "var(--space-4)" }}>
            <Alert variant="danger" role="alert">
              {error}
            </Alert>
          </div>
        )}
        {result && (
          <div style={{ marginTop: "var(--space-4)" }}>
            <Alert variant="success">
              Sincronizado desde {result.synced_since}: {result.accumulated_count} linha(s) de
              acumulado, {result.portfolio_count} cliente(s) na carteira, {result.baseline_count}{" "}
              linha(s) na base de distribuição.
            </Alert>
          </div>
        )}
      </Card>

      <h3>Configurações adicionais</h3>
      <p>
        <em>
          Em breve. Os mapeamentos de histórico de vendas (vendedor/subgrupo externos) continuam no{" "}
          <a href="/admin/" target="_blank" rel="noreferrer">
            Django Admin
          </a>{" "}
          por enquanto.
        </em>
      </p>
    </section>
  );
}
