import type { SimulationStep } from "../types/manifest";
import type { ScreenConfig } from "../types/screenConfig";

/**
 * Detects whether a manifest is a legacy (pixel-based) format.
 * Legacy manifests have steps with tap_target but no target_component_id.
 */
export function isLegacyManifest(manifest: {
  steps?: Array<Record<string, unknown>>;
}): boolean {
  if (!manifest.steps || !Array.isArray(manifest.steps)) return false;
  return manifest.steps.some(
    (s) => s.tap_target != null && !s.target_component_id,
  );
}

/**
 * Rendering mode for a given step:
 * - "component": render from ScreenConfig using dynamic components (new manifests)
 * - "screenshot": render from screenshot image (legacy manifests)
 * - "placeholder": neither screen_config nor screenshot available
 */
export type RenderingMode = "component" | "screenshot" | "placeholder";

/**
 * Determines the rendering mode for a given step.
 *
 * - If screenConfigs contains the step's screen_id → "component"
 * - If screenConfigs does not contain screen_id but step has a screenshot → "screenshot"
 * - If neither → "placeholder"
 */
export function getRenderingMode(
  step: SimulationStep,
  screenConfigs: Record<string, ScreenConfig>,
): RenderingMode {
  if (screenConfigs[step.screen_id]) {
    return "component";
  }
  if (step.screenshot) {
    return "screenshot";
  }
  return "placeholder";
}
