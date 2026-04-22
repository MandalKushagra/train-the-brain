import React, { useState, useEffect } from "react";
import { wms } from "./sim/wmsTheme";

export interface FloatingTipWidgetProps {
  tipText: string | null; // null = no tip for this step, widget hidden
  isVisible: boolean;
}

/* ---- CSS keyframe animations injected once ---- */
const STYLE_ID = "floating-tip-keyframes";
function ensureKeyframes() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    @keyframes ftw-entrance {
      from { opacity: 0; transform: scale(0.6); }
      to { opacity: 1; transform: scale(1); }
    }
    @keyframes ftw-slide-up {
      from { transform: translateY(100%); }
      to { transform: translateY(0); }
    }
    @keyframes ftw-fade-in {
      from { opacity: 0; }
      to { opacity: 1; }
    }
  `;
  document.head.appendChild(style);
}

/**
 * Floating lightbulb button anchored to bottom-right.
 * On tap: opens a bottom sheet with tip text and "OKAY" dismiss button.
 * Hidden when tipText is null.
 * Entrance animation when a new step loads with a tip.
 */
const FloatingTipWidget: React.FC<FloatingTipWidgetProps> = ({
  tipText,
  isVisible,
}) => {
  const [sheetOpen, setSheetOpen] = useState(false);
  const [animKey, setAnimKey] = useState(0);

  useEffect(() => {
    ensureKeyframes();
  }, []);

  // Reset sheet and trigger entrance animation when tip changes
  useEffect(() => {
    setSheetOpen(false);
    setAnimKey((k) => k + 1);
  }, [tipText]);

  // Don't render if no tip or not visible
  if (!tipText || !isVisible) return null;

  return (
    <>
      {/* Floating lightbulb button */}
      <button
        key={animKey}
        data-testid="tip-widget-button"
        onClick={() => setSheetOpen(true)}
        aria-label="Show tip"
        style={{
          position: "absolute",
          bottom: "16px",
          right: "16px",
          width: "48px",
          height: "48px",
          borderRadius: "50%",
          backgroundColor: wms.colors.warning,
          border: "none",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "24px",
          boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
          zIndex: 800,
          animation: "ftw-entrance 0.3s ease-out",
        }}
      >
        💡
      </button>

      {/* Bottom sheet backdrop + sheet */}
      {sheetOpen && (
        <div
          data-testid="tip-backdrop"
          onClick={() => setSheetOpen(false)}
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.4)",
            zIndex: 850,
            animation: "ftw-fade-in 0.2s ease-out",
          }}
        >
          <div
            data-testid="tip-bottom-sheet"
            onClick={(e) => e.stopPropagation()}
            style={{
              position: "absolute",
              bottom: 0,
              left: 0,
              right: 0,
              backgroundColor: wms.colors.white,
              borderTopLeftRadius: wms.radii.xl,
              borderTopRightRadius: wms.radii.xl,
              padding: wms.spacing.xl,
              paddingBottom: "24px",
              animation: "ftw-slide-up 0.3s ease-out",
              boxShadow: "0 -4px 20px rgba(0,0,0,0.15)",
            }}
          >
            {/* Drag handle */}
            <div
              style={{
                width: "40px",
                height: "4px",
                backgroundColor: wms.colors.border,
                borderRadius: "2px",
                margin: "0 auto 12px",
              }}
            />

            {/* Tip icon + text */}
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: wms.spacing.md,
                marginBottom: wms.spacing.xl,
              }}
            >
              <span style={{ fontSize: "20px", flexShrink: 0 }}>💡</span>
              <p
                data-testid="tip-text"
                style={{
                  fontFamily: wms.fonts.family,
                  fontSize: wms.fonts.sizeLg,
                  color: wms.colors.text,
                  lineHeight: 1.5,
                  margin: 0,
                }}
              >
                {tipText}
              </p>
            </div>

            {/* OKAY dismiss button */}
            <button
              data-testid="tip-okay-button"
              onClick={() => setSheetOpen(false)}
              style={{
                width: "100%",
                padding: `${wms.spacing.lg} ${wms.spacing.xl}`,
                backgroundColor: wms.colors.primary,
                color: wms.colors.white,
                border: "none",
                borderRadius: wms.radii.lg,
                fontFamily: wms.fonts.family,
                fontSize: wms.fonts.sizeLg,
                fontWeight: wms.fonts.weightBold,
                cursor: "pointer",
                letterSpacing: "0.5px",
              }}
            >
              OKAY
            </button>
          </div>
        </div>
      )}
    </>
  );
};

export default FloatingTipWidget;
