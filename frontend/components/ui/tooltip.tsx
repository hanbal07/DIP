"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  side?: "top" | "bottom";
  className?: string;
}

/**
 * Dependency-free tooltip. Shows on hover and keyboard focus. The native title is
 * kept as a fallback so the information remains available to every user.
 */
export function Tooltip({ content, children, side = "top", className }: TooltipProps) {
  return (
    <span className={cn("group/tip relative inline-flex", className)}>
      {children}
      <span
        role="tooltip"
        className={cn(
          "pointer-events-none absolute left-1/2 z-[60] -translate-x-1/2 whitespace-nowrap rounded-md bg-foreground px-2 py-1 text-xs font-medium text-background opacity-0 shadow-md transition-[opacity,transform] duration-150",
          "group-hover/tip:opacity-100 group-focus-within/tip:opacity-100",
          side === "top" ? "bottom-full mb-1.5 origin-bottom -translate-y-1 group-hover/tip:translate-y-0 group-focus-within/tip:translate-y-0" : "top-full mt-1.5 origin-top translate-y-1 group-hover/tip:translate-y-0 group-focus-within/tip:translate-y-0"
        )}
      >
        {content}
      </span>
      <span title={content} className="sr-only">
        {content}
      </span>
    </span>
  );
}