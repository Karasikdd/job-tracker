import { useRef, useState } from "react";
import {
  useLocation,
  useNavigate,
} from "react-router";

import { createApplication } from "../api/applications";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { ApplicationForm } from "../components/ApplicationForm";

import type { ApplicationCreate } from "../types/api";

export function NewApplicationPage() {
  const {
    accessToken,
    logout,
  } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();

  const controllerRef = useRef<AbortController | null>(null);

  const [errorMessage, setErrorMessage] =
    useState<string | null>(null);

  async function handleCreate(
    payload: ApplicationCreate,
  ): Promise<void> {
    if (accessToken === null) {
      return;
    }

    setErrorMessage(null);

    controllerRef.current?.abort();

    const controller = new AbortController();
    controllerRef.current = controller;

    try {
      const createdApplication = await createApplication(
        accessToken,
        payload,
        controller.signal,
      );

      navigate(
        `/applications/${createdApplication.id}`,
        {
          replace: true,
        },
      );
    } catch (error) {
      if (error instanceof DOMException && error.name === "AbortError") {
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

      if (error instanceof ApiError) {
        setErrorMessage(error.message);
      } else {
        setErrorMessage("An unexpected error occurred.");
      }
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null;
      }
    }
  }

  return (
    <section>
      <div className="page-heading">
        <div>
          <h1>Add application</h1>
          <p>Create a new job application.</p>
        </div>
      </div>

      <ApplicationForm
        submitLabel="Create application"
        errorMessage={errorMessage}
        onSubmit={handleCreate}
        onCancel={() => navigate("/applications")}
      />
    </section>
  );
}