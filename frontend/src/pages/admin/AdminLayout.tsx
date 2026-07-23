import { Outlet } from "react-router-dom";

export function AdminLayout() {
  return (
    <div className="page">
      <Outlet />
    </div>
  );
}
