"use client";

import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cn } from "@/lib/utils";

interface RevealProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Elements reveal once when scrolled into the viewport. */
  asChild?: boolean;
  /** Stagger delay in milliseconds (used for grid entrances). */
  delay?: number;
  /** Vertical offset used for the initial hidden state (px). */
  y?: number;
  /** Keep observing (re-animate when re-entering viewport). Default: animate once. */
  reAnimate?: boolean;
}

/**
 * Scroll-triggered entrance helper. Wraps children in a node that fades + slides in
 * when it enters the viewport. Driven purely by opacity/transform for cheap compositing.
 * Respects prefers-reduced-motion via the `.reveal` CSS rules in globals.css.
 */
export function Reveal({
  asChild,
  delay = 0,
  y = 14,
  reAnimate = false,
  className,
  style,
  children,
  ...props
}: RevealProps) {
  const ref = React.useRef<HTMLDivElement>(null);
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const node = ref.current;
    if (!node) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true);
            observer.unobserve(entry.target);
          } else if (reAnimate) {
            setVisible(false);
          }
        }
      },
      { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [reAnimate]);

  const Comp = asChild ? Slot : "div";

  return (
    <Comp
      ref={ref}
      data-visible={visible || undefined}
      className={cn("reveal", visible && "is-visible", className)}
      style={{
        ...style,
        transitionDelay: visible ? `${delay}ms` : "0ms",
        transform: visible ? undefined : `translateY(${y}px)`,
      }}
      {...props}
    >
      {children}
    </Comp>
  );
}