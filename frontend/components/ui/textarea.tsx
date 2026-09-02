import * as React from "react";
import { cn } from "@/lib/utils";

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        "flex min-h-[60px] w-full rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm transition-[border-color,box-shadow,background-color] duration-150 placeholder:text-muted-foreground/80",
        "hover:border-input/70",
        "focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30 focus-visible:shadow-md",
        "disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      ref={ref}
      {...props}
    />
  );
});
Textarea.displayName = "Textarea";

export { Textarea };