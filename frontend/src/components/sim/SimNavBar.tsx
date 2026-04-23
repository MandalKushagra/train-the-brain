import React from "react";
import { wms } from "./wmsTheme";

interface SimNavBarProps {
  label: string;
}

const SimNavBar: React.FC<SimNavBarProps> = ({ label }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: wms.colors.navBg,
        borderTop: `1px solid ${wms.colors.border}`,
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeSm,
        fontWeight: wms.fonts.weightMedium,
        color: wms.colors.textSecondary,
        boxSizing: "border-box",
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </div>
  );
};

export default SimNavBar;
