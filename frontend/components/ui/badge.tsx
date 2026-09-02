import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium leading-5 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background [&>svg]:size-3 [&>svg]:shrink-0",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground",
        outline: "border-border text-foreground bg-background",
        destructive:
          "border-transparent bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
        success:
          "border-transparent bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
        warning:
          "border-transparent bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
        info: "border-transparent bg-sky-50 text-sky-700 dark:bg-sky-950 dark:text-sky-300",
        neutral:
          "border-border bg-muted/60 text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {
  /** Show a small status dot before the label (primary-colored by default). */
  dot?: boolean;
}

function Badge({ className, variant, dot = false, children, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && <span aria-hidden className="size-1.5 rounded-full bg-current" />}
      {children}
    </div>
  );
}

export { Badge, badgeVariants };