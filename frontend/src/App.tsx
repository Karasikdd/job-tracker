import { Route, Routes } from "react-router";

import { RequireAuth } from "./auth/RequireAuth";
import { AppLayout } from "./components/AppLayout";
import { RootRedirect } from "./components/RootRedirect";
import { ApplicationPage } from "./pages/ApplicationPage";
import { ApplicationsPage } from "./pages/ApplicationsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LoginPage } from "./pages/LoginPage";
import { NotFoundPage } from "./pages/NotFoundPage";
import { RegisterPage } from "./pages/RegisterPage";
import { NewApplicationPage } from "./pages/NewApplicationPage";
import { StatsPage } from "./pages/StatsPage";
import { NotificationsPage } from "./pages/NotificationsPage";
export default function App() {
  return (
  <Routes>
    <Route path="/" element={<RootRedirect />} />

    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />

    <Route element={<RequireAuth />}>
      <Route element={<AppLayout />}>
        <Route
          path="/applications"
          element={<ApplicationsPage />}
        />
        <Route
          path="/applications/new"
          element={<NewApplicationPage />}
        />
        <Route
          path="/applications/:id"
          element={<ApplicationPage />}
        />
        <Route
          path="/dashboard"
          element={<DashboardPage />}
        />
        <Route
          path="/stats"
          element={<StatsPage />}
        />
        <Route
          path="/notifications"
          element={<NotificationsPage />}
        />
      </Route>
    </Route>

    <Route path="*" element={<NotFoundPage />} />
  </Routes>
);
}