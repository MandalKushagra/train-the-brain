/**
 * Property-based tests for Overlay Engine (tap actions) using fast-check.
 *
 * Feature: simulation-optimization
 */
import { describe, it, expect, vi } from "vitest";
import * as fc from "fast-check";
import { render, fireEvent } from "@testing-library/react";
import OverlayEngine from "../../components/OverlayEngine";

// ── Arbitraries ──────────────────────────────────────────────

const arbNonEmptyString = fc.stringMatching(/^[a-z0-9_]{1,20}$/);

const arbErrorMessage = fc.string({ minLength: 5, maxLength: 40 });

// ── Property Tests ───────────────────────────────────────────

describe("Overlay Engine Property Tests", () => {
  // Feature: simulation-optimization, Property 9: Correct tap advances step
  it("Property 9: clicking the overlay highlight calls onCorrectAction for TAP", () => {
    fc.assert(
      fc.property(arbNonEmptyString, arbErrorMessage, (targetId, errorMsg) => {
        // Validates: Requirements 5.4
        const onCorrect = vi.fn();
        const onWrong = vi.fn();

        // Render with pixelFallback so we have a known rect (screenshot mode for simplicity)
        const { getByTestId } = render(
          <OverlayEngine
            targetComponentId={targetId}
            renderMode="screenshot"
            expectedAction="TAP"
            pixelFallback={{ x: 10, y: 10, width: 50, height: 20 }}
            onCorrectAction={onCorrect}
            onWrongAction={onWrong}
            errorMessage={errorMsg}
          />,
        );

        const highlight = getByTestId("overlay-highlight");
        fireEvent.click(highlight);

        expect(onCorrect).toHaveBeenCalledTimes(1);
        expect(onWrong).not.toHaveBeenCalled();
      }),
      { numRuns: 100 },
    );
  });

  // Feature: simulation-optimization, Property 10: Wrong tap shows error feedback
  it("Property 10: clicking the backdrop calls onWrongAction with error message for TAP", () => {
    fc.assert(
      fc.property(arbNonEmptyString, arbErrorMessage, (targetId, errorMsg) => {
        // Validates: Requirements 5.5
        const onCorrect = vi.fn();
        const onWrong = vi.fn();

        const { getByTestId } = render(
          <OverlayEngine
            targetComponentId={targetId}
            renderMode="screenshot"
            expectedAction="TAP"
            pixelFallback={{ x: 10, y: 10, width: 50, height: 20 }}
            onCorrectAction={onCorrect}
            onWrongAction={onWrong}
            errorMessage={errorMsg}
          />,
        );

        const backdrop = getByTestId("overlay-backdrop");
        fireEvent.click(backdrop);

        expect(onWrong).toHaveBeenCalledWith(errorMsg);
        expect(onCorrect).not.toHaveBeenCalled();
      }),
      { numRuns: 100 },
    );
  });
});
