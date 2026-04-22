import React from "react";
import { wms } from "./sim/wmsTheme";

export interface PlaceholderScreenProps {
  screenName: string;
}

/**
 * Placeholder screen displayed when neither a ScreenConfig nor a screenshot
 * is available for a given step. Shows the screen name and a "not configured" message.
 */
const PlaceholderScreen: React.FC<PlaceholderScreenProps> = ({
  screenName,
}) => {
  return (
    <div
      data-testid="placeholder-screen"
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: wms.colors.background,
        fontFamily: wms.fonts.family,
        gap: wms.spacing.lg,
      }}
    >
      <span style={{ fontSize: "48px", opacity: 0.5 }}>📱</span>
      <p
        style={{
          fontSize: wms.fonts.sizeXl,
          fontWeight: wms.fonts.weightMedium,
          color: wms.colors.text,
          margin: 0,
        }}
      >
        {screenName}
      </p>
      <p
        style={{
          fontSize: wms.fonts.sizeMd,
          color: wms.colors.textSecondary,
          margin: 0,
        }}
      >
        Screen not configured
      </p>
    </div>
  );
};

export default PlaceholderScreen;
