import { useState, useCallback } from "react";
import type { SimulationManifest, SimulationStep } from "./types/manifest";
import type { ScreenConfig } from "./types/screenConfig";
import ComponentRenderer from "./components/ComponentRenderer";
import OverlayEngine from "./components/OverlayEngine";
import FloatingTipWidget from "./components/FloatingTipWidget";
import PlaceholderScreen from "./components/PlaceholderScreen";
import { getRenderingMode } from "./utils/manifestUtils";

interface DynamicSimulatorProps {
  manifest: SimulationManifest;
  onBack: () => void;
}

export default function DynamicSimulator({ manifest, onBack }: DynamicSimulatorProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [completed, setCompleted] = useState(false);

  const step: SimulationStep | undefined = manifest.steps[currentStep];

  const goNext = useCallback(() => {
    if (currentStep + 1 >= manifest.steps.length) {
      setCompleted(true);
    } else {
      setCurrentStep((s) => s + 1);
    }
  }, [currentStep, manifest.steps.length]);

  const handleCorrectAction = useCallback(() => {
    goNext();
  }, [goNext]);

  const handleWrongAction = useCallback((_msg: string) => {
    // Error display is handled by OverlayEngine internally
  }, []);

  const handleComponentClick = useCallback((_id: string) => {
    // Clicks are handled by OverlayEngine
  }, []);

  const handleInputSubmit = useCallback((componentId: string, value: string) => {
    // Dispatch custom event for OverlayEngine to pick up
    document.dispatchEvent(
      new CustomEvent("sim-input-submit", {
        detail: { componentId, value },
      })
    );
  }, []);

  if (completed) {
    return (
      <div style={styles.container}>
        <div style={styles.completeCard}>
          <div style={{ fontSize: 64, marginBottom: 16 }}>🎉</div>
          <h2 style={{ fontSize: 24, fontWeight: "bold", marginBottom: 8 }}>Training Complete!</h2>
          <p style={{ color: "#6B7280", marginBottom: 24 }}>{manifest.workflow_name}</p>
          <p style={{ color: "#9CA3AF", marginBottom: 24 }}>
            {manifest.steps.length} steps completed
          </p>
          <button
            onClick={() => { setCurrentStep(0); setCompleted(false); }}
            style={styles.primaryBtn}
          >
            Restart Training
          </button>
          <button onClick={onBack} style={styles.secondaryBtn}>
            Back to Menu
          </button>
        </div>
      </div>
    );
  }

  if (!step) return null;

  const renderMode = getRenderingMode(step, manifest.screen_configs);
  const screenConfig: ScreenConfig | undefined = manifest.screen_configs[step.screen_id];

  return (
    <div style={styles.container}>
      <div style={styles.phoneFrame}>
        {/* Progress bar */}
        <div style={styles.progressBar}>
          <div style={styles.progressMeta}>
            <span>Step {step.step_id} of {manifest.steps.length}</span>
            <span>{step.title}</span>
          </div>
          <div style={styles.progressTrack}>
            <div
              style={{
                ...styles.progressFill,
                width: `${(step.step_id / manifest.steps.length) * 100}%`,
              }}
            />
          </div>
        </div>

        {/* Instruction */}
        <div style={styles.instruction}>
          <p style={{ margin: 0, fontWeight: 600 }}>👆 {step.instruction}</p>
        </div>

        {/* Screen area */}
        <div style={styles.screenArea}>
          {renderMode === "component" && screenConfig ? (
            <>
              <ComponentRenderer
                screenConfig={screenConfig}
                activeTargetId={step.target_component_id}
                activeAction={step.expected_action}
                expectedValue={step.expected_value}
                onComponentClick={handleComponentClick}
                onInputSubmit={handleInputSubmit}
              />
              <OverlayEngine
                targetComponentId={step.target_component_id}
                renderMode="component"
                expectedAction={step.expected_action}
                expectedValue={step.expected_value}
                onCorrectAction={handleCorrectAction}
                onWrongAction={handleWrongAction}
                errorMessage={step.on_wrong_action}
              />
            </>
          ) : renderMode === "screenshot" && step.screenshot ? (
            <>
              <img
                src={step.screenshot}
                alt={step.screen}
                style={{ width: "100%", height: "100%", objectFit: "contain" }}
                draggable={false}
              />
              <OverlayEngine
                targetComponentId={step.target_component_id}
                renderMode="screenshot"
                expectedAction={step.expected_action}
                pixelFallback={step.tap_target}
                onCorrectAction={handleCorrectAction}
                onWrongAction={handleWrongAction}
                errorMessage={step.on_wrong_action}
              />
            </>
          ) : (
            <PlaceholderScreen screenName={step.screen} />
          )}

          {/* Floating tip */}
          <FloatingTipWidget
            tipText={step.tip}
            isVisible={!!step.tip}
          />
        </div>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    minHeight: "100vh",
    background: "#111827",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "flex-start",
    padding: "16px 8px",
  },
  phoneFrame: {
    maxWidth: 390,
    width: "100%",
    display: "flex",
    flexDirection: "column",
  },
  progressBar: { marginBottom: 8 },
  progressMeta: {
    display: "flex",
    justifyContent: "space-between",
    color: "white",
    fontSize: 11,
    opacity: 0.6,
    marginBottom: 4,
  },
  progressTrack: {
    width: "100%",
    background: "#374151",
    borderRadius: 4,
    height: 6,
  },
  progressFill: {
    background: "#3B82F6",
    height: 6,
    borderRadius: 4,
    transition: "width 0.3s",
  },
  instruction: {
    background: "#2563EB",
    borderRadius: "12px 12px 0 0",
    padding: "12px 16px",
    color: "white",
    fontSize: 15,
  },
  screenArea: {
    position: "relative",
    width: "100%",
    height: 600,
    background: "#F5F5F5",
    borderRadius: "0 0 12px 12px",
    overflow: "hidden",
  },
  completeCard: {
    background: "white",
    borderRadius: 16,
    padding: 32,
    maxWidth: 384,
    width: "100%",
    textAlign: "center",
  },
  primaryBtn: {
    width: "100%",
    padding: "14px 0",
    marginBottom: 8,
    background: "#2563EB",
    color: "white",
    fontSize: 16,
    fontWeight: "bold",
    border: "none",
    borderRadius: 12,
    cursor: "pointer",
  },
  secondaryBtn: {
    width: "100%",
    padding: "14px 0",
    background: "#E5E7EB",
    color: "#374151",
    fontSize: 16,
    fontWeight: "bold",
    border: "none",
    borderRadius: 12,
    cursor: "pointer",
  },
};
