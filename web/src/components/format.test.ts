import { describe, expect, it } from "vitest";

import { formatDate, formatDays, titleCase } from "./format";

describe("formatDate", () => {
  it("does not shift a date-only value across a timezone", () => {
    expect(formatDate("2026-03-01")).toBe("1 Mar 2026");
  });

  it("returns a dash for nothing", () => {
    expect(formatDate(null)).toBe("—");
  });
});

describe("formatDays", () => {
  it("says ago for the past", () => {
    expect(formatDays(-3)).toBe("3 days ago");
  });

  it("handles the singular", () => {
    expect(formatDays(1)).toBe("in 1 day");
  });

  it("handles no expiry", () => {
    expect(formatDays(null)).toBe("no expiry");
  });
});

describe("titleCase", () => {
  it("turns an enum value into prose", () => {
    expect(titleCase("non_compliant")).toBe("Non Compliant");
  });
});
