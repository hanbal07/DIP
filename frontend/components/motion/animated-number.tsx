"use client";

import * as React from "react";

interface AnimatedNumberProps {
  value: number;
  duration?: number;
  className?: string;
  format?: (n: number) => string;
}

/**
 * Counts from the previous value to the current value using requestAnimationFrame.
 * Uses easeOutCubic so it feels fast and deliberate. Fully disabled under
 * prefers-reduced-motion (jumps straight to the target value).
 */
export function AnimatedNumber({
  value,
  duration = 500,
  className,
  format,
}: AnimatedNumberProps) {
  const [display, setDisplay] = React.useState(value);
  const prevRef = React.useRef(value);
  const rafRef = React.useRef<number>(0);

  React.useEffect(() => {
    if (typeof window === "undefined") return;

    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setDisplay(value);
      prevRef.current = value;
      return;
    }

    const from = prevRef.current;
    const to = value;
    if (from === to) return;
    const start = performance.now();

    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      setDisplay(Math.round(from + (to - from) * eased));
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        prevRef.current = to;
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(rafRef.current);
  }, [value, duration]);

  const text = format ? format(display) : String(display);
  return <span className={className}>{text}</span>;
}