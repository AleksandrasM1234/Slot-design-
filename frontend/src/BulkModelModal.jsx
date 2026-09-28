import { useState } from "react";
import { DEFAULT_MODEL_ID } from "./config";

const TYPES = [
  { key: "image", label: "Images" },
  { key: "animation", label: "Animations" },
  { key: "sound", label: "Sounds" },
];

function initialChoice(models, type) {
  const preferred = models.find((m) => m.model_id === DEFAULT_MODEL_ID[type]);
  return preferred ? preferred.model_id : "";
}

export default function BulkModelModal({ modelsByType, countsByType, onApply, onClose }) {
  const [choice, setChoice] = useState({
    image: initialChoice(modelsByType.image, "image"),
    animation: initialChoice(modelsByType.animation, "animation"),
    sound: initialChoice(modelsByType.sound, "sound"),
  });
  const [onlyEmpty, setOnlyEmpty] = useState(true);

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg p-6 w-[480px]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">Set models for all assets</h3>
          <button className="text-gray-500" onClick={onClose}>✕</button>
        </div>

        <div className="space-y-3 mb-4">
          {TYPES.map(({ key, label }) => (
            <label key={key} className="block text-sm">
              {label} ({countsByType[key]} blocks)
              <select
                className="border rounded p-2 w-full mt-1"
                value={choice[key]}
                onChange={(e) => setChoice((prev) => ({ ...prev, [key]: e.target.value }))}
              >
                <option value="">— leave unchanged —</option>
                {modelsByType[key].map((m) => (
                  <option key={m.model_id} value={m.model_id}>{m.name}</option>
                ))}
              </select>
            </label>
          ))}
        </div>

        <label className="flex items-center gap-2 text-sm mb-4">
          <input
            type="checkbox"
            checked={onlyEmpty}
            onChange={(e) => setOnlyEmpty(e.target.checked)}
          />
          Only fill blocks that have no model yet
        </label>

        <div className="text-xs text-gray-400 mb-4">
          Each block keeps its resolution and duration when the new model supports them;
          otherwise a valid one is picked (backgrounds 16:9, everything else 1:1).
        </div>

        <button
          className="border rounded p-2 bg-blue-500 text-white w-full"
          onClick={() => onApply({ ...choice, onlyEmpty })}
        >
          Apply
        </button>
      </div>
    </div>
  );
}