import React from "react";
import type { ScreenConfig, UIElement, ElementType } from "../types/screenConfig";
import type { ExpectedAction } from "../types/manifest";
import {
  SimButton,
  SimInput,
  SimDropdown,
  SimCard,
  SimTab,
  SimLabel,
  SimHeader,
  SimNavBar,
  SimIcon,
  SimCheckbox,
  SimScanInput,
  SimPlaceholder,
} from "./sim";
import { wms } from "./sim/wmsTheme";

export interface ComponentRendererProps {
  screenConfig: ScreenConfig;
  activeTargetId?: string;
  activeAction?: ExpectedAction;
  expectedValue?: string;
  onComponentClick: (componentId: string) => void;
  onInputSubmit: (componentId: string, value: string) => void;
}

/** Set of element types that are considered interactive */
const INTERACTIVE_TYPES: ReadonlySet<string> = new Set<string>([
  "button",
  "input",
  "dropdown",
  "checkbox",
  "scan_input",
]);

/** Set of supported element types for the component mapping */
const SUPPORTED_TYPES: ReadonlySet<string> = new Set<string>([
  "button",
  "input",
  "dropdown",
  "card",
  "tab",
  "text_label",
  "header",
  "navigation_bar",
  "icon",
  "checkbox",
  "scan_input",
]);

/**
 * Renders a single UIElement as the appropriate Sim* component.
 * Interactive elements are non-functional unless their component_id matches activeTargetId.
 */
function renderSimComponent(
  element: UIElement,
  isActive: boolean,
  activeAction?: ExpectedAction,
  expectedValue?: string,
  onComponentClick?: (componentId: string) => void,
  onInputSubmit?: (componentId: string, value: string) => void,
): React.ReactNode {
  const handleClick = () => onComponentClick?.(element.component_id);
  const handleInputSubmit = (value: string) =>
    onInputSubmit?.(element.component_id, value);

  if (!SUPPORTED_TYPES.has(element.type)) {
    return (
      <SimPlaceholder label={element.label} typeName={element.type} />
    );
  }

  const type: ElementType = element.type;

  switch (type) {
    case "button":
      return (
        <SimButton
          label={element.label}
          isActive={isActive}
          onClick={handleClick}
        />
      );
    case "input":
      return (
        <SimInput
          label={element.label}
          isActive={isActive}
          activeAction={activeAction}
          expectedValue={expectedValue}
          onInputSubmit={handleInputSubmit}
        />
      );
    case "dropdown":
      return (
        <SimDropdown
          label={element.label}
          isActive={isActive}
          activeAction={activeAction}
          expectedValue={expectedValue}
          onInputSubmit={handleInputSubmit}
        />
      );
    case "card":
      return <SimCard label={element.label} />;
    case "tab":
      return (
        <SimTab
          label={element.label}
          isActive={isActive}
          onClick={handleClick}
        />
      );
    case "text_label":
      return <SimLabel label={element.label} />;
    case "header":
      return <SimHeader label={element.label} />;
    case "navigation_bar":
      return <SimNavBar label={element.label} />;
    case "icon":
      return <SimIcon label={element.label} />;
    case "checkbox":
      return (
        <SimCheckbox
          label={element.label}
          isActive={isActive}
          onClick={handleClick}
        />
      );
    case "scan_input":
      return (
        <SimScanInput
          label={element.label}
          isActive={isActive}
          activeAction={activeAction}
          onInputSubmit={handleInputSubmit}
        />
      );
    default:
      return (
        <SimPlaceholder label={element.label} typeName={String(type)} />
      );
  }
}

/**
 * Renders a single UIElement with absolute positioning and optional nested children.
 */
function renderElement(
  element: UIElement,
  activeTargetId?: string,
  activeAction?: ExpectedAction,
  expectedValue?: string,
  onComponentClick?: (componentId: string) => void,
  onInputSubmit?: (componentId: string, value: string) => void,
): React.ReactNode {
  const isActive =
    INTERACTIVE_TYPES.has(element.type) &&
    element.component_id === activeTargetId;

  const hasChildren = element.children && element.children.length > 0;

  const handleWrapperClick = (e: React.MouseEvent) => {
    // Only fire click for interactive elements; prevent bubbling from children
    if (INTERACTIVE_TYPES.has(element.type)) {
      e.stopPropagation();
      onComponentClick?.(element.component_id);
    }
  };

  return (
    <div
      key={element.component_id}
      data-component-id={element.component_id}
      onClick={isActive ? handleWrapperClick : undefined}
      style={{
        position: "absolute",
        left: `${element.position.x}%`,
        top: `${element.position.y}%`,
        width: `${element.position.width}%`,
        height: `${element.position.height}%`,
        // If element has children, act as a relative container for them
        ...(hasChildren ? { position: "absolute" } : {}),
      }}
    >
      {renderSimComponent(
        element,
        isActive,
        activeAction,
        expectedValue,
        onComponentClick,
        onInputSubmit,
      )}
      {hasChildren && (
        <div
          style={{
            position: "relative",
            width: "100%",
            height: "100%",
            top: 0,
            left: 0,
          }}
        >
          {element.children!.map((child) =>
            renderElement(
              child,
              activeTargetId,
              activeAction,
              expectedValue,
              onComponentClick,
              onInputSubmit,
            ),
          )}
        </div>
      )}
    </div>
  );
}

/**
 * ComponentRenderer reads a ScreenConfig and renders each element as a real
 * React component using percentage-based absolute positioning.
 *
 * - All interactive elements are non-functional unless activated by the Overlay Engine.
 * - Unsupported element types render as SimPlaceholder.
 * - Nested elements are rendered within their parent container.
 * - Each element gets a `data-component-id` attribute for DOM querying.
 */
const ComponentRenderer: React.FC<ComponentRendererProps> = ({
  screenConfig,
  activeTargetId,
  activeAction,
  expectedValue,
  onComponentClick,
  onInputSubmit,
}) => {
  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        height: "100%",
        backgroundColor: wms.colors.background,
        fontFamily: wms.fonts.family,
        overflow: "hidden",
      }}
    >
      {screenConfig.elements.map((element) =>
        renderElement(
          element,
          activeTargetId,
          activeAction,
          expectedValue,
          onComponentClick,
          onInputSubmit,
        ),
      )}
    </div>
  );
};

export default ComponentRenderer;
