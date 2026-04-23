import React from "react";
import { wms } from "./wmsTheme";

interface SimLabelProps {
  label: string;
}

const SimLabel: React.FC<SimLabelProps> = ({ label }) => {
  return (
    <span
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeMd,
        color: wms.colors.text,
        overflow: "hidden",
        textOverflow: "ellipsis",
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
};

export default SimLabel;
