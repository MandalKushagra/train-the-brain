/**
 * Property-based tests for Screen Config using fast-check.
 *
 * Feature: simulation-optimization
 */
import { describe, it, expect } from "vitest";
import * as fc from "fast-check";
import type {
  ScreenConfig,
  UIElement,
  ElementType,
  Position,
} from "../../types/screenConfig";
import {
  validateScreenConfig,
} from "../../utils/validateScreenConfig";

// ── Arbitraries ──────────────────────────────────────────────

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

const VALID_SOURCES = ["vision_ai", "manual"] as const;

/** Arbitrary for a valid Position with values in [0, 100]. */
const arbPosition: fc.Arbitrary<Position> = fc.record({
  x: fc.double({ min: 0, max: 100, noNaN: true }),
  y: fc.double({ min: 0, max: 100, noNaN: true }),
  width: fc.double({ min: 0, max: 100, noNaN: true }),
  height: fc.double({ min: 0, max: 100, noNaN: true }),
});

/** Arbitrary for a non-empty alphanumeric string (for IDs/labels). */
const arbNonEmptyString = fc.stringMatching(/^[a-z0-9_]{1,20}$/);

/** Arbitrary for a valid UIElement (leaf — no children). */
const arbLeafElement: fc.Arbitrary<UIElement> = fc.record({
  component_id: arbNonEmptyString,
  type: fc.constantFrom(...VALID_ELEMENT_TYPES),
  label: arbNonEmptyString,
  position: arbPosition,
  needs_review: fc.boolean(),
});

/** Arbitrary for a UIElement with optional children (1 level deep). */
const arbElement: fc.Arbitrary<UIElement> = fc.record({
  component_id: arbNonEmptyString,
  type: fc.constantFrom(...VALID_ELEMENT_TYPES),
  label: arbNonEmptyString,
  position: arbPosition,
  needs_review: fc.boolean(),
  children: fc.array(arbLeafElement, { minLength: 0, maxLength: 3 }),
});

/** Arbitrary for a valid ScreenConfig. */
const arbScreenConfig: fc.Arbitrary<ScreenConfig> = fc.record({
  screen_id: arbNonEmptyString,
  screen_name: arbNonEmptyString,
  source: fc.constantFrom(...VALID_SOURCES),
  elements: fc.array(arbElement, { minLength: 0, maxLength: 5 }),
});

// ── Property Tests ───────────────────────────────────────────

describe("Screen Config Property Tests", () => {
  // Feature: simulation-optimization, Property 1: Screen Config schema completeness
  it("Property 1: every valid ScreenConfig has all required fields and positions in [0,100]", () => {
    fc.assert(
      fc.property(arbScreenConfig, (config) => {
        // Validates: Requirements 1.3, 2.1, 2.2, 2.5

        // Top-level required fields
        expect(config.screen_id).toBeTruthy();
        expect(typeof config.screen_id).toBe("string");
        expect(config.screen_name).toBeTruthy();
        expect(typeof config.screen_name).toBe("string");
        expect(VALID_SOURCES).toContain(config.source);
        expect(Array.isArray(config.elements)).toBe(true);

        // Each element has required fields
        function checkElement(el: UIElement) {
          expect(el.component_id).toBeTruthy();
          expect(typeof el.component_id).toBe("string");
          expect(VALID_ELEMENT_TYPES).toContain(el.type);
          expect(typeof el.label).toBe("string");
          expect(el.position.x).toBeGreaterThanOrEqual(0);
          expect(el.position.x).toBeLessThanOrEqual(100);
          expect(el.position.y).toBeGreaterThanOrEqual(0);
          expect(el.position.y).toBeLessThanOrEqual(100);
          expect(el.position.width).toBeGreaterThanOrEqual(0);
          expect(el.position.width).toBeLessThanOrEqual(100);
          expect(el.position.height).toBeGreaterThanOrEqual(0);
          expect(el.position.height).toBeLessThanOrEqual(100);
          if (el.children) {
            el.children.forEach(checkElement);
          }
        }

        config.elements.forEach(checkElement);

        // Validation function should accept this config
        const result = validateScreenConfig(config);
        expect(result.valid).toBe(true);
        expect(result.errors).toHaveLength(0);
      }),
      { numRuns: 100 },
    );
  });

  // Feature: simulation-optimization, Property 2: Screen Config JSON round-trip
  it("Property 2: JSON.stringify → JSON.parse produces an equivalent ScreenConfig", () => {
    fc.assert(
      fc.property(arbScreenConfig, (config) => {
        // Validates: Requirements 2.3, 2.4
        const json = JSON.stringify(config);
        const parsed = JSON.parse(json) as ScreenConfig;

        expect(parsed).toEqual(config);
      }),
      { numRuns: 100 },
    );
  });

  // Feature: simulation-optimization, Property 3: Screen Config validation rejects incomplete configs
  it("Property 3: configs with missing required fields are rejected", () => {
    const requiredElementFields = ["component_id", "type", "position"] as const;

    fc.assert(
      fc.property(
        arbScreenConfig.filter((c) => c.elements.length > 0),
        fc.constantFrom(...requiredElementFields),
        fc.nat({ max: 100 }),
        (config, fieldToRemove, seed) => {
          // Validates: Requirements 3.4

          // Pick an element to corrupt
          const elementIndex = seed % config.elements.length;
          const corrupted = JSON.parse(JSON.stringify(config));
          delete corrupted.elements[elementIndex][fieldToRemove];

          const result = validateScreenConfig(corrupted);
          expect(result.valid).toBe(false);
          expect(result.errors.length).toBeGreaterThan(0);
        },
      ),
      { numRuns: 100 },
    );
  });
});
