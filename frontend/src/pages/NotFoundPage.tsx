import { Link } from "react-router";

import { useAuth } from "../auth/AuthProvider";

export function NotFoundPage() {
  const { isAuthenticated } = useAuth();

  return (
    <main>
      <h1>Page not found</h1>

      <p>The requested page does not exist.</p>

      <Link
        to={isAuthenticated ? "/applications" : "/login"}
      >
        {isAuthenticated
          ? "Return to applications"
          : "Go to login"}
      </Link>
    </main>
  );
}