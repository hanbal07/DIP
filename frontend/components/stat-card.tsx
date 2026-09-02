import { AnimatedNumber } from "@/components/motion/animated-number";
import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: number;
  icon?: React.ReactNode;
  hint?: string;
  tone?: "default" | "success" | "warning" | "destructive" | "info";
  className?: string;
}

const TONE_TEXT: Record<NonNullable<StatCardProps["tone"]>, string> = {
  default: "bg-muted text-foreground",
  success: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  warning: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  destructive: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
  info: "bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
};

/**
 * Dashboard KPI card. The number animates via <AnimatedNumber> (respects
 * prefers-reduced-motion). Only real counts are shown; pages that lack data
 * render honest zero / empty states instead of invented metrics.
 */
export function StatCard({
  label,
  value,
  icon,
  hint,
  tone = "default",
  className,
}: StatCardProps) {
  return (
    <Card hoverable className={cn("p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <p className="text-sm font-medium text-muted-foreground">{label}</p>
          <p className="flex items-baseline gap-1 text-3xl font-semibold tracking-tight tabular-nums">
            <AnimatedNumber value={value} />
          </p>
        </div>
        {icon && (
          <div
            className={cn(
              "flex size-9 shrink-0 items-center justify-center rounded-lg",
              TONE_TEXT[tone]
            )}
          >
            {icon}
          </div>
        )}
      </div>
      {hint && (
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{hint}</p>
      )}
    </Card>
  );
}