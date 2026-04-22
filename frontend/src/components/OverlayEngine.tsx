import React, { useState, useEffect, useCallback, useRef } from "react";
import type { ExpectedAction } from "../types/manifest";
import { matchesExpected } from "./UserInputHandler";
import { wms } from "./sim/wmsTheme";

export interface OverlayEngineProps {
  targetComponentId: string;
  renderMode: "component" | "screenshot";
  expectedAction: ExpectedAction;
  expectedValue?: string;
  pixelFallback?: { x: number; y: number; width: number; height: number };
  onCorrectAction: () => void;
  onWrongAction: (message: string) => void;
  errorMessage: string;
}

/** Retry config for exponential backoff when target not yet rendered */
const RETRY_DELAYS = [100, 200, 400];

interface TargetRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * Queries the DOM for a component by data-component-id and returns its
 * bounding rect relative to the given container.
 */
function findTargetRect(
  targetId: string,
  containerEl: HTMLElement | null,
): TargetRect | null {
  if (!containerEl) return null;
  const el = containerEl.querySelector(
    `[data-component-id="${targetId}"]`,
  ) as HTMLElement | null;
  if (!el) return null;

  const containerRect = containerEl.getBoundingClientRect();
  const targetRect = el.getBoundingClientRect();

  return {
    left: targetRect.left - containerRect.left,
    top: targetRect.top - containerRect.top,
    width: targetRect.width,
    height: targetRect.height,
  };
}

