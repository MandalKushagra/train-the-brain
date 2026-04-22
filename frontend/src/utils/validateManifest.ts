import type { SimulationManifest } from "../types/manifest";

export interface ValidationError {
  path: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

const VALID_ACTIONS = ["TAP", "TYPE", "SELECT", "SCAN", "VERIFY"] as const;

function validateStep(
  step: Record<string, unknown>,
  path: string,
  errors: ValidationError[]
): void {
  if (typeof step.step_id !== "number") {
    errors.push({ path: `${path}.step_id`, message: "step_id is required and must be a number" });
  }

  if (!step.screen_id || typeof step.screen_id !== "string") {
    errors.push({ path: `${path}.screen_id`, message: "screen_id is required and must be a string" });
  }

  if (!step.title || typeof step.title !== "string") {
    errors.push({ path: `${path}.title`, message: "title is required and must be a string" });
  }

  if (!step.instruction || typeof step.instruction !== "string") {
    errors.push({ path: `${path}.instruction`, message: "instruction is required and must be a string" });
  }

  if (!step.expected_action || typeof step.expected_action !== "string") {
    errors.push({ path: `${path}.expected_action`, message: "expected_action is required and must be a string" });
  } else if (!VALID_ACTIONS.includes(step.expected_action as typeof VALID_ACTIONS[number])) {
    errors.push({
      path: `${path}.expected_action`,
      message: `expected_action must be one of: ${VALID_ACTIONS.join(", ")}`,
    });
  }

  if (!step.on_wrong_action || typeof step.on_wrong_action !== "string") {
    errors.push({ path: `${path}.on_wrong_action`, message: "on_wrong_action is required and must be a string" });
  }

  if (!step.target_component_id || typeof step.target_component_id !== "string") {
    errors.push({
      path: `${path}.target_component_id`,
      message: "target_component_id is required and must be a string",
    });
  }
}

export function validateManifest(manifest: unknown): ValidationResult {
  const errors: ValidationError[] = [];

  if (!manifest || typeof manifest !== "object") {
    return { valid: false, errors: [{ path: "", message: "manifest must be an object" }] };
  }

  const m = manifest as Record<string, unknown>;

  if (!m.workflow_id || typeof m.workflow_id !== "string") {
    errors.push({ path: "workflow_id", message: "workflow_id is required and must be a string" });
  }

  if (!m.workflow_name || typeof m.workflow_name !== "string") {
    errors.push({ path: "workflow_name", message: "workflow_name is required and must be a string" });
  }

  if (!Array.isArray(m.steps)) {
    errors.push({ path: "steps", message: "steps is required and must be an array" });
  } else {
    (m.steps as Record<string, unknown>[]).forEach((step, i) => {
      validateStep(step, `steps[${i}]`, errors);
    });
  }

  if (!m.screen_configs || typeof m.screen_configs !== "object" || Array.isArray(m.screen_configs)) {
    errors.push({ path: "screen_configs", message: "screen_configs is required and must be an object" });
  }

  if (!Array.isArray(m.quiz_breaks)) {
    errors.push({ path: "quiz_breaks", message: "quiz_breaks is required and must be an array" });
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Type guard that validates and narrows unknown data to SimulationManifest.
 */
export function isValidManifest(manifest: unknown): manifest is SimulationManifest {
  return validateManifest(manifest).valid;
}
