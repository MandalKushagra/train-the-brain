import React from "react";
import { wms } from "./wmsTheme";

interface SimButtonProps {
  label: string;
  isActive: boolean;
  onClick?: () => void;
}

const SimButton: React.FC<SimButtonProps> = ({ label, isActive, onClick }) => {
  return (
    <button
      onClick={isActive ? onClick : undefined}
      disabled={!isActive}
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: isActive ? wms.colors.primary : wms.colors.disabled,
        color: isActive ? wms.colors.white : wms.colors.textDisabled,
        border: `1px solid ${isActive ? wms.colors.primaryDark : wms.colors.disabledBorder}`,
        borderRadius: wms.radii.md,
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeMd,
        fontWeight: wms.fonts.weightMedium,
        cursor: isActive ? "pointer" : "default",
        padding: `${wms.spacing.sm} ${wms.spacing.md}`,
        boxSizing: "border-box",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </button>
  );
};

export default SimButton;
