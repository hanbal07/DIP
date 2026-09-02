"use client";

import * as React from "react";
import { ChevronDown, Check } from "lucide-react";
import { cn } from "@/lib/utils";

// A dependency-light, accessible select built on the native <select> element,
// exposing the shadcn-style API used across the app.

interface SelectContextValue {
  value: string;
  onValueChange: (value: string) => void;
  items: { value: string; label: string }[];
  register: (value: string, label: string) => void;
}

const SelectContext = React.createContext<SelectContextValue | null>(null);

export function Select({
  value,
  defaultValue,
  onValueChange,
  children,
  className,
  disabled,
}: {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  className?: string;
  disabled?: boolean;
}) {
  const [self, setSelf] = React.useState(defaultValue ?? value ?? "");
  const selected = value !== undefined ? value : self;
  const [items, setItems] = React.useState<{ value: string; label: string }[]>([]);
  const [open, setOpen] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (!open) return;
    const onPointer = (e: MouseEvent | TouchEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("touchstart", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("touchstart", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <SelectContext.Provider
      value={{
        value: selected,
        onValueChange: (v) => {
          if (value === undefined) setSelf(v);
          onValueChange?.(v);
          setOpen(false);
        },
        items,
        register: (v, label) =>
          setItems((prev) =>
            prev.some((i) => i.value === v) ? prev : [...prev, { value: v, label }]
          ),
      }}
    >
      <div
        ref={containerRef}
        className={cn("relative", className)}
        data-disabled={disabled || undefined}
      >
        {typeof children === "function"
          ? (children as (props: { open: boolean; setOpen: (o: boolean) => void }) => React.ReactNode)({
              open,
              setOpen,
            })
          : React.Children.map(children, (child) => {
              if (!React.isValidElement(child)) return child;
              if ((child.type as { displayName?: string }).displayName === "SelectTrigger") {
                return React.cloneElement(
                  child as React.ReactElement<{
                    onClick?: () => void;
                    "aria-expanded"?: boolean;
                    "data-state"?: string;
                  }>,
                  {
                    onClick: () => !disabled && setOpen((o) => !o),
                    "aria-expanded": open,
                    "data-state": open ? "open" : "closed",
                  }
                );
              }
              if ((child.type as { displayName?: string }).displayName === "SelectContent") {
                if (!open) return null;
                return React.cloneElement(child as React.ReactElement<{ onClose?: () => void }>, {
                  onClose: () => setOpen(false),
                });
              }
              return child;
            })}
      </div>
    </SelectContext.Provider>
  );
}

export const SelectTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement>
>(({ className, children, ...props }, ref) => (
  <button
    ref={ref}
    type="button"
    aria-haspopup="listbox"
    className={cn(
      "flex h-9 w-full items-center justify-between gap-2 rounded-md border border-input bg-card px-3 py-2 text-sm text-foreground shadow-sm transition-[border-color,box-shadow,background-color,transform] duration-150",
      "hover:border-input/70",
      "focus-visible:border-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/30",
      "disabled:cursor-not-allowed disabled:opacity-50",
      className
    )}
    {...props}
  >
    {children}
    <ChevronDown className="size-3.5 shrink-0 text-muted-foreground transition-transform duration-150 data-[state=open]:rotate-180" />
  </button>
));
SelectTrigger.displayName = "SelectTrigger";

export function SelectValue({ placeholder }: { placeholder?: string }) {
  const ctx = React.useContext(SelectContext);
  if (!ctx) return null;
  const label = ctx.items.find((i) => i.value === ctx.value)?.label;
  return (
    <span className={cn("truncate", !label && "text-muted-foreground")}>
      {label ?? placeholder}
    </span>
  );
}

export function SelectContent({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const ctx = React.useContext(SelectContext);
  if (!ctx) return null;
  return (
    <div
      role="listbox"
      className={cn(
        "absolute z-40 mt-1.5 w-full min-w-[var(--select-min-w,9rem)] overflow-hidden rounded-lg border border-border bg-popover shadow-lg animate-scale-in",
        className
      )}
    >
      <div className="max-h-72 overflow-y-auto p-1">{children}</div>
    </div>
  );
}

export function SelectItem({
  value,
  children,
  disabled,
  className,
}: {
  value: string;
  children: React.ReactNode;
  disabled?: boolean;
  className?: string;
}) {
  const ctx = React.useContext(SelectContext);
  if (!ctx) return null;
  const label = typeof children === "string" ? children : String(children ?? value);
  React.useEffect(() => {
    ctx.register(value, label);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, label]);
  const selected = ctx.value === value;
  return (
    <button
      type="button"
      role="option"
      aria-selected={selected}
      disabled={disabled}
      onClick={() => {
        if (!disabled) ctx.onValueChange(value);
      }}
      className={cn(
        "flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors duration-100 hover:bg-accent hover:text-accent-foreground",
        selected && "bg-accent/60 font-medium text-accent-foreground",
        disabled && "cursor-not-allowed opacity-50",
        className
      )}
    >
      <span className="truncate">{children}</span>
      {selected && <Check className="size-3.5 shrink-0 text-primary" />}
    </button>
  );
}