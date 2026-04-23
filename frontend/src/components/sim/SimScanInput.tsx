import React, { useState } from "react";
import { wms } from "./wmsTheme";

interface SimScanInputProps {
  label: string;
  isActive: boolean;
  activeAction?: string;
  onInputSubmit?: (value: string) => void;
}

const SimScanInput: React.FC<SimScanInputProps> = ({
  label,
  isActive,
  activeAction,
  onInputSubmit,
}) => {
  const [value, setValue] = useState("");
  const canScan = isActive && activeAction === "SCAN";

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && canScan && onInputSubmit) {
      onInputSubmit(value);
    }
  };

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        alignItems: "center",
        gap: wms.spacing.sm,
        boxSizing: "border-box",
      }}
    >
      <input
        type="text"
        placeholder={label}
        value={canScan ? value : ""}
        readOnly={!canScan}
        disabled={!isActive}
        onChange={canScan ? (e) => setValue(e.target.value) : undefined}
        onKeyDown={canScan ? handleKeyDown : undefined}
        style={{
          flex: 1,
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
        }}
      />
      <span
        style={{
          fontSize: wms.fonts.sizeLg,
          color: isActive ? wms.colors.primary : wms.colors.textDisabled,
        }}
        title="Scan"
      >
        ⊞
      </span>
    </div>
  );
};

export default SimScanInput;
