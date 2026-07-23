import { X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { api, ApiError } from "../../api/client";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { PasswordInput } from "./PasswordInput";

export function ChangePasswordModal({ onClose }: { onClose: () => void }) {
  const [currentPassword, setCurrentPassword] = useState("");
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
      await api.post("/auth/password-change/", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível mudar a senha.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card" onClick={(event) => event.stopPropagation()}>
        <div className="modal-header">
          <h3>Mudar senha</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Fechar">
            <X size={18} />
          </button>
        </div>

        {done ? (
          <>
            <Alert variant="success">Senha alterada com sucesso.</Alert>
            <Button type="button" onClick={onClose}>
              Fechar
            </Button>
          </>
        ) : (
          <form className="login-form" onSubmit={handleSubmit}>
            <div className="field">
              <label className="field-label field-label-caps" htmlFor="current-password">
                Senha atual
              </label>
              <PasswordInput
                id="current-password"
                value={currentPassword}
                onChange={setCurrentPassword}
                autoComplete="current-password"
                autoFocus
              />
            </div>
            <div className="field">
              <label className="field-label field-label-caps" htmlFor="new-password">
                Nova senha
              </label>
              <PasswordInput
                id="new-password"
                value={newPassword}
                onChange={setNewPassword}
                autoComplete="new-password"
              />
            </div>
            <div className="field">
              <label className="field-label field-label-caps" htmlFor="confirm-new-password">
                Confirmar nova senha
              </label>
              <PasswordInput
                id="confirm-new-password"
                value={confirmPassword}
                onChange={setConfirmPassword}
                autoComplete="new-password"
              />
            </div>
            {error && <Alert variant="danger">{error}</Alert>}
            <Button type="submit" disabled={submitting}>
              {submitting ? "Salvando…" : "Salvar nova senha"}
            </Button>
          </form>
        )}
      </div>
    </div>
  );
}
