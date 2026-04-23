/**
 * Unit tests for UserInputHandler and matchesExpected utility.
 */
import { describe, it, expect } from "vitest";
import { matchesExpected } from "../components/UserInputHandler";

describe("matchesExpected", () => {
  describe("TYPE action", () => {
    it("returns true for exact match", () => {
      expect(matchesExpected("TYPE", "hello", "hello")).toBe(true);
    });

    it("returns true for case-insensitive match", () => {
      expect(matchesExpected("TYPE", "Hello", "hello")).toBe(true);
      expect(matchesExpected("TYPE", "HELLO", "hello")).toBe(true);
    });

    it("returns true when input has leading/trailing whitespace", () => {
      expect(matchesExpected("TYPE", "  hello  ", "hello")).toBe(true);
    });

    it("returns false for incorrect input", () => {
      expect(matchesExpected("TYPE", "world", "hello")).toBe(false);
    });

    it("returns false for partial match", () => {
      expect(matchesExpected("TYPE", "hel", "hello")).toBe(false);
    });
  });

  describe("SELECT action", () => {
    it("returns true for exact match", () => {
      expect(matchesExpected("SELECT", "Option A", "Option A")).toBe(true);
    });

    it("returns true for case-insensitive match", () => {
      expect(matchesExpected("SELECT", "option a", "Option A")).toBe(true);
    });

    it("returns false for wrong selection", () => {
      expect(matchesExpected("SELECT", "Option B", "Option A")).toBe(false);
    });
  });

  describe("SCAN action", () => {
    it("returns true for matching barcode value", () => {
      expect(matchesExpected("SCAN", "ABC123", "ABC123")).toBe(true);
    });

    it("returns true for case-insensitive barcode match", () => {
      expect(matchesExpected("SCAN", "abc123", "ABC123")).toBe(true);
    });

    it("returns false for wrong barcode", () => {
      expect(matchesExpected("SCAN", "XYZ789", "ABC123")).toBe(false);
    });
  });

  describe("unsupported actions", () => {
    it("returns false for TAP action", () => {
      expect(matchesExpected("TAP", "anything", "anything")).toBe(false);
    });

    it("returns false for VERIFY action", () => {
      expect(matchesExpected("VERIFY", "anything", "anything")).toBe(false);
    });
  });
});
