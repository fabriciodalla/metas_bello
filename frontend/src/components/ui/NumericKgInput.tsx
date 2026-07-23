import type { FocusEvent } from "react";

interface Props {
  value: number | "";
  onChange: (value: number | "") => void;
  id?: string;
  disabled?: boolean;
  ariaLabel?: string;
  ariaInvalid?: boolean;
}

function formatDisplay(value: number | ""): string {
  if (value === "") return "";
  return value.toLocaleString("pt-BR");
}

export function NumericKgInput({ value, onChange, id, disabled, ariaLabel, ariaInvalid }: Props) {
  function handleChange(event: React.ChangeEvent<HTMLInputElement>) {
    const digits = event.target.value.replace(/\D/g, "");
    if (digits === "") {
      onChange("");
      return;
    }
    onChange(Number(digits));
  }

  function handleFocus(event: FocusEvent<HTMLInputElement>) {
    event.target.select();
  }

  return (
    <span className="kg-input">
      <input
        id={id}
        type="text"
        inputMode="numeric"
        value={formatDisplay(value)}
        onChange={handleChange}
        onFocus={handleFocus}
        disabled={disabled}
        aria-label={ariaLabel}
        aria-invalid={ariaInvalid}
        placeholder="0"
      />
      <span className="kg-input-suffix">kg</span>
    </span>
  );
}
