export interface Position {
  x: number; // percentage 0-100
  y: number; // percentage 0-100
  width: number; // percentage 0-100
  height: number; // percentage 0-100
}

export type ElementType =
  | "button"
  | "input"
  | "dropdown"
  | "card"
  | "tab"
  | "text_label"
  | "header"
  | "navigation_bar"
  | "icon"
  | "checkbox"
  | "scan_input";

export interface UIElement {
  component_id: string;
  type: ElementType;
  label: string;
  position: Position;
  needs_review?: boolean;
  children?: UIElement[];
}

export interface ScreenConfigMetadata {
  source_screenshot_path?: string;
  extraction_confidence?: number;
}

export interface ScreenConfig {
  screen_id: string;
  screen_name: string;
  source: "vision_ai" | "manual";
  elements: UIElement[];
  metadata?: ScreenConfigMetadata;
}
