import { Mail, User } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { Button } from "../components/ui/Button";
import { Alert } from "../components/ui/Alert";
import { PasswordInput } from "../components/ui/PasswordInput";
import belloLogoWhite from "../assets/bello-logo-white.png";
import vendasFaturamentoIcon from "../assets/login-vendas-faturamento.png";
import metasDesempenhoIcon from "../assets/login-metas-desempenho.png";
import gestaoCarteiraClientesIcon from "../assets/login-gestao-carteira-clientes.png";

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function LoginPage() {
  const { user, login } = useAuth();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    const fallback = user.is_admin ? "/admin/visao-geral" : "/distribuicao";
    const from = (location.state as { from?: string } | null)?.from ?? fallback;
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    if (!email.trim() || !EMAIL_PATTERN.test(email)) {
      setEmailError("Informe um e-mail corporativo válido.");
      return;
    }
    setEmailError(null);

    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível conectar. Tente novamente.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-page">
      <div className="login-brand-panel">
        <div className="login-brand-decor" aria-hidden="true" />
        <div className="login-brand-content">
          <div className="login-brand-mark-wrap">
            <img src={belloLogoWhite} alt="Bello Alimentos" />
            <span className="login-brand-name">Vendas</span>
          </div>

          <h1 className="login-brand-title">
            Gestão comercial
            <br />
            em um <span>só lugar</span>
          </h1>

          <p className="login-brand-subtitle login-brand-subtitle-full">
            Acompanhe vendas, metas, clientes e desempenho da equipe de forma simples e simplificada.
          </p>
          <p className="login-brand-subtitle login-brand-subtitle-short">
            Acompanhe vendas, metas, clientes e desempenho da equipe de forma simples e simplificada.
          </p>

          <div className="login-brand-stats">
            <div className="login-brand-stat">
              <div className="login-brand-stat-icon" aria-hidden="true">
                <img src={vendasFaturamentoIcon} alt="" />
              </div>
              <span>
                Vendas e<br /> faturamento
              </span>
            </div>
            <div className="login-brand-stat">
              <div className="login-brand-stat-icon" aria-hidden="true">
                <img src={metasDesempenhoIcon} alt="" />
              </div>
              <span>
                Metas e<br /> desempenho
              </span>
            </div>
            <div className="login-brand-stat">
              <div className="login-brand-stat-icon" aria-hidden="true">
                <img src={gestaoCarteiraClientesIcon} alt="" />
              </div>
              <span>
                Gestão da
                <br /> carteira de clientes
              </span>
            </div>
          </div>
        </div>

        <div className="login-brand-footer">
          <strong>Bello Alimentos.</strong>
          <span>Parceria que move resultados.</span>
        </div>
      </div>

      <div className="login-form-panel">
        <div className="login-card">
          <div className="login-card-icon">
            <User size={36} />
          </div>
          <h2 className="login-card-title">Bem-vindo ao Bello Vendas</h2>
          <p className="login-card-subtitle">Acesse sua conta para continuar.</p>

          <form className="login-form login-form-standalone" onSubmit={handleSubmit} noValidate>
            <div className="field">
              <label className="field-label" htmlFor="email">
                E-mail corporativo
              </label>
              <div className="field-input-icon">
                <Mail size={16} />
                <input
                  id="email"
                  type="email"
                  placeholder="nome@belloalimentos.com.br"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (emailError) setEmailError(null);
                  }}
                  autoFocus
                  aria-invalid={emailError ? true : undefined}
                />
              </div>
              <p className="field-error">{emailError ?? ""}</p>
            </div>

            <div className="field">
              <label className="field-label" htmlFor="password">
                Senha
              </label>
              <PasswordInput id="password" value={password} onChange={setPassword} autoComplete="current-password" />
            </div>

            <div className="login-options-row">
              <label className="field-check login-remember">
                <input type="checkbox" defaultChecked={false} />
                Lembrar meu acesso
              </label>
              <Link to="/esqueci-senha" className="login-link-accent">
                Esqueci minha senha
              </Link>
            </div>

            {error && <Alert variant="danger">{error}</Alert>}

            <Button type="submit" disabled={submitting}>
              {submitting ? (
                <>
                  <span className="spinner spinner-inverse" />
                  Entrando...
                </>
              ) : (
                "Entrar no sistema"
              )}
            </Button>
          </form>

          <div className="login-card-divider" />
          <p className="login-card-signup">
            Primeiro acesso?{" "}
            <Link to="/esqueci-senha" className="login-link-accent">
              Ative sua conta
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
