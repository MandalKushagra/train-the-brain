import { useState, useCallback, useEffect } from "react";
import type { ExpectedAction } from "../types/manifest";
import { wms } from "./sim/wmsTheme";

export interface UserInputHandlerProps {
  action: ExpectedAction;
  expectedValue: string;
  targetComponentId: string;
  onCorrectInput: () => void;
  onIncorrectInput: (message: string) => void;
}

/**
 * Validates trainee input against expected values for TYPE, SELECT, and SCAN actions.
 *
 * TYPE: Compares typed text against expectedValue (case-insensitive trim match).
 * SELECT: Compares selected option against expectedValue.
 * SCAN: Compares scanned barcode/QR value against expectedValue.
 *
 * On correct input: calls onCorrectInput to advance the step.
 * On incorrect input: calls onIncorrectInput with the error message, shown for 2.5s.
 */
const UserInputHandler: React.FC<UserInputHandlerProps> = ({
  action,
  expectedValue,
  targetComponentId,
  onCorrectInput,
  onIncorrectInput,
}) => {
  const [errorVisible, setErrorVisible] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  // Clear error state when step changes
  useEffect(() => {
    setErrorVisible(false);
    setErrorMessage("");
  }, [targetComponentId, expectedValue]);

  // Listen for custom input-submit events dispatched by the OverlayEngine
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent).detail as {
        componentId: string;
        value: string;
      };
      if (detail.componentId !== targetComponentId) return;

      const isCorrect = matchesExpected(action, detail.value, expectedValue);

      if (isCorrect) {
        onCorrectInput();
      } else {
        const msg = `Incorrect ${action.toLowerCase()} input. Expected: "${expectedValue}"`;
        setErrorMessage(msg);
        setErrorVisible(true);
        onIncorrectInput(msg);
        setTimeout(() => {
          setErrorVisible(false);
          setErrorMessage("");
        }, 2500);
      }
    };

    document.addEventListener("sim-input-submit", handler);
    return () => document.removeEventListener("sim-input-submit", handler);
  }, [action, expectedValue, targetComponentId, onCorrectInput, onIncorrectInput]);

  if (!errorVisible) return null;

  return (
    <div
      data-testid="input-error-feedback"
      style={{
        position: "absolute",
        top: "8px",
        left: "8px",
        right: "8px",
        backgroundColor: wms.colors.error,
        color: wms.colors.white,
        padding: `${wms.spacing.md} ${wms.spacing.lg}`,
        borderRadius: wms.radii.lg,
        fontFamily: wms.fonts.family,
        fontSize: wms.fonts.sizeMd,
        fontWeight: wms.fonts.weightMedium,
        zIndex: 1000,
        textAlign: "center",
        boxShadow: "0 4px 12px rgba(0,0,0,0.3)",
      }}
    >
      ❌ {errorMessage}
    </div>
  );
};

/**
 * Case-insensitive trim match for TYPE, SELECT, and SCAN actions.
 */
export function matchesExpected(
  action: ExpectedAction,
  submittedValue: string,
  expectedValue: string,
): boolean {
  switch (action) {
    case "TYPE":
    case "SELECT":
    case "SCAN":
      return (
        submittedValue.trim().toLowerCase() ===
        expectedValue.trim().toLowerCase()
      );
    default:
      return false;
  }
}

/**
 * Hook that provides input validation logic for use by parent components.
 * Returns a validateInput function compatible with ComponentRenderer's onInputSubmit.
 */
export function useInputValidation(
  action: ExpectedAction,
  expectedValue: string,
  onCorrectInput: () => void,
  onIncorrectInput: (message: string) => void,
) {
  const validateInput = useCallback(
    (_componentId: string, submittedValue: string) => {
      const isCorrect = matchesExpected(action, submittedValue, expectedValue);

      if (isCorrect) {
        onCorrectInput();
      } else {
        const msg = `Incorrect ${action.toLowerCase()} input. Expected: "${expectedValue}"`;
        onIncorrectInput(msg);
      }
    },
    [action, expectedValue, onCorrectInput, onIncorrectInput],
  );

  return validateInput;
}

export default UserInputHandler;
