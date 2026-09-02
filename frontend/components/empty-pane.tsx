import { Loader2, type LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface EmptyPaneProps {
  title: string;
  description?: string;
  icon?: LucideIcon;
  busy?: boolean;
  className?: string;
}

/** Compact placeholder used inside card panels. */
export function EmptyPane({ title, description, icon: Icon, busy, className }: EmptyPaneProps) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-2 py-10 text-center", className)}>
      {busy ? (
        <Loader2 className="size-5 animate-spin text-muted-foreground" />
      ) : Icon ? (
        <Icon className="size-5 text-muted-foreground" />
      ) : null}
      <p className="text-sm font-medium text-foreground">{title}</p>
      {description && <p className="max-w-sm text-xs text-muted-foreground">{description}</p>}
    </div>
  );
}