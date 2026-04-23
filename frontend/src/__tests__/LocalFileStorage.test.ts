/**
 * Unit tests for LocalFileStorage (localStorage-based implementation).
 */
import { describe, it, expect, beforeEach } from "vitest";
import { LocalFileStorage } from "../storage/LocalFileStorage";
import { NotFoundError, ParseError } from "../storage/StorageInterface";
import type { ScreenConfig } from "../types/screenConfig";
import type { SimulationManifest } from "../types/manifest";

/** Simple in-memory Storage mock that implements the Web Storage API. */
class MockStorage implements Storage {
  private store: Record<string, string> = {};
  get length() {
    return Object.keys(this.store).length;
  }
  clear() {
    this.store = {};
  }
  getItem(key: string) {
    return this.store[key] ?? null;
  }
  key(index: number) {
    return Object.keys(this.store)[index] ?? null;
  }
  removeItem(key: string) {
    delete this.store[key];
  }
  setItem(key: string, value: string) {
    this.store[key] = value;
  }
}

const sampleConfig: ScreenConfig = {
  screen_id: "login",
  screen_name: "Login Screen",
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

const sampleManifest: SimulationManifest = {
  workflow_id: "wf_001",
  workflow_name: "Test Workflow",
  steps: [
    {
      step_id: 1,
      screen_id: "login",
      screen: "Login Screen",
      title: "Tap Login",
      instruction: "Tap the login button",
      tip: null,
      expected_action: "TAP",
      on_wrong_action: "Wrong element!",
      target_component_id: "btn_login",
    },
  ],
  screen_configs: {
    login: sampleConfig,
  },
  quiz_breaks: [],
};

describe("LocalFileStorage", () => {
  let storage: LocalFileStorage;
  let mockStorage: MockStorage;

  beforeEach(() => {
    mockStorage = new MockStorage();
    storage = new LocalFileStorage(mockStorage);
  });

  describe("Screen Config operations", () => {
    it("save and load round-trip", async () => {
      await storage.saveScreenConfig("wf_001", sampleConfig);
      const loaded = await storage.loadScreenConfig("wf_001", "login");
      expect(loaded).toEqual(sampleConfig);
    });

    it("throws NotFoundError when loading non-existent config", async () => {
      await expect(
        storage.loadScreenConfig("wf_001", "nonexistent"),
      ).rejects.toThrow(NotFoundError);
    });

    it("lists saved configs", async () => {
      await storage.saveScreenConfig("wf_001", sampleConfig);
      const configs = await storage.listScreenConfigs("wf_001");
      expect(configs).toHaveLength(1);
      expect(configs[0].screen_id).toBe("login");
    });

    it("returns empty list for workflow with no configs", async () => {
      const configs = await storage.listScreenConfigs("wf_empty");
      expect(configs).toHaveLength(0);
    });

    it("deletes a config", async () => {
      await storage.saveScreenConfig("wf_001", sampleConfig);
      await storage.deleteScreenConfig("wf_001", "login");
      await expect(
        storage.loadScreenConfig("wf_001", "login"),
      ).rejects.toThrow(NotFoundError);
    });
  });

  describe("Manifest operations", () => {
    it("save and load round-trip", async () => {
      await storage.saveManifest("wf_001", sampleManifest);
      const loaded = await storage.loadManifest("wf_001");
      expect(loaded).toEqual(sampleManifest);
    });

    it("throws NotFoundError when loading non-existent manifest", async () => {
      await expect(storage.loadManifest("wf_missing")).rejects.toThrow(
        NotFoundError,
      );
    });

    it("manifestExists returns true after save", async () => {
      await storage.saveManifest("wf_001", sampleManifest);
      expect(await storage.manifestExists("wf_001")).toBe(true);
    });

    it("manifestExists returns false when not saved", async () => {
      expect(await storage.manifestExists("wf_missing")).toBe(false);
    });
  });

  describe("Error handling", () => {
    it("throws ParseError for corrupted JSON in config", async () => {
      // Manually inject invalid JSON
      mockStorage.setItem("sc:wf_001:bad", "not valid json{{{");
      mockStorage.setItem("sc-index:wf_001", '["bad"]');

      await expect(
        storage.loadScreenConfig("wf_001", "bad"),
      ).rejects.toThrow(ParseError);
    });

    it("throws ParseError for corrupted JSON in manifest", async () => {
      mockStorage.setItem("manifest:wf_001", "broken json!!!");

      await expect(storage.loadManifest("wf_001")).rejects.toThrow(ParseError);
    });
  });
});
