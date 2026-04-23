import type { ScreenConfig } from "./screenConfig";

export type ExpectedAction = "TAP" | "TYPE" | "SELECT" | "SCAN" | "VERIFY";

export interface SimulationStep {
  step_id: number;
  screen_id: string;
  screen: string;
  title: string;
  instruction: string;
  tip: string | null;
  expected_action: ExpectedAction;
  expected_value?: string;
  on_wrong_action: string;
  target_component_id: string;

  // Legacy fields for backward compatibility (legacy manifests only)
  screenshot?: string;
  tap_target?: { x: number; y: number; width: number; height: number };
}

export interface QuizBreak {
  after_step: number;
  questions: {
    question: string;
    options: string[];
    correct: number;
  }[];
}

export interface GoldenManifestMetadata {
  created_at: string; // ISO timestamp
  last_modified_at: string; // ISO timestamp
  generated_by: "ai_pipeline";
  is_edited: boolean;
}

export interface SimulationManifest {
  workflow_id: string;
  workflow_name: string;
  steps: SimulationStep[];
  screen_configs: Record<string, ScreenConfig>;
  quiz_breaks: QuizBreak[];
  golden_metadata?: GoldenManifestMetadata;
}
