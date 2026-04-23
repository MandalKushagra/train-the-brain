import React from "react";
import { wms } from "./wmsTheme";

interface SimPlaceholderProps {
  label: string;
  typeName: string;
}

const SimPlaceholder: React.FC<SimPlaceholderProps> = ({ label, typeName }) => {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: wms.colors.placeholder,
        border: `1px dashed ${wms.colors.placeholderBorder}`,
        borderRadius: wms.radii.md,
        fontFamily: wms.fonts.family,
        boxSizing: "border-box",
        overflow: "hidden",
        gap: wms.spacing.xs,
        padding: wms.spacing.sm,
      }}
    >
      <span
        style={{
          fontSize: wms.fonts.sizeSm,
          color: wms.colors.text,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          maxWidth: "100%",
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: wms.fonts.sizeXs,
          color: wms.colors.textSecondary,
          fontStyle: "italic",
        }}
      >
        unsupported: {typeName}
      </span>
    </div>
  );
};

export default SimPlaceholder;
