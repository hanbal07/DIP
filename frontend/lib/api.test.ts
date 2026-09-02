import { describe, expect, it } from "vitest";
import { cn } from "./utils";
import { formatBytes, formatDate, formatPercent } from "./api";

describe("cn", () => {
  it("joins class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("filters falsy values", () => {
    expect(cn("a", false && "b", undefined, null, "c")).toBe("a c");
  });

  it("merges tailwind conflicts (last wins)", () => {
    expect(cn("px-2", "px-4")).toBe("px-4");
  });
});

describe("formatBytes", () => {
  it("formats bytes", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(1536)).toBe("1.5 KB");
    expect(formatBytes(1024 * 1024)).toBe("1.0 MB");
  });
});

describe("formatPercent", () => {
  it("rounds to integer percent", () => {
    expect(formatPercent(0.453)).toBe("45%");
    expect(formatPercent(1)).toBe("100%");
    expect(formatPercent(0)).toBe("0%");
  });
});

describe("formatDate", () => {
  it("returns placeholder for null", () => {
    expect(formatDate(null)).toBe("—");
  });

  it("formats ISO dates", () => {
    expect(formatDate("2024-01-02T03:04:05Z")).not.toBe("—");
  });
});