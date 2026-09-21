import {
  NavLink,
  Outlet,
  useNavigate,
} from "react-router";

import { useAuth } from "../auth/AuthProvider";
import { NotificationBell } from "./NotificationBell";
import { NotificationsProvider } from "../notifications/NotificationsProvider";

function getNavigationClassName({
  isActive,
}: {
  isActive: boolean;
}): string {
  return isActive
    ? "navigation-link navigation-link-active"
    : "navigation-link";
}

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout(): void {
    logout();
    navigate("/login", { replace: true });
  }

  return (
      <NotificationsProvider>
        <div className="app">
          <header className="app-header">
            <div className="header-content">
              <NavLink
                className="brand"
                to="/applications"
                aria-label="Job Tracker home"
              >
                Job Tracker
              </NavLink>

              <nav
                className="navigation"
                aria-label="Main navigation"
              >
                <NavLink
                  className={getNavigationClassName}
                  to="/applications"
                >
                  Applications
                </NavLink>

                <NavLink
                  className={getNavigationClassName}
                  to="/stats"
                >
                  Statistics
                </NavLink>
                <NotificationBell />
              </nav>

              <div className="user-menu">
                {user !== null && (
                  <span
                    className="user-email"
                    title={user.email}
                  >
                    {user.email}
                  </span>
                )}

                <button
                  className="logout-button"
                  type="button"
                  onClick={handleLogout}
                >
                  Logout
                </button>
              </div>
            </div>
          </header>

          <main className="page-container">
            <Outlet />
          </main>
        </div>
    </NotificationsProvider>
  );
}