import { useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { Alert } from "../components/ui/Alert";
import { Button } from "../components/ui/Button";
import { PasswordInput } from "../components/ui/PasswordInput";
import belloLogoWhite from "../assets/bello-logo-white.png";

export function ResetPasswordPage() {
  const { uid, token } = useParams<{ uid: string; token: string }>();
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError("As senhas não coincidem.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/auth/password-reset-confirm/", { uid, token, new_password: newPassword });
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível definir a senha.");
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
          <h2>Definir nova senha</h2>
          {done ? (
            <>
              <Alert variant="success">Senha definida com sucesso.</Alert>
              <Link to="/login">Ir para o login</Link>
            </>
          ) : (
            <form className="login-form" onSubmit={handleSubmit}>
              <div className="field">
                <label className="field-label field-label-caps" htmlFor="new-password">
                  Nova senha
                </label>
                <PasswordInput
                  id="new-password"
                  value={newPassword}
                  onChange={setNewPassword}
                  autoComplete="new-password"
                  autoFocus
                />
              </div>
              <div className="field">
                <label className="field-label field-label-caps" htmlFor="confirm-password">
                  Confirmar senha
                </label>
                <PasswordInput
                  id="confirm-password"
                  value={confirmPassword}
                  onChange={setConfirmPassword}
                  autoComplete="new-password"
                />
              </div>
              {error && <Alert variant="danger">{error}</Alert>}
              <Button type="submit" disabled={submitting}>
                {submitting ? "Salvando…" : "Definir senha"}
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
