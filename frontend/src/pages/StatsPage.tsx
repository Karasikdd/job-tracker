import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import { ApiError } from "../api/client";
import { getStats } from "../api/stats";
import { useAuth } from "../auth/AuthProvider";
import { ErrorMessage } from "../components/ErrorMessage";

import type {
  ApplicationStats,
  ApplicationStatus,
} from "../types/api";

const statusCards: {
  status: ApplicationStatus;
  label: string;
}[] = [
  { status: "saved", label: "Saved" },
  { status: "applied", label: "Applied" },
  { status: "interview", label: "Interview" },
  { status: "offer", label: "Offer" },
  { status: "rejected", label: "Rejected" },
];

const numberFormatter = new Intl.NumberFormat("en");

export function StatsPage() {
  const { accessToken, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [reloadNumber, setReloadNumber] = useState(0);

  useEffect(() => {
    if (accessToken === null) {
      setStats(null);
      setIsLoading(false);
      return;
    }

    const token = accessToken;
    const controller = new AbortController();

    async function loadStats(): Promise<void> {
      setIsLoading(true);
      setErrorMessage(null);
      setStats(null);

      try {
        const result = await getStats(token, controller.signal);

        if (!controller.signal.aborted) {
          setStats(result);
        }
      } catch (error) {
        if (controller.signal.aborted) {
          return;
        }

        if (error instanceof ApiError && error.status === 401) {
          logout();

          navigate("/login", {
            replace: true,
            state: {
              from: location.pathname,
              message: "Your session has expired. Please log in again.",
            },
          });

          return;
        }

        setErrorMessage(
          error instanceof ApiError
            ? error.message
            : "Could not load statistics.",
        );
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadStats();

    return () => {
      controller.abort();
    };
  }, [
    accessToken,
    reloadNumber,
    location.pathname,
    logout,
    navigate,
  ]);

  function refreshStats(): void {
    setReloadNumber((current) => current + 1);
  }

  if (accessToken === null) {
    return (
      <section>
        <h1>Please log in</h1>
        <p>You must be logged in to view your statistics.</p>
        <Link to="/login">Go to login</Link>
      </section>
    );
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <h1>Statistics</h1>
          <p>Your applications grouped by their current status.</p>
        </div>

        <button
          type="button"
          onClick={refreshStats}
          disabled={isLoading}
        >
          {isLoading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {isLoading ? (
        <p role="status">Loading statistics...</p>
      ) : errorMessage !== null ? (
        <ErrorMessage
          message={errorMessage}
          onRetry={refreshStats}
        />
      ) : stats !== null ? (
        <>
          <dl className="stats-grid">
            <div className="stats-card stats-card-total">
              <dt>Total applications</dt>
              <dd>{numberFormatter.format(stats.total)}</dd>
            </div>

            {statusCards.map(({ status, label }) => (
              <div className="stats-card" key={status}>
                <dt>{label}</dt>
                <dd>
                  {numberFormatter.format(stats.by_status[status])}
                </dd>
              </div>
            ))}
          </dl>

          {stats.total === 0 && (
            <div className="stats-empty">
              <h2>No applications yet</h2>
              <p>
                Add your first application to start tracking your progress.
              </p>

              <Link
                to="/applications/new"
                className="button-link"
              >
                Add application
              </Link>
            </div>
          )}

          <p>
            <Link to="/applications">View applications</Link>
          </p>
        </>
      ) : null}
    </section>
  );
}