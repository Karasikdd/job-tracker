import {
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Link,
  Navigate,
  useLocation,
  useNavigate,
} from "react-router";

import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";

type LoginLocationState = {
  from?: string;
  email?: string;
  message?: string;
};

function getSafeDestination(from: string | undefined): string {
  if (
    typeof from === "string" &&
    from.startsWith("/") &&
    !from.startsWith("//")
  ) {
    return from;
  }

  return "/applications";
}

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const locationState =
    location.state as LoginLocationState | null;

  const [email, setEmail] = useState(locationState?.email ?? "");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const controllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      controllerRef.current?.abort();
    };
  }, []);

  if (isAuthenticated) {
    return <Navigate to="/applications" replace />;
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setErrorMessage(null);
    setIsSubmitting(true);

    controllerRef.current?.abort();

    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      await login(
        {
          email: email.trim(),
          password,
        },
        controller.signal,
      );

      const destination = getSafeDestination(locationState?.from);

      navigate(destination, {
        replace: true,
        state: null,
      });
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
        return;
      }

      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("An unexpected error occurred.");
      }
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
        setIsSubmitting(false);
      }
    }
  }

  return (
    <main>
      <h1>Login</h1>

      {locationState?.message !== undefined && (
        <p role="status">{locationState.message}</p>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="login-email">Email</label>

          <input
            id="login-email"
            name="email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
            disabled={isSubmitting}
          />
        </div>

        <div className="form-field">
          <label htmlFor="login-password">Password</label>

          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={12}
            maxLength={128}
            required
            disabled={isSubmitting}
          />
        </div>

        {errorMessage !== null && (
          <p role="alert" className="error-message">
            {errorMessage}
          </p>
        )}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Logging in..." : "Login"}
        </button>
      </form>

      <p>
        Do not have an account?{" "}
        <Link to="/register">Register</Link>
      </p>
    </main>
  );
}