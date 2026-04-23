/**
 * Unit tests for ComponentRenderer component.
 */
import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import ComponentRenderer from "../components/ComponentRenderer";
import type { ScreenConfig } from "../types/screenConfig";

const sampleConfig: ScreenConfig = {
  screen_id: "login_screen",
  screen_name: "Login Screen",
  source: "manual",
  elements: [
    {
      component_id: "header_main",
      type: "header",
      label: "WMS Login",
      position: { x: 0, y: 0, width: 100, height: 8 },
    },
    {
      component_id: "input_username",
      type: "input",
      label: "Username",
      position: { x: 10, y: 30, width: 80, height: 8 },
    },
    {
      component_id: "input_password",
      type: "input",
      label: "Password",
      position: { x: 10, y: 45, width: 80, height: 8 },
    },
    {
      component_id: "btn_login",
      type: "button",
      label: "Login",
      position: { x: 10, y: 60, width: 80, height: 8 },
    },
    {
      component_id: "label_footer",
      type: "text_label",
      label: "Forgot password?",
      position: { x: 10, y: 75, width: 80, height: 5 },
    },
  ],
};

describe("ComponentRenderer", () => {
  it("renders all elements with data-component-id attributes", () => {
    const { container } = render(
      <ComponentRenderer
        screenConfig={sampleConfig}
        onComponentClick={() => {}}
        onInputSubmit={() => {}}
      />,
    );

    for (const element of sampleConfig.elements) {
      const node = container.querySelector(
        `[data-component-id="${element.component_id}"]`,
      );
      expect(node).not.toBeNull();
    }
  });

  it("renders the correct number of components", () => {
    const { container } = render(
      <ComponentRenderer
        screenConfig={sampleConfig}
        onComponentClick={() => {}}
        onInputSubmit={() => {}}
      />,
    );

    const components = container.querySelectorAll("[data-component-id]");
    expect(components.length).toBe(sampleConfig.elements.length);
  });

  it("positions elements using percentage-based absolute positioning", () => {
    const { container } = render(
      <ComponentRenderer
        screenConfig={sampleConfig}
        onComponentClick={() => {}}
        onInputSubmit={() => {}}
      />,
    );

    const btnNode = container.querySelector(
      '[data-component-id="btn_login"]',
    ) as HTMLElement;
    expect(btnNode).not.toBeNull();
    expect(btnNode.style.left).toBe("10%");
    expect(btnNode.style.top).toBe("60%");
    expect(btnNode.style.width).toBe("80%");
    expect(btnNode.style.height).toBe("8%");
  });

  it("renders nested children within parent container", () => {
    const configWithChildren: ScreenConfig = {
      screen_id: "card_screen",
      screen_name: "Card Screen",
      source: "manual",
      elements: [
        {
          component_id: "card_main",
          type: "card",
          label: "Order Card",
          position: { x: 5, y: 10, width: 90, height: 40 },
          children: [
            {
              component_id: "card_label",
              type: "text_label",
              label: "Order #123",
              position: { x: 5, y: 5, width: 50, height: 10 },
            },
            {
              component_id: "card_btn",
              type: "button",
              label: "View Details",
              position: { x: 5, y: 25, width: 40, height: 10 },
            },
          ],
        },
      ],
    };

    const { container } = render(
      <ComponentRenderer
        screenConfig={configWithChildren}
        onComponentClick={() => {}}
        onInputSubmit={() => {}}
      />,
    );

    // Parent and children should all be rendered
    expect(
      container.querySelector('[data-component-id="card_main"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[data-component-id="card_label"]'),
    ).not.toBeNull();
    expect(
      container.querySelector('[data-component-id="card_btn"]'),
    ).not.toBeNull();
  });

  it("renders unsupported element types as placeholders", () => {
    const configWithUnsupported: ScreenConfig = {
      screen_id: "test",
      screen_name: "Test",
      source: "manual",
      elements: [
        {
          component_id: "unknown_widget",
          type: "slider" as any,
          label: "Volume",
          position: { x: 10, y: 10, width: 80, height: 10 },
        },
      ],
    };

    const { container } = render(
      <ComponentRenderer
        screenConfig={configWithUnsupported}
        onComponentClick={() => {}}
        onInputSubmit={() => {}}
      />,
    );

    const node = container.querySelector(
      '[data-component-id="unknown_widget"]',
    );
    expect(node).not.toBeNull();
    expect(node!.textContent).toContain("Volume");
    expect(node!.textContent!.toLowerCase()).toContain("unsupported");
  });
});
