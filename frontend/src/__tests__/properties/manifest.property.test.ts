/**
 * Property-based tests for Simulation Manifest using fast-check.
 *
 * Feature: simulation-optimization
 */
import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import type {
  SimulationManifest,
  SimulationStep,
  ExpectedAction,
} from "../../types/manifest";
import type {
  ScreenConfig,
  UIElement,
  ElementType,
  Position,
} from "../../types/screenConfig";
import { validateManifest } from "../../utils/validateManifest";
import {
  isLegacyManifest,
  getRenderingMode,
} from "../../utils/manifestUtils";

// ── Arbitraries ──────────────────────────────────────────────

const VALID_ACTIONS: ExpectedAction[] = [
  "TAP",
  "TYPE",
  "SELECT",
  "SCAN",
  "VERIFY",
];

const VALID_ELEMENT_TYPES: ElementType[] = [
  "button",
  "input",
  "dropdown",
  "card",
  "tab",
  "text_label",
  "header",
  "navigation_bar",
  "icon",
  "checkbox",
  "scan_input",
];

const arbId = fc.stringMatching(/^[a-z0-9_]{1,15}$/);
const arbNonEmptyString = fc.stringMatching(/^[a-z0-9 ]{1,20}$/);

const arbPosition: fc.Arbitrary<Position> = fc.record({
  x: fc.double({ min: 0, max: 100, noNaN: true }),
  y: fc.double({ min: 0, max: 100, noNaN: true }),
  width: fc.double({ min: 0, max: 100, noNaN: true }),
  height: fc.double({ min: 0, max: 100, noNaN: true }),
});

const arbElement: fc.Arbitrary<UIElement> = fc.record({
  component_id: arbId,
  type: fc.constantFrom(...VALID_ELEMENT_TYPES),
  label: arbNonEmptyString,
  position: arbPosition,
});

function arbScreenConfig(screenId: string): fc.Arbitrary<ScreenConfig> {
  return fc
    .array(arbElement, { minLength: 1, maxLength: 4 })
    .map((elements) => ({
      screen_id: screenId,
      screen_name: `Screen ${screenId}`,
      source: "manual" as const,
      elements: elements.map((el, i) => ({
        ...el,
        component_id: `${screenId}_comp_${i}`,
      })),
    }));
}

/** Generate a valid SimulationStep referencing a given screen and its elements. */
function arbStep(
  stepId: number,
  screenId: string,
  targetComponentId: string,
): fc.Arbitrary<SimulationStep> {
  return fc.record({
    step_id: fc.constant(stepId),
    screen_id: fc.constant(screenId),
    screen: arbNonEmptyString,
    title: arbNonEmptyString,
    instruction: arbNonEmptyString,
    tip: fc.oneof(arbNonEmptyString, fc.constant(null)),
    expected_action: fc.constantFrom(...VALID_ACTIONS),
    expected_value: fc.option(arbNonEmptyString, { nil: undefined }),
    on_wrong_action: arbNonEmptyString,
    target_component_id: fc.constant(targetComponentId),
  });
}

/** Generate a complete valid manifest with N steps. */
function arbManifest(
  numSteps: number,
): fc.Arbitrary<SimulationManifest> {
  const screenIds = Array.from({ length: numSteps }, (_, i) => `screen_${i}`);

  return fc
    .tuple(
      arbId,
      arbNonEmptyString,
      ...screenIds.map((sid) => arbScreenConfig(sid)),
    )
    .chain(([workflowId, workflowName, ...configs]) => {
      const screenConfigs: Record<string, ScreenConfig> = {};
      for (const cfg of configs as ScreenConfig[]) {
        screenConfigs[cfg.screen_id] = cfg;
      }

      const stepArbs = (configs as ScreenConfig[]).map((cfg, i) =>
        arbStep(i + 1, cfg.screen_id, cfg.elements[0].component_id),
      );

      return fc.tuple(...stepArbs).map((steps) => ({
        workflow_id: workflowId as string,
        workflow_name: workflowName as string,
        steps,
        screen_configs: screenConfigs,
        quiz_breaks: [] as never[],
      }));
    });
}

