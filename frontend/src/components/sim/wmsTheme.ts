/**
 * WMS Design System tokens for simulation components.
 * Consistent color scheme: blue primary, white backgrounds, gray borders, rounded corners.
 */
export const wms = {
  colors: {
    primary: "#1565C0",
    primaryLight: "#1E88E5",
    primaryDark: "#0D47A1",
    white: "#FFFFFF",
    background: "#F5F5F5",
    surface: "#FFFFFF",
    border: "#E0E0E0",
    borderDark: "#BDBDBD",
    text: "#212121",
    textSecondary: "#757575",
    textDisabled: "#9E9E9E",
    disabled: "#F0F0F0",
    disabledBorder: "#E0E0E0",
    error: "#D32F2F",
    success: "#388E3C",
    warning: "#F9A825",
    headerBg: "#1565C0",
    navBg: "#FAFAFA",
    cardShadow: "0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.08)",
    placeholder: "#EEEEEE",
    placeholderBorder: "#BDBDBD",
  },
  fonts: {
    family: "'Roboto', 'Helvetica Neue', Arial, sans-serif",
    sizeXs: "10px",
    sizeSm: "12px",
    sizeMd: "14px",
    sizeLg: "16px",
    sizeXl: "20px",
    weightNormal: 400,
    weightMedium: 500,
    weightBold: 700,
  },
  spacing: {
    xs: "2px",
    sm: "4px",
    md: "8px",
    lg: "12px",
    xl: "16px",
  },
  radii: {
    sm: "4px",
    md: "6px",
    lg: "8px",
    xl: "12px",
  },
} as const;
