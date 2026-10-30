import React from "react";

function errorText(error) {
  return error instanceof Error ? error.message : "Ocorreu um erro inesperado.";
}

function Notice({ children, kind = "info", onClose }) {
  if (!children) return null;
  return <div className={"notice " + kind} role="status">
    <span>{children}</span>{onClose && <button className="icon-button" onClick={onClose} aria-label="Fechar aviso">×</button>}
  </div>;
}

function Button({ children, secondary = false, small = false, disabled = false, ...props }) {
  return <button className={"button" + (secondary ? " secondary" : "") + (small ? " small" : "")} disabled={disabled} {...props}>{children}</button>;
}

function Chip({ children, active = false, ...props }) {
  return <button className={"chip" + (active ? " active" : "")} {...props}>{children}</button>;
}

export { errorText, Notice, Button, Chip };
