import { Outlet } from "react-router-dom";

export function NivelLayout() {
  return (
    <div className="page">
      <Outlet />
    </div>
  );
}
