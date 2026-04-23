import type { ScreenConfig } from "../types/screenConfig";
import type { SimulationManifest } from "../types/manifest";

/** Thrown when a requested resource is not found in storage. */
export class NotFoundError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "NotFoundError";
  }
}

/** Thrown when stored data cannot be parsed or fails validation. */
export class ParseError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ParseError";
  }
}

/**
 * Abstract storage interface for Screen Configs and Simulation Manifests.
 * Local implementation uses localStorage; a teammate will swap this with
 * an API-backed implementation behind the same interface.
 */
export interface StorageInterface {
  // Screen Config operations
  saveScreenConfig(workflowId: string, config: ScreenConfig): Promise<void>;
  loadScreenConfig(workflowId: string, screenId: string): Promise<ScreenConfig>;
  listScreenConfigs(workflowId: string): Promise<ScreenConfig[]>;
  deleteScreenConfig(workflowId: string, screenId: string): Promise<void>;

  // Manifest operations (golden copy aware)
  saveManifest(workflowId: string, manifest: SimulationManifest): Promise<void>;
  loadManifest(workflowId: string): Promise<SimulationManifest>;
  manifestExists(workflowId: string): Promise<boolean>;
}
