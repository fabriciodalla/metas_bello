import { Mail } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import belloLogoWhite from "../assets/bello-logo-white.png";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api.post("/auth/password-reset/", { email });
      setSent(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível processar o pedido.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-brand-panel">
        <div className="login-brand-content">
          <div className="login-brand-mark-wrap">
            <img src={belloLogoWhite} alt="Bello Alimentos" />
            <span className="login-brand-name">Vendas</span>
          </div>
        </div>
      </div>
      <div className="login-form-panel">
        <div className="login-card">
          <h2>Esqueci a senha / primeiro acesso</h2>
          {sent ? (
            <>
              <Alert variant="success">
                Se o e-mail existir, você vai receber um link para definir a senha.
              </Alert>
              <Link to="/login">Voltar para o login</Link>
            </>
          ) : (
            <form className="login-form" onSubmit={handleSubmit}>
              <div className="field">
                <label className="field-label field-label-caps" htmlFor="email">
                  E-mail
                </label>
                <div className="field-input-icon">
                  <Mail size={16} />
                  <input
                    id="email"
                    type="email"
                    placeholder="seu@email.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoFocus
                  />
                </div>
              </div>
              {error && <Alert variant="danger">{error}</Alert>}
              <Button type="submit" disabled={submitting}>
                {submitting ? "Enviando…" : "Enviar link"}
              </Button>
              <div className="login-links-row">
                <Link to="/login">Voltar para o login</Link>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
