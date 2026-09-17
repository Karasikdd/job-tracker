import { Link, Outlet } from "react-router";

export function AppLayout() {
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
      </header>

      <main className="page-container">
        <Outlet />
      </main>
    </div>
  );
}