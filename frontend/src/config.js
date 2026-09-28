export const API_BASE = import.meta.env.VITE_API_URL || "";
export const WS_BASE = API_BASE
  ? API_BASE.replace(/^http/, "ws")
  : (window.location.protocol === "https:" ? "wss://" : "ws://") + window.location.host;

export const DEFAULT_MODEL_ID = {
  image: "nano-banana-2",
  animation: "kling-3.0",
  sound: "sound-effects-v2",
};

export function getDefaultRatioForCategory(category) {
  return category === "background" ? "16:9" : "1:1";
}

export function pickResolutionForCategory(model, category) {
  if (!model?.valid_resolutions?.length) return null;
  const desiredRatio = getDefaultRatioForCategory(category);
  const match = model.valid_resolutions.find((r) => r.ratio.startsWith(desiredRatio));
  return match || model.valid_resolutions[0];
}

export function fitResolutionToModel(model, category, width, height) {
  if (!model || model.resolution_mode === "none") return { width, height };

  if (model.resolution_mode === "enumerated") {
    const stillValid = model.valid_resolutions.some(
      (r) => r.width === width && r.height === height
    );
    if (stillValid) return { width, height };
    return pickResolutionForCategory(model, category) || { width, height };
  }

  const clamp = (value, lo, hi) => Math.min(Math.max(value, lo), hi);
  return {
    width: clamp(width, model.min_width, model.max_width),
    height: clamp(height, model.min_height, model.max_height),
  };
}