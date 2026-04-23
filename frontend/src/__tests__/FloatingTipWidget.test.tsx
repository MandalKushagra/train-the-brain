/**
 * Unit tests for FloatingTipWidget component.
 */
import { describe, it, expect } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import FloatingTipWidget from "../components/FloatingTipWidget";

describe("FloatingTipWidget", () => {
  it("renders the lightbulb button when tip is available and visible", () => {
    const { getByTestId } = render(
      <FloatingTipWidget tipText="Remember to check the barcode" isVisible={true} />,
    );
    expect(getByTestId("tip-widget-button")).toBeDefined();
  });

  it("is hidden when tipText is null", () => {
    const { queryByTestId } = render(
      <FloatingTipWidget tipText={null} isVisible={true} />,
    );
    expect(queryByTestId("tip-widget-button")).toBeNull();
  });

  it("is hidden when isVisible is false", () => {
    const { queryByTestId } = render(
      <FloatingTipWidget tipText="Some tip" isVisible={false} />,
    );
    expect(queryByTestId("tip-widget-button")).toBeNull();
  });

  it("opens bottom sheet on button tap", () => {
    const { getByTestId, queryByTestId } = render(
      <FloatingTipWidget tipText="Scan the item first" isVisible={true} />,
    );

    // Bottom sheet should not be visible initially
    expect(queryByTestId("tip-bottom-sheet")).toBeNull();

    // Tap the button
    fireEvent.click(getByTestId("tip-widget-button"));

    // Bottom sheet should now be visible
    expect(getByTestId("tip-bottom-sheet")).toBeDefined();
    expect(getByTestId("tip-text").textContent).toBe("Scan the item first");
  });

  it("dismisses bottom sheet when OKAY is tapped", () => {
    const { getByTestId, queryByTestId } = render(
      <FloatingTipWidget tipText="Check the weight" isVisible={true} />,
    );

    // Open the sheet
    fireEvent.click(getByTestId("tip-widget-button"));
    expect(getByTestId("tip-bottom-sheet")).toBeDefined();

    // Tap OKAY
    fireEvent.click(getByTestId("tip-okay-button"));

    // Sheet should be dismissed
    expect(queryByTestId("tip-bottom-sheet")).toBeNull();
  });

  it("displays the correct tip text in the bottom sheet", () => {
    const tipText = "Always verify the shipment ID before proceeding";
    const { getByTestId } = render(
      <FloatingTipWidget tipText={tipText} isVisible={true} />,
    );

    fireEvent.click(getByTestId("tip-widget-button"));
    expect(getByTestId("tip-text").textContent).toBe(tipText);
  });
});
