import type { ScreenConfig } from "../types/screenConfig";

export interface ValidationError {
  path: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

const VALID_ELEMENT_TYPES = [
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
] as const;

const VALID_SOURCES = ["vision_ai", "manual"] as const;

function isInRange(value: unknown, min: number, max: number): boolean {
  return typeof value === "number" && value >= min && value <= max;
}

function validateElement(
  element: Record<string, unknown>,
  path: string,
  errors: ValidationError[]
): void {
  if (!element.component_id || typeof element.component_id !== "string") {
    errors.push({ path: `${path}.component_id`, message: "component_id is required and must be a string" });
  }

  if (!element.type || typeof element.type !== "string") {
    errors.push({ path: `${path}.type`, message: "type is required and must be a string" });
  } else if (!VALID_ELEMENT_TYPES.includes(element.type as typeof VALID_ELEMENT_TYPES[number])) {
    errors.push({ path: `${path}.type`, message: `type must be one of: ${VALID_ELEMENT_TYPES.join(", ")}` });
  }

  if (!element.position || typeof element.position !== "object") {
    errors.push({ path: `${path}.position`, message: "position is required and must be an object" });
  } else {
    const pos = element.position as Record<string, unknown>;
    for (const field of ["x", "y", "width", "height"] as const) {
      if (!isInRange(pos[field], 0, 100)) {
        errors.push({
          path: `${path}.position.${field}`,
          message: `${field} is required and must be a number between 0 and 100`,
        });
      }
    }
  }

  if (Array.isArray(element.children)) {
    (element.children as Record<string, unknown>[]).forEach((child, i) => {
      validateElement(child, `${path}.children[${i}]`, errors);
    });
  }
}

export function validateScreenConfig(config: unknown): ValidationResult {
  const errors: ValidationError[] = [];

  if (!config || typeof config !== "object") {
    return { valid: false, errors: [{ path: "", message: "config must be an object" }] };
  }

  const c = config as Record<string, unknown>;

  if (!c.screen_id || typeof c.screen_id !== "string") {
    errors.push({ path: "screen_id", message: "screen_id is required and must be a string" });
  }

  if (!c.screen_name || typeof c.screen_name !== "string") {
    errors.push({ path: "screen_name", message: "screen_name is required and must be a string" });
  }

  if (!c.source || !VALID_SOURCES.includes(c.source as typeof VALID_SOURCES[number])) {
    errors.push({ path: "source", message: 'source is required and must be "vision_ai" or "manual"' });
  }

  if (!Array.isArray(c.elements)) {
    errors.push({ path: "elements", message: "elements is required and must be an array" });
  } else {
    (c.elements as Record<string, unknown>[]).forEach((el, i) => {
      validateElement(el, `elements[${i}]`, errors);
    });
  }

  return { valid: errors.length === 0, errors };
}

/**
 * Type guard that validates and narrows unknown data to ScreenConfig.
 */
export function isValidScreenConfig(config: unknown): config is ScreenConfig {
  return validateScreenConfig(config).valid;
}
