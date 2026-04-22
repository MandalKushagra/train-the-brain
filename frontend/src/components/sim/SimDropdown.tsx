import React from "react";
import { wms } from "./wmsTheme";

interface SimDropdownProps {
  label: string;
  isActive: boolean;
  activeAction?: string;
  expectedValue?: string;
  onInputSubmit?: (value: string) => void;
}

const SimDropdown: React.FC<SimDropdownProps> = ({
  label,
  isActive,
  activeAction,
  onInputSubmit,
}) => {
  const canSelect = isActive && activeAction === "SELECT";

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    if (canSelect && onInputSubmit) {
      onInputSubmit(e.target.value);
    }
  };

  return (
    <select
      disabled={!canSelect}
      onChange={canSelect ? handleChange : undefined}
      defaultValue=""
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: isActive ? wms.colors.white : wms.colors.disabled,
        color: isActive ? wms.colors.text : wms.colors.textDisabled,
        border: `1px solid ${isActive ? wms.colors.primaryLight : wms.colors.disabledBorder}`,
        borderRadius: wms.radii.md,
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeMd,
        padding: `${wms.spacing.sm} ${wms.spacing.md}`,
        boxSizing: "border-box",
        cursor: canSelect ? "pointer" : "default",
        appearance: canSelect ? "auto" : "none",
      }}
    >
      <option value="" disabled>
        {label}
      </option>
      {canSelect && (
        <option value={label}>{label}</option>
      )}
    </select>
  );
};

export default SimDropdown;
