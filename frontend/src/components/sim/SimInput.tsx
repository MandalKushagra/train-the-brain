import React, { useState } from "react";
import { wms } from "./wmsTheme";

interface SimInputProps {
  label: string;
  isActive: boolean;
  activeAction?: string;
  expectedValue?: string;
  onInputSubmit?: (value: string) => void;
}

const SimInput: React.FC<SimInputProps> = ({
  label,
  isActive,
  activeAction,
  onInputSubmit,
}) => {
  const [value, setValue] = useState("");
  const canType = isActive && activeAction === "TYPE";

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && canType && onInputSubmit) {
      onInputSubmit(value);
    }
  };

  return (
    <input
      type="text"
      placeholder={label}
      value={canType ? value : ""}
      readOnly={!canType}
      disabled={!isActive}
      onChange={canType ? (e) => setValue(e.target.value) : undefined}
      onKeyDown={canType ? handleKeyDown : undefined}
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
        outline: "none",
        cursor: canType ? "text" : "default",
      }}
    />
  );
};

export default SimInput;
