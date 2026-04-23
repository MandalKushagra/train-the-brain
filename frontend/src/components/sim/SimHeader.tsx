import React from "react";
import { wms } from "./wmsTheme";

interface SimHeaderProps {
  label: string;
}

const SimHeader: React.FC<SimHeaderProps> = ({ label }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        backgroundColor: wms.colors.headerBg,
        color: wms.colors.white,
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeLg,
        fontWeight: wms.fonts.weightBold,
        padding: `0 ${wms.spacing.xl}`,
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

export default SimHeader;
