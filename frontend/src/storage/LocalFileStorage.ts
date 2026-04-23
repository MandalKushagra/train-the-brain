import type { ScreenConfig } from "../types/screenConfig";
import type { SimulationManifest } from "../types/manifest";
import type { StorageInterface } from "./StorageInterface";
import { NotFoundError, ParseError } from "./StorageInterface";
import { validateScreenConfig } from "../utils/validateScreenConfig";
import { validateManifest } from "../utils/validateManifest";

/**
 * Key-naming convention in localStorage:
 *   Screen config: `sc:{workflowId}:{screenId}`
 *   Screen config index: `sc-index:{workflowId}` (JSON array of screenIds)
 *   Manifest: `manifest:{workflowId}`
 *
 * This is a frontend-friendly "local" implementation.
 * A teammate will swap this with an API-backed implementation later.
 */
export class LocalFileStorage implements StorageInterface {
  private storage: Storage;

  constructor(storage: Storage = localStorage) {
    this.storage = storage;
  }

  // ── helpers ──────────────────────────────────────────────

  private configKey(workflowId: string, screenId: string): string {
    return `sc:${workflowId}:${screenId}`;
  }

  private indexKey(workflowId: string): string {
    return `sc-index:${workflowId}`;
  }

  private manifestKey(workflowId: string): string {
    return `manifest:${workflowId}`;
  }

  private getScreenIds(workflowId: string): string[] {
    const raw = this.storage.getItem(this.indexKey(workflowId));
    if (!raw) return [];
    try {
      const ids = JSON.parse(raw);
      return Array.isArray(ids) ? ids : [];
    } catch {
      return [];
    }
  }

  private setScreenIds(workflowId: string, ids: string[]): void {
    this.storage.setItem(this.indexKey(workflowId), JSON.stringify(ids));
  }

  // ── Screen Config operations ─────────────────────────────

  async saveScreenConfig(workflowId: string, config: ScreenConfig): Promise<void> {
    this.storage.setItem(
      this.configKey(workflowId, config.screen_id),
      JSON.stringify(config),
    );

    const ids = this.getScreenIds(workflowId);
    if (!ids.includes(config.screen_id)) {
      ids.push(config.screen_id);
      this.setScreenIds(workflowId, ids);
    }
  }

  async loadScreenConfig(workflowId: string, screenId: string): Promise<ScreenConfig> {
    const raw = this.storage.getItem(this.configKey(workflowId, screenId));
    if (raw === null) {
      throw new NotFoundError(
        `Screen config not found: workflow=${workflowId}, screen=${screenId}`,
      );
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      throw new ParseError(
        `Failed to parse screen config JSON: workflow=${workflowId}, screen=${screenId}`,
      );
    }

    const result = validateScreenConfig(parsed);
    if (!result.valid) {
      throw new ParseError(
        `Invalid screen config: ${result.errors.map((e) => e.message).join("; ")}`,
      );
    }

    return parsed as ScreenConfig;
  }

  async listScreenConfigs(workflowId: string): Promise<ScreenConfig[]> {
    const ids = this.getScreenIds(workflowId);
    const configs: ScreenConfig[] = [];

    for (const id of ids) {
      try {
        const config = await this.loadScreenConfig(workflowId, id);
        configs.push(config);
      } catch {
        // skip entries that can't be loaded (deleted / corrupt)
      }
    }

    return configs;
  }

  async deleteScreenConfig(workflowId: string, screenId: string): Promise<void> {
    this.storage.removeItem(this.configKey(workflowId, screenId));

    const ids = this.getScreenIds(workflowId);
    const filtered = ids.filter((id) => id !== screenId);
    this.setScreenIds(workflowId, filtered);
  }

  // ── Manifest operations ──────────────────────────────────

  async saveManifest(workflowId: string, manifest: SimulationManifest): Promise<void> {
    this.storage.setItem(this.manifestKey(workflowId), JSON.stringify(manifest));
  }

  async loadManifest(workflowId: string): Promise<SimulationManifest> {
    const raw = this.storage.getItem(this.manifestKey(workflowId));
    if (raw === null) {
      throw new NotFoundError(`Manifest not found: workflow=${workflowId}`);
    }

    let parsed: unknown;
    try {
      parsed = JSON.parse(raw);
    } catch {
      throw new ParseError(`Failed to parse manifest JSON: workflow=${workflowId}`);
    }

    const result = validateManifest(parsed);
    if (!result.valid) {
      throw new ParseError(
        `Invalid manifest: ${result.errors.map((e) => e.message).join("; ")}`,
      );
    }

    return parsed as SimulationManifest;
  }

  async manifestExists(workflowId: string): Promise<boolean> {
    return this.storage.getItem(this.manifestKey(workflowId)) !== null;
  }
}
