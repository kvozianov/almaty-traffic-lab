import type { RunPassportJson } from "./types";

type CalibrationValidation = RunPassportJson["calibrationValidation"];

export function isEmpiricalCalibrationComplete(validation: CalibrationValidation): boolean {
  return (
    validation?.available === true &&
    validation.claimLabel === "calibrated" &&
    Array.isArray(validation.observedVsSimulated) &&
    validation.observedVsSimulated.length > 0
  );
}
