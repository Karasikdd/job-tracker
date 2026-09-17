import { Link, Outlet, useNavigate } from "react-router";

import { useAuth } from "../auth/AuthProvider";

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="app">
      <header className="app-header">
        <Link className="brand" to="/applications">
          Job Tracker
        </Link>

        <nav className="navigation" aria-label="Main navigation">
          <Link to="/applications">Applications</Link>
          <Link to="/dashboard">Statistics</Link>
        </nav>

        <div className="user-menu">
          {user !== null && (
            <span className="user-email">{user.email}</span>
          )}

          <button type="button" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </header>

      <main className="page-container">
        <Outlet />
      </main>
    </div>
  );
}