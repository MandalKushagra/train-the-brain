/**
 * Property-based tests for Floating Tip Widget using fast-check.
 *
 * Feature: simulation-optimization
 */
import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import { render } from "@testing-library/react";
import FloatingTipWidget from "../../components/FloatingTipWidget";

// ── Arbitraries ──────────────────────────────────────────────

const arbTipText = fc.string({ minLength: 1, maxLength: 50 });

// ── Property Tests ───────────────────────────────────────────

describe("Floating Tip Widget Property Tests", () => {
  // Feature: simulation-optimization, Property 12: Tip widget visibility matches tip availability
  it("Property 12: widget is visible iff tipText is non-null and isVisible is true", () => {
    fc.assert(
      fc.property(
        fc.oneof(arbTipText, fc.constant(null)),
        fc.boolean(),
        (tipText, isVisible) => {
          // Validates: Requirements 6.2, 6.4, 6.5
          const { queryByTestId } = render(
            <FloatingTipWidget tipText={tipText} isVisible={isVisible} />,
          );

          const button = queryByTestId("tip-widget-button");

          if (tipText && isVisible) {
            // Widget should be visible
            expect(button).not.toBeNull();
          } else {
            // Widget should be hidden
            expect(button).toBeNull();
          }
        },
      ),
      { numRuns: 100 },
    );
  });
});
