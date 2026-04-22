import React from "react";
import { wms } from "./wmsTheme";

interface SimCardProps {
  label: string;
}

const SimCard: React.FC<SimCardProps> = ({ label }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: wms.colors.surface,
        border: `1px solid ${wms.colors.border}`,
        borderRadius: wms.radii.lg,
        boxShadow: wms.colors.cardShadow,
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeMd,
        color: wms.colors.text,
        padding: wms.spacing.md,
        boxSizing: "border-box",
        overflow: "hidden",
      }}
    >
      {label}
    </div>
  );
};

export default SimCard;
