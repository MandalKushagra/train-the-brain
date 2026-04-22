import React from "react";
import { wms } from "./wmsTheme";

interface SimIconProps {
  label: string;
}

const SimIcon: React.FC<SimIconProps> = ({ label }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeXl,
        color: wms.colors.textSecondary,
      }}
      title={label}
    >
      ●
    </div>
  );
};

export default SimIcon;