// ── Property Tests ───────────────────────────────────────────

describe("Manifest Property Tests", () => {
  // Feature: simulation-optimization, Property 13: Manifest step completeness
  it("Property 13: every step has all required fields and screen_id maps to screen_configs", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 4 }).chain((n) => arbManifest(n)),
        (manifest) => {
          // Validates: Requirements 7.1, 7.2, 7.3
          for (const step of manifest.steps) {
            expect(typeof step.step_id).toBe("number");
            expect(step.screen_id).toBeTruthy();
            expect(step.title).toBeTruthy();
            expect(step.instruction).toBeTruthy();
            expect(VALID_ACTIONS).toContain(step.expected_action);
            expect(step.on_wrong_action).toBeTruthy();
            expect(step.target_component_id).toBeTruthy();

            // screen_id must map to a key in screen_configs
            expect(manifest.screen_configs).toHaveProperty(step.screen_id);
          }

          // Validation function should accept this manifest
          const result = validateManifest(manifest);
          expect(result.valid).toBe(true);
        },
      ),
      { numRuns: 100 },
    );
  });

  // Feature: simulation-optimization, Property 14: Manifest JSON round-trip
  it("Property 14: JSON.stringify → JSON.parse produces an equivalent manifest", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 3 }).chain((n) => arbManifest(n)),
        (manifest) => {
          // Validates: Requirements 7.5
          const json = JSON.stringify(manifest);
          const parsed = JSON.parse(json) as SimulationManifest;
          expect(parsed).toEqual(manifest);
        },
      ),
      { numRuns: 100 },
    );
  });

  // Feature: simulation-optimization, Property 15: Rendering mode selection
  it("Property 15: correct rendering mode based on screen_configs and screenshot availability", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 3 }).chain((n) => arbManifest(n)),
        (manifest) => {
          // Validates: Requirements 8.1, 8.2, 8.3, 8.4
          for (const step of manifest.steps) {
            const mode = getRenderingMode(step, manifest.screen_configs);

            if (manifest.screen_configs[step.screen_id]) {
              expect(mode).toBe("component");
            } else if (step.screenshot) {
              expect(mode).toBe("screenshot");
            } else {
              expect(mode).toBe("placeholder");
            }
          }
        },
      ),
      { numRuns: 100 },
    );
  });

  // Feature: simulation-optimization, Property 16: Legacy manifest detection
  it("Property 16: manifests with tap_target but no target_component_id are detected as legacy", () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 1, max: 4 }),
        arbNonEmptyString,
        (numSteps, workflowName) => {
          // Validates: Requirements 7.4
          const legacySteps = Array.from({ length: numSteps }, (_, i) => ({
            step_id: i + 1,
            screen_id: `screen_${i}`,
            screen: `Screen ${i}`,
            title: `Step ${i}`,
            instruction: `Do step ${i}`,
            tip: null,
            expected_action: "TAP" as const,
            on_wrong_action: "Wrong!",
            target_component_id: "", // empty — legacy
            tap_target: { x: 10, y: 20, width: 30, height: 40 },
            screenshot: `screen_${i}.png`,
          }));

          const legacyManifest = {
            workflow_id: "wf_legacy",
            workflow_name: workflowName,
            steps: legacySteps,
            screen_configs: {},
            quiz_breaks: [],
          };

          // Should be detected as legacy (tap_target present, no target_component_id)
          expect(isLegacyManifest(legacyManifest)).toBe(true);

          // A new manifest with target_component_id should NOT be legacy
          const newSteps = legacySteps.map((s) => ({
            ...s,
            target_component_id: `comp_${s.step_id}`,
            tap_target: undefined,
          }));
          const newManifest = { ...legacyManifest, steps: newSteps };
          expect(isLegacyManifest(newManifest)).toBe(false);
        },
      ),
      { numRuns: 100 },
    );
  });
});