/* ---- CSS keyframe animations injected once ---- */
const STYLE_ID = "overlay-engine-keyframes";
function ensureKeyframes() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    @keyframes oe-pulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(21,101,192,0.5); }
      50% { box-shadow: 0 0 0 8px rgba(21,101,192,0); }
    }
    @keyframes oe-bounce {
      0%, 100% { transform: translate(-50%, -100%) translateY(0); }
      50% { transform: translate(-50%, -100%) translateY(-8px); }
    }
    @keyframes oe-fade-in {
      from { opacity: 0; transform: translateY(-8px); }
      to { opacity: 1; transform: translateY(0); }
    }
  `;
  document.head.appendChild(style);
}

/**
 * OverlayEngine renders training overlays (highlight ring, arrow, error feedback)
 * targeting either a component ID in the DOM or pixel coordinates for legacy mode.
 *
 * - component mode: queries DOM for [data-component-id], positions overlay relative to bounding rect
 * - screenshot mode: uses pixelFallback coordinates
 * - TAP: validates correct component was tapped
 * - TYPE/SELECT/SCAN: delegates to UserInputHandler via onInputSubmit from ComponentRenderer
 * - Fallback: centered overlay when target not found
 * - Retry: exponential backoff (3 attempts, 100ms/200ms/400ms) when target not yet rendered
 */
const OverlayEngine: React.FC<OverlayEngineProps> = ({
  targetComponentId,
  renderMode,
  expectedAction,
  expectedValue,
  pixelFallback,
  onCorrectAction,
  onWrongAction,
  errorMessage,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [targetRect, setTargetRect] = useState<TargetRect | null>(null);
  const [showFallback, setShowFallback] = useState(false);
  const [showError, setShowError] = useState(false);
  const [currentError, setCurrentError] = useState("");
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Inject keyframe animations
  useEffect(() => {
    ensureKeyframes();
  }, []);

  // Find target element with retry + exponential backoff
  useEffect(() => {
    setShowFallback(false);
    setTargetRect(null);
    setShowError(false);

    if (renderMode === "screenshot") {
      // Legacy mode: use pixel fallback directly
      if (pixelFallback) {
        setTargetRect({
          left: pixelFallback.x,
          top: pixelFallback.y,
          width: pixelFallback.width,
          height: pixelFallback.height,
        });
      } else {
        setShowFallback(true);
      }
      return;
    }

    // Component mode: query DOM with retry
    let attempt = 0;
    let cancelled = false;

    function tryFind() {
      if (cancelled) return;
      const parent = containerRef.current?.parentElement ?? document.body;
      const rect = findTargetRect(targetComponentId, parent);
      if (rect) {
        setTargetRect(rect);
        setShowFallback(false);
      } else if (attempt < RETRY_DELAYS.length) {
        setTimeout(tryFind, RETRY_DELAYS[attempt]);
        attempt++;
      } else {
        setShowFallback(true);
      }
    }

    tryFind();
    return () => {
      cancelled = true;
    };
  }, [targetComponentId, renderMode, pixelFallback]);

  // Show error feedback for 2.5s then auto-dismiss
  const showErrorFeedback = useCallback((msg: string) => {
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    setCurrentError(msg);
    setShowError(true);
    errorTimerRef.current = setTimeout(() => {
      setShowError(false);
      setCurrentError("");
    }, 2500);
  }, []);

  // Handle tap on the overlay area (for TAP actions)
  const handleOverlayClick = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      if (expectedAction === "TAP") {
        onCorrectAction();
      }
    },
    [expectedAction, onCorrectAction],
  );

  // Handle tap on wrong area
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      // Only handle if clicking the backdrop itself, not the target overlay
      if (e.target === e.currentTarget) {
        if (expectedAction === "TAP") {
          showErrorFeedback(errorMessage);
          onWrongAction(errorMessage);
        }
      }
    },
    [expectedAction, errorMessage, onWrongAction, showErrorFeedback],
  );

  // Listen for input submissions from ComponentRenderer (for TYPE/SELECT/SCAN)
  useEffect(() => {
    if (
      expectedAction !== "TYPE" &&
      expectedAction !== "SELECT" &&
      expectedAction !== "SCAN"
    )
      return;
    if (!expectedValue) return;

    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        componentId: string;
        value: string;
      };
      if (detail.componentId !== targetComponentId) return;

      const isCorrect = matchesExpected(
        expectedAction,
        detail.value,
        expectedValue,
      );
      if (isCorrect) {
        onCorrectAction();
      } else {
        showErrorFeedback(errorMessage);
        onWrongAction(errorMessage);
      }
    };

    document.addEventListener("sim-input-submit", handler);
    return () => document.removeEventListener("sim-input-submit", handler);
  }, [
    expectedAction,
    expectedValue,
    targetComponentId,
    onCorrectAction,
    onWrongAction,
    errorMessage,
    showErrorFeedback,
  ]);

  // Cleanup error timer on unmount
  useEffect(() => {
    return () => {
      if (errorTimerRef.current) clearTimeout(errorTimerRef.current);
    };
  }, []);

  // Determine positioning mode
  const isPercentage = renderMode === "screenshot" && pixelFallback != null;

  // Render fallback overlay (centered) when target not found
  if (showFallback) {
    return (
      <div ref={containerRef} data-testid="overlay-engine">
        <div
          onClick={handleBackdropClick}
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 900,
          }}
        >
          <div
            data-testid="overlay-fallback"
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              transform: "translate(-50%, -50%)",
              backgroundColor: wms.colors.white,
              border: `2px solid ${wms.colors.warning}`,
              borderRadius: wms.radii.xl,
              padding: wms.spacing.xl,
              fontFamily: wms.fonts.family,
              fontSize: wms.fonts.sizeMd,
              color: wms.colors.text,
              textAlign: "center",
              zIndex: 910,
              boxShadow: wms.colors.cardShadow,
            }}
          >
            ⚠️ Target element not found
          </div>
        </div>
        {showError && (
          <ErrorToast message={currentError} />
        )}
      </div>
    );
  }

  if (!targetRect) return <div ref={containerRef} data-testid="overlay-engine" />;

  const highlightStyle: React.CSSProperties = isPercentage
    ? {
        position: "absolute",
        left: `${targetRect.left}%`,
        top: `${targetRect.top}%`,
        width: `${targetRect.width}%`,
        height: `${targetRect.height}%`,
      }
    : {
        position: "absolute",
        left: `${targetRect.left}px`,
        top: `${targetRect.top}px`,
        width: `${targetRect.width}px`,
        height: `${targetRect.height}px`,
      };

  // Arrow position: centered above the target
  const arrowStyle: React.CSSProperties = isPercentage
    ? {
        position: "absolute",
        left: `${targetRect.left + targetRect.width / 2}%`,
        top: `${targetRect.top}%`,
        transform: "translate(-50%, -100%)",
        animation: "oe-bounce 1s ease-in-out infinite",
      }
    : {
        position: "absolute",
        left: `${targetRect.left + targetRect.width / 2}px`,
        top: `${targetRect.top}px`,
        transform: "translate(-50%, -100%)",
        animation: "oe-bounce 1s ease-in-out infinite",
      };

  return (
    <div ref={containerRef} data-testid="overlay-engine">
      {/* Transparent backdrop to catch wrong taps */}
      <div
        data-testid="overlay-backdrop"
        onClick={handleBackdropClick}
        style={{
          position: "absolute",
          inset: 0,
          zIndex: 900,
          pointerEvents: expectedAction === "TAP" ? "auto" : "none",
        }}
      />

      {/* Pulsing highlight ring */}
      <div
        data-testid="overlay-highlight"
        onClick={handleOverlayClick}
        style={{
          ...highlightStyle,
          border: `2px solid ${wms.colors.primary}`,
          borderRadius: wms.radii.lg,
          animation: "oe-pulse 1.5s ease-in-out infinite",
          zIndex: 910,
          pointerEvents: expectedAction === "TAP" ? "auto" : "none",
          cursor: expectedAction === "TAP" ? "pointer" : "default",
          boxSizing: "border-box",
        }}
      />

      {/* Animated arrow pointing to target */}
      <div data-testid="overlay-arrow" style={{ ...arrowStyle, zIndex: 920, pointerEvents: "none" }}>
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none">
          <path
            d="M12 4v12m0 0l-4-4m4 4l4-4"
            stroke={wms.colors.primary}
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* Error feedback toast */}
      {showError && (
        <ErrorToast message={currentError} />
      )}
    </div>
  );
};

/** Error toast displayed for 2.5s on wrong action */
const ErrorToast: React.FC<{ message: string }> = ({ message }) => (
  <div
    data-testid="overlay-error"
    style={{
      position: "absolute",
      top: "8px",
      left: "8px",
      right: "8px",
      backgroundColor: wms.colors.error,
      color: wms.colors.white,
      padding: `${wms.spacing.md} ${wms.spacing.lg}`,
      borderRadius: wms.radii.lg,
      fontFamily: wms.fonts.family,
      fontSize: wms.fonts.sizeMd,
      fontWeight: wms.fonts.weightMedium,
      zIndex: 950,
      textAlign: "center",
      boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
      animation: "oe-fade-in 0.2s ease-out",
    }}
  >
    ❌ {message}
  </div>
);

export default OverlayEngine;
