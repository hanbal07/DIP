import { cn } from "@/lib/utils";

/**
 * Small inline spinner for loading states within buttons, badges, and lists.
 * Asks assistive tech to announce the busy state via aria-label.
 */
export function Spinner({
  className,
  label = "Loading",
}: {
  className?: string;
  label?: string;
}) {
  return (
    <svg
      className={cn("animate-spin-slow", className)}
      viewBox="0 0 24 24"
      fill="none"
      role="status"
      aria-label={label}
      aria-live="polite"
    >
      <circle
        className="opacity-20"
        cx="12"
        cy="12"
        r="9"
        stroke="currentColor"
        strokeWidth="2.5"
      />
      <path
        className="opacity-90"
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
      />
    </svg>
  );
}