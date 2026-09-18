import { Navigate } from "react-router";

import { useAuth } from "../auth/AuthProvider";

export function RootRedirect() {
  const { isAuthenticated } = useAuth();

  return (
    <Navigate
      to={isAuthenticated ? "/applications" : "/login"}
      replace
    />
  );
}