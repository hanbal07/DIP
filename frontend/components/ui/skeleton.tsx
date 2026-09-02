import { cn } from "@/lib/utils";

/**
 * Polished loading placeholder with a soft shimmer sweep instead of the default
 * pulse. Purely decorative; marks itself so screen readers can ignore it.
 */
function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      aria-hidden
      className={cn(
        "animate-shimmer rounded-md bg-[linear-gradient(100deg,var(--tw-gradient-from),var(--tw-gradient-to))]",
        "[--tw-gradient-from:hsl(var(--muted))] [--tw-gradient-to:hsl(var(--muted)/0.4)]",
        className
      )}
      {...props}
    />
  );
}

export { Skeleton };