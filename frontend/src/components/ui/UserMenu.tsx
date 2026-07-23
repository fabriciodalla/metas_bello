import { ChevronDown, KeyRound, LogOut } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import type { User } from "../../api/types";
import { LEVEL_LABELS, type Level } from "../../pages/admin/constants";
import { ChangePasswordModal } from "./ChangePasswordModal";

function initials(username: string) {
  return username.slice(0, 2).toUpperCase();
}

function firstName(username: string) {
  const first = username.trim().split(/[.\s]+/)[0] ?? "";
  return first.charAt(0).toUpperCase() + first.slice(1).toLowerCase();
}

export function UserMenu({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const roleLabel = user.is_admin
    ? "Administrador"
    : (LEVEL_LABELS[user.hierarchy_nodes[0]?.level as Level] ?? "Usuário");

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  return (
    <div className="user-menu" ref={menuRef}>
      <button type="button" className="user-menu-trigger" onClick={() => setOpen((o) => !o)}>
        <span className="avatar">{initials(user.username)}</span>
        <span className="user-menu-info">
          <span className="user-menu-name">{firstName(user.username)}</span>
          <span className="user-menu-role">{roleLabel}</span>
        </span>
        <ChevronDown size={16} />
      </button>

      {open && (
        <div className="user-menu-dropdown">
          <button
            type="button"
            className="user-menu-item"
            onClick={() => {
              setShowPasswordModal(true);
              setOpen(false);
            }}
          >
            <KeyRound size={16} />
            <span>Mudar senha</span>
          </button>
          <button type="button" className="user-menu-item" onClick={() => void onLogout()}>
            <LogOut size={16} />
            <span>Sair</span>
          </button>
        </div>
      )}

      {showPasswordModal && <ChangePasswordModal onClose={() => setShowPasswordModal(false)} />}
    </div>
  );
}
