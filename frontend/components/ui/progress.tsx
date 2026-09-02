import * as React from "react";
import { cn } from "@/lib/utils";

interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
  /** Render an indeterminate shimmer overlay (used while a stage is running). */
  indeterminate?: boolean;
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value = 0, indeterminate = false, ...props }, ref) => {
    const clamped = Math.min(100, Math.max(0, value));
    return (
      <div
        ref={ref}
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(clamped)}
        className={cn(
          "relative h-2 w-full overflow-hidden rounded-full bg-muted",
          className
        )}
        {...props}
      >
        <div
          className="h-full rounded-full bg-primary transition-[width,transform] duration-500 ease-out"
          style={{ width: `${Math.max(clamped, 0)}%` }}
        />
        {indeterminate && (
          <div className="animate-shimmer absolute inset-0 bg-[linear-gradient(90deg,transparent,hsl(var(--primary)/0.18),transparent)]" />
        )}
      </div>
    );
  }
);
Progress.displayName = "Progress";

export { Progress };