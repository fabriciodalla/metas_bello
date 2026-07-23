import { Eye, EyeOff, Lock } from "lucide-react";
import { useState } from "react";

interface Props {
  id: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  autoFocus?: boolean;
}

export function PasswordInput({ id, value, onChange, autoComplete, autoFocus }: Props) {
  const [visible, setVisible] = useState(false);

  return (
    <div className="field-input-icon">
      <Lock size={16} />
      <input
        id={id}
        type={visible ? "text" : "password"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete}
        autoFocus={autoFocus}
      />
      <button
        type="button"
        className="field-input-toggle"
        onClick={() => setVisible((v) => !v)}
        aria-label={visible ? "Ocultar senha" : "Mostrar senha"}
      >
        {visible ? <EyeOff size={16} /> : <Eye size={16} />}
      </button>
    </div>
  );
}
