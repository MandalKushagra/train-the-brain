/**
 * Unit tests for manifestUtils — legacy detection and rendering mode.
 */
import { describe, it, expect } from "vitest";
import { isLegacyManifest, getRenderingMode } from "../utils/manifestUtils";
import type { SimulationStep } from "../types/manifest";
import type { ScreenConfig } from "../types/screenConfig";

describe("isLegacyManifest", () => {
  it("detects a legacy manifest with tap_target and no target_component_id", () => {
    const legacy = {
      steps: [
        {
          step_id: 1,
          screen_id: "login",
          screen: "Login",
          title: "Tap Login",
          instruction: "Tap the login button",
          tip: null,
          expected_action: "TAP",
          on_wrong_action: "Wrong!",
          tap_target: { x: 50, y: 80, width: 30, height: 8 },
          screenshot: "login.png",
        },
      ],
    };

    expect(isLegacyManifest(legacy)).toBe(true);
  });

  it("returns false for a new manifest with target_component_id", () => {
    const newManifest = {
      steps: [
        {
          step_id: 1,
          screen_id: "login",
          screen: "Login",
          title: "Tap Login",
          instruction: "Tap the login button",
          tip: null,
          expected_action: "TAP",
          on_wrong_action: "Wrong!",
          target_component_id: "btn_login",
        },
      ],
    };

    expect(isLegacyManifest(newManifest)).toBe(false);
  });

  it("returns false for manifest with no steps", () => {
    expect(isLegacyManifest({ steps: [] })).toBe(false);
  });

  it("returns false for manifest with undefined steps", () => {
    expect(isLegacyManifest({})).toBe(false);
  });

  it("detects legacy when at least one step has tap_target without target_component_id", () => {
    const mixed = {
      steps: [
        {
          step_id: 1,
          target_component_id: "btn_1",
        },
        {
          step_id: 2,
          tap_target: { x: 10, y: 20, width: 30, height: 40 },
          // no target_component_id
        },
      ],
    };

    expect(isLegacyManifest(mixed)).toBe(true);
  });
});

describe("getRenderingMode", () => {
  const sampleScreenConfig: ScreenConfig = {
    screen_id: "login",
    screen_name: "Login",
    source: "manual",
    elements: [
      {
        component_id: "btn_login",
        type: "button",
        label: "Login",
        position: { x: 10, y: 80, width: 80, height: 8 },
      },
    ],
  };

  it('returns "component" when screen_configs contains the step screen_id', () => {
    const step: SimulationStep = {
      step_id: 1,
      screen_id: "login",
      screen: "Login",
      title: "Tap Login",
      instruction: "Tap the login button",
      tip: null,
      expected_action: "TAP",
      on_wrong_action: "Wrong!",
      target_component_id: "btn_login",
    };

    const mode = getRenderingMode(step, { login: sampleScreenConfig });
    expect(mode).toBe("component");
  });

  it('returns "screenshot" when no screen_config but step has screenshot', () => {
    const step: SimulationStep = {
      step_id: 1,
      screen_id: "dashboard",
      screen: "Dashboard",
      title: "Tap Menu",
      instruction: "Tap the menu",
      tip: null,
      expected_action: "TAP",
      on_wrong_action: "Wrong!",
      target_component_id: "btn_menu",
      screenshot: "dashboard.png",
    };

    const mode = getRenderingMode(step, {});
    expect(mode).toBe("screenshot");
  });

  it('returns "placeholder" when neither screen_config nor screenshot exists', () => {
    const step: SimulationStep = {
      step_id: 1,
      screen_id: "missing",
      screen: "Missing Screen",
      title: "Step",
      instruction: "Do something",
      tip: null,
      expected_action: "TAP",
      on_wrong_action: "Wrong!",
      target_component_id: "btn_x",
    };

    const mode = getRenderingMode(step, {});
    expect(mode).toBe("placeholder");
  });
});
