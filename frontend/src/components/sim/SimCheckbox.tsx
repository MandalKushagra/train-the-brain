import React, { useState } from "react";
import { wms } from "./wmsTheme";

interface SimCheckboxProps {
  label: string;
  isActive: boolean;
  onClick?: () => void;
}

const SimCheckbox: React.FC<SimCheckboxProps> = ({ label, isActive, onClick }) => {
  const [checked, setChecked] = useState(false);

  const handleClick = () => {
    if (isActive) {
      setChecked((prev) => !prev);
      onClick?.();
    }
  };

  return (
    <label
      onClick={handleClick}
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        gap: wms.spacing.md,
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeMd,
        color: isActive ? wms.colors.text : wms.colors.textDisabled,
        cursor: isActive ? "pointer" : "default",
        padding: `0 ${wms.spacing.sm}`,
        boxSizing: "border-box",
      }}
    >
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          width: "18px",
          height: "18px",
          minWidth: "18px",
          border: `2px solid ${isActive ? wms.colors.primary : wms.colors.disabledBorder}`,
          borderRadius: wms.radii.sm,
          backgroundColor: checked && isActive ? wms.colors.primary : wms.colors.white,
          color: wms.colors.white,
          fontSize: "12px",
        }}
      >
        {checked && isActive ? "✓" : ""}
      </span>
      <span
        style={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {label}
      </span>
    </label>
  );
};

export default SimCheckbox;
