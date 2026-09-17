import { useState } from "react";
import { Link } from "react-router";

import { ApiError, apiRequest } from "../api/client";

type HealthResponse = {
  status: string;
};

export function HomePage() {
  const [apiStatus, setApiStatus] = useState("Not checked");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function checkApi() {
    setIsLoading(true);
    setErrorMessage(null);
    setApiStatus("Checking...");

    try {
      const result = await apiRequest<HealthResponse>("/health");
      setApiStatus(result.status);
    } catch (error) {
      setApiStatus("Unavailable");

      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("An unexpected error occurred.");
      }
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main>
      <h1>Job Tracker</h1>

      <p>A web interface for managing job applications.</p>

      <nav>
        <Link to="/login">Login</Link>
        {" | "}
        <Link to="/register">Register</Link>
      </nav>

      <h2>API connection</h2>

      <button
        type="button"
        onClick={checkApi}
        disabled={isLoading}
      >
        {isLoading ? "Checking..." : "Check API"}
      </button>

      <p>API status: {apiStatus}</p>

      {errorMessage !== null && (
        <p role="alert">{errorMessage}</p>
      )}
    </main>
  );
}