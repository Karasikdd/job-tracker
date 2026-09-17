type ErrorMessageProps = {
  message: string;
  onRetry?: () => void;
};

export function ErrorMessage({
  message,
  onRetry,
}: ErrorMessageProps) {
  return (
    <div className="error-panel" role="alert">
      <p>{message}</p>

      {onRetry !== undefined && (
        <button type="button" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}