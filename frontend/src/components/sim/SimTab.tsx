import React from "react";
import { wms } from "./wmsTheme";

interface SimTabProps {
  label: string;
  isActive: boolean;
  onClick?: () => void;
}

const SimTab: React.FC<SimTabProps> = ({ label, isActive, onClick }) => {
  return (
    <div
      onClick={isActive ? onClick : undefined}
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: wms.colors.white,
        borderBottom: `2px solid ${isActive ? wms.colors.primary : wms.colors.border}`,
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeMd,
        fontWeight: isActive ? wms.fonts.weightMedium : wms.fonts.weightNormal,
        color: isActive ? wms.colors.primary : wms.colors.textSecondary,
        cursor: isActive ? "pointer" : "default",
        boxSizing: "border-box",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
        padding: `0 ${wms.spacing.md}`,
      }}
    >
      {label}
    </div>
  );
};

export default SimTab;
