import { NavLink } from "react-router";

import { useNotifications } from "../notifications/NotificationsProvider";

export function NotificationBell() {
  const { unreadCount, countError } = useNotifications();

  const label = countError
    ? "Notifications, unread count temporarily unavailable"
    : unreadCount === null
      ? "Notifications"
      : `Notifications, ${unreadCount} unread`;

  return (
    <NavLink
      to="/notifications"
      className={({ isActive }) =>
        isActive
          ? "navigation-link navigation-link-active notification-link"
          : "navigation-link notification-link"
      }
      aria-label={label}
      title={label}
    >
      <span aria-hidden="true">🔔</span>
      <span>Notifications</span>

      {countError ? (
        <span aria-hidden="true">!</span>
      ) : unreadCount !== null && unreadCount > 0 ? (
        <span className="notification-count" aria-hidden="true">
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      ) : null}
    </NavLink>
  );
}