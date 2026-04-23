/**
 * Unit tests for OverlayEngine component.
 */
import { describe, it, expect, vi } from "vitest";
import { render, fireEvent, waitFor } from "@testing-library/react";
import OverlayEngine from "../components/OverlayEngine";

describe("OverlayEngine", () => {
  it("renders overlay with pixel fallback in screenshot mode", () => {
    const { getByTestId } = render(
      <OverlayEngine
        targetComponentId="btn_submit"
        renderMode="screenshot"
        expectedAction="TAP"
        pixelFallback={{ x: 10, y: 20, width: 60, height: 10 }}
        onCorrectAction={() => {}}
        onWrongAction={() => {}}
        errorMessage="Wrong element!"
      />,
    );

    const highlight = getByTestId("overlay-highlight");
    expect(highlight).toBeDefined();
    // In screenshot mode with pixelFallback, positions use percentages
    expect(highlight.style.left).toBe("10%");
    expect(highlight.style.top).toBe("20%");
  });

  it("shows fallback overlay when target component not found in DOM", async () => {
    const { getByTestId } = render(
      <OverlayEngine
        targetComponentId="nonexistent_component"
        renderMode="component"
        expectedAction="TAP"
        onCorrectAction={() => {}}
        onWrongAction={() => {}}
        errorMessage="Wrong!"
      />,
    );

    // After retries exhaust, fallback should appear
    await waitFor(
      () => {
        expect(getByTestId("overlay-fallback")).toBeDefined();
      },
      { timeout: 2000 },
    );

    expect(getByTestId("overlay-fallback").textContent).toContain(
      "Target element not found",
    );
  });

  it("calls onCorrectAction when highlight is clicked for TAP action", () => {
    const onCorrect = vi.fn();
    const { getByTestId } = render(
      <OverlayEngine
        targetComponentId="btn"
        renderMode="screenshot"
        expectedAction="TAP"
        pixelFallback={{ x: 10, y: 10, width: 50, height: 20 }}
        onCorrectAction={onCorrect}
        onWrongAction={() => {}}
        errorMessage="Wrong!"
      />,
    );

    fireEvent.click(getByTestId("overlay-highlight"));
    expect(onCorrect).toHaveBeenCalledTimes(1);
  });

  it("calls onWrongAction when backdrop is clicked for TAP action", () => {
    const onWrong = vi.fn();
    const { getByTestId } = render(
      <OverlayEngine
        targetComponentId="btn"
        renderMode="screenshot"
        expectedAction="TAP"
        pixelFallback={{ x: 10, y: 10, width: 50, height: 20 }}
        onCorrectAction={() => {}}
        onWrongAction={onWrong}
        errorMessage="That's wrong!"
      />,
    );

    fireEvent.click(getByTestId("overlay-backdrop"));
    expect(onWrong).toHaveBeenCalledWith("That's wrong!");
  });

  it("shows error toast after wrong tap", async () => {
    const { getByTestId } = render(
      <OverlayEngine
        targetComponentId="btn"
        renderMode="screenshot"
        expectedAction="TAP"
        pixelFallback={{ x: 10, y: 10, width: 50, height: 20 }}
        onCorrectAction={() => {}}
        onWrongAction={() => {}}
        errorMessage="Try again!"
      />,
    );

    fireEvent.click(getByTestId("overlay-backdrop"));

    await waitFor(() => {
      const error = getByTestId("overlay-error");
      expect(error.textContent).toContain("Try again!");
    });
  });

  it("renders arrow pointing to target", () => {
    const { getByTestId } = render(
      <OverlayEngine
        targetComponentId="btn"
        renderMode="screenshot"
        expectedAction="TAP"
        pixelFallback={{ x: 20, y: 30, width: 40, height: 10 }}
        onCorrectAction={() => {}}
        onWrongAction={() => {}}
        errorMessage="Wrong!"
      />,
    );

    expect(getByTestId("overlay-arrow")).toBeDefined();
  });
});
