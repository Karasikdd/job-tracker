import {
  type FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  Link,
  Navigate,
  useNavigate,
} from "react-router";

import { registerUser } from "../api/auth";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";

export function RegisterPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
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

    const normalizedEmail = email.trim();

    if (password !== passwordConfirmation) {
      setErrorMessage("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);

    controllerRef.current?.abort();

    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      await registerUser(
        {
          email: normalizedEmail,
          password,
        },
        controller.signal,
      );

      navigate("/login", {
        replace: true,
        state: {
          email: normalizedEmail,
          message: "Registration completed. You can now log in.",
        },
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
      <h1>Register</h1>

      <form onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="register-email">Email</label>

          <input
            id="register-email"
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
          <label htmlFor="register-password">Password</label>

          <input
            id="register-password"
            name="password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={12}
            maxLength={128}
            required
            disabled={isSubmitting}
          />

          <small>
            Use between 12 and 128 characters.
          </small>
        </div>

        <div className="form-field">
          <label htmlFor="register-password-confirmation">
            Confirm password
          </label>

          <input
            id="register-password-confirmation"
            name="passwordConfirmation"
            type="password"
            autoComplete="new-password"
            value={passwordConfirmation}
            onChange={(event) =>
              setPasswordConfirmation(event.target.value)
            }
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
          {isSubmitting ? "Creating account..." : "Register"}
        </button>
      </form>

      <p>
        Already registered? <Link to="/login">Login</Link>
      </p>
    </main>
  );
}