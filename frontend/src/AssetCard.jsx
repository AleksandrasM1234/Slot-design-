import { useEffect, useState } from "react";

const CATEGORIES = [
  "wild", "scatter", "logo", "low_tier", "high_tier", "symbol",
  "hold_and_win", "background", "background_character", "ui_element",
  "animation", "frame_animation",
];

const STAGES = ["queued", "generating", "postprocessing", "done"];

const CHECKERBOARD_STYLE = {
  backgroundImage: "repeating-conic-gradient(#ccc 0% 25%, white 0% 50%) 50% / 12px 12px",
};

const uploadReferenceImage = async (file) => {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch("http://localhost:8000/uploads/reference-image", {
    method: "POST",
    body: formData,
  });
  const data = await res.json();
  return data.path;
};

const importAsset = async (name, category, generationType, file) => {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("category", category);
  formData.append("generation_type", generationType);
  formData.append("file", file);

  const res = await fetch("http://localhost:8000/assets/import", {
    method: "POST",
    body: formData,
  });
  return res.json();
};

const downloadFile = async (path, filename) => {
  const res = await fetch(`http://localhost:8000/${path}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};

const estimateCost = (model, width, height, duration) => {
  if (!model?.reference_cost_usd || !model.reference_width || !model.reference_height) return null;
  const areaRatio = (width * height) / (model.reference_width * model.reference_height);
  let cost = model.reference_cost_usd * areaRatio;
  if (model.reference_duration && duration) {
    cost *= duration / model.reference_duration;
  }
  return cost;
};

function ProgressBar({ status }) {
  if (status === "failed") {
    return <div className="text-red-500 text-xs font-semibold">Failed</div>;
  }
  const currentIndex = STAGES.indexOf(status);
  const percent = currentIndex >= 0 ? ((currentIndex + 1) / STAGES.length) * 100 : 0;

  return (
    <div className="mt-2">
      <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${
            status === "done" ? "bg-green-500" : "bg-blue-500 animate-pulse"
          }`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="text-xs text-gray-500 mt-1 capitalize">{status}</div>
    </div>
  );
}

function ReferencePicker({ onSelect, onClose }) {
  const [items, setItems] = useState([]);

  useEffect(() => {
    const fetchAll = async () => {
      const [assetsRes, filesRes] = await Promise.all([
        fetch("http://localhost:8000/assets"),
        fetch("http://localhost:8000/api/output-files"),
      ]);
      const jobs = await assetsRes.json();
      const files = await filesRes.json();

      const named = new Map();
      jobs
        .filter((j) => j.status === "done" && j.result_paths?.length > 0)
        .forEach((job) => {
          job.result_paths.forEach((path) => named.set(path, job.asset_name));
        });

      const merged = files.map((f) => ({
        path: f.path,
        label: named.get(f.path) || f.filename,
      }));

      setItems(merged);
    };
    fetchAll();
  }, []);

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg p-6 w-[60vw] max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">Choose a reference</h3>
          <button className="text-gray-500" onClick={onClose}>✕</button>
        </div>
        {items.length === 0 ? (
          <div className="text-gray-400 text-sm text-center py-8">
            No generated assets yet — generate something first.
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-3">
            {items.map((item) => (
              <button
                key={item.path}
                className="border rounded p-1 hover:ring-2 hover:ring-blue-500"
                onClick={() => onSelect(item.path)}
              >
                <img
                  src={`http://localhost:8000/${item.path}`}
                  alt={item.label}
                  className="w-full h-24 object-cover rounded"
                  style={CHECKERBOARD_STYLE}
                />
                <div className="text-xs text-gray-500 truncate mt-1">{item.label}</div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ResolutionControl({ asset, index, updateAsset, selectedModel }) {
  if (!selectedModel) {
    return (
      <div className="col-span-2 text-sm text-gray-400 flex items-center">
        Select a model to set resolution
      </div>
    );
  }

  if (selectedModel.resolution_mode === "enumerated") {
    const options = selectedModel.valid_resolutions;
    const currentValue = `${asset.width}x${asset.height}`;

    return (
      <select
        className="border rounded p-2 col-span-2"
        value={currentValue}
        onChange={(e) => {
          const [w, h] = e.target.value.split("x").map(Number);
          updateAsset(index, "width", w);
          updateAsset(index, "height", h);
        }}
      >
        <option value="">— Select resolution —</option>
        {options.map((r) => (
          <option key={`${r.width}x${r.height}`} value={`${r.width}x${r.height}`}>
            {r.ratio} — {r.width} × {r.height}
          </option>
        ))}
      </select>
    );
  }

  return (
    <>
      <input
        className="border rounded p-2"
        type="number"
        placeholder="Width"
        min={selectedModel.min_width}
        max={selectedModel.max_width}
        step={selectedModel.step}
        value={asset.width}
        onChange={(e) => updateAsset(index, "width", e.target.value)}
      />
      <input
        className="border rounded p-2"
        type="number"
        placeholder="Height"
        min={selectedModel.min_height}
        max={selectedModel.max_height}
        step={selectedModel.step}
        value={asset.height}
        onChange={(e) => updateAsset(index, "height", e.target.value)}
      />
    </>
  );
}

function BackgroundRemovalPanel({ jobId, index, onApplied, onClose }) {
  const [settings, setSettings] = useState({
    edge_tolerance: 45,
    interior_tolerance: 32,
    soft_edge_margin: 18,
    feather_radius: 1.0,
    chroma: "green",
    removal_mode: "color",
    ml_model: "isnet-general-use",
    upscale_strategy: "lanczos",
    scale_factor: 4,
  });
  const [previewPath, setPreviewPath] = useState(null);
  const [loading, setLoading] = useState(false);

  const update = (field, value) => setSettings((prev) => ({ ...prev, [field]: value }));

  const runPreview = async () => {
    setLoading(true);
    const res = await fetch(`http://localhost:8000/assets/${jobId}/reprocess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index, commit: false, ...settings }),
    });
    const data = await res.json();
    setPreviewPath(`${data.path}?t=${Date.now()}`);
    setLoading(false);
  };

  const applyChanges = async () => {
    setLoading(true);
    await fetch(`http://localhost:8000/assets/${jobId}/reprocess`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ index, commit: true, ...settings }),
    });
    setLoading(false);
    onApplied?.();
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[70]" onClick={onClose}>
      <div className="bg-white rounded-lg p-6 w-[70vw] max-h-[85vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">Background removal settings</h3>
          <button className="text-gray-500" onClick={onClose}>✕</button>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-3">
            <label className="block text-sm">
              Removal mode
              <select className="border rounded p-2 w-full mt-1" value={settings.removal_mode}
                onChange={(e) => update("removal_mode", e.target.value)}>
                <option value="color">Color key (chroma green screen)</option>
                <option value="ml">ML segmentation (rembg)</option>
              </select>
            </label>

            {settings.removal_mode === "color" && (
              <label className="block text-sm">
                Chroma color
                <select className="border rounded p-2 w-full mt-1" value={settings.chroma}
                  onChange={(e) => update("chroma", e.target.value)}>
                  <option value="green">Green</option>
                  <option value="magenta">Magenta</option>
                  <option value="white">White</option>
                </select>
              </label>
            )}

            <label className="block text-sm">
              Outer edge tolerance: {settings.edge_tolerance}
              <input type="range" min="0" max="100" value={settings.edge_tolerance}
                onChange={(e) => update("edge_tolerance", Number(e.target.value))} className="w-full" />
            </label>
            <label className="block text-sm">
              Interior gap tolerance: {settings.interior_tolerance}
              <input type="range" min="0" max="100" value={settings.interior_tolerance}
                onChange={(e) => update("interior_tolerance", Number(e.target.value))} className="w-full" />
            </label>
            <label className="block text-sm">
              Glow width: {settings.soft_edge_margin}
              <input type="range" min="1" max="150" value={settings.soft_edge_margin}
                onChange={(e) => update("soft_edge_margin", Number(e.target.value))} className="w-full" />
            </label>
            <label className="block text-sm">
              Edge smoothing: {settings.feather_radius}
              <input type="range" min="0" max="30" step="0.5" value={settings.feather_radius}
                onChange={(e) => update("feather_radius", Number(e.target.value))} className="w-full" />
            </label>
            <label className="block text-sm">
              Upscale factor: {settings.scale_factor}x
              <input type="range" min="1" max="4" value={settings.scale_factor}
                onChange={(e) => update("scale_factor", Number(e.target.value))} className="w-full" />
            </label>

            <button className="border rounded p-2 bg-gray-200 w-full" onClick={runPreview} disabled={loading}>
              {loading ? "Working..." : "Preview"}
            </button>
            <button className="border rounded p-2 bg-blue-500 text-white w-full" onClick={applyChanges} disabled={loading}>
              Apply to this asset
            </button>
          </div>

          <div>
            <div className="text-sm text-gray-500 mb-1">Preview</div>
            <div className="border rounded p-2 h-64 flex items-center justify-center" style={CHECKERBOARD_STYLE}>
              {previewPath ? (
                <img src={`http://localhost:8000/${previewPath}`} alt="preview" className="max-h-full max-w-full" />
              ) : (
                <span className="text-gray-400 text-sm">Click Preview to see the result</span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AssetCard({
  asset, index, updateAsset, enhancePrompt, submitAsset,
  imageModels, animationModels, onAssetDone,
}) {
  const [expanded, setExpanded] = useState(false);
  const [status, setStatus] = useState(null);
  const [resultPaths, setResultPaths] = useState([]);
  const [videoPath, setVideoPath] = useState(null);
  const [error, setError] = useState(null);
  const [showReferencePicker, setShowReferencePicker] = useState(false);
  const [bgPanelIndex, setBgPanelIndex] = useState(null);
  const [showFrames, setShowFrames] = useState(false);

  useEffect(() => {
    if (!asset.jobId) return;

    const fetchCurrentStatus = async () => {
      const res = await fetch(`http://localhost:8000/assets/${asset.jobId}`);
      if (!res.ok) return;
      const data = await res.json();
      setStatus(data.status);
      setResultPaths(data.result_paths || []);
      setVideoPath(data.video_path || null);
      setError(data.error);
      if (data.status === "done" && data.result_paths?.[0]) {
        onAssetDone?.(data.result_paths[0]);
      }
    };
    fetchCurrentStatus();

    const ws = new WebSocket(`ws://localhost:8000/ws/assets/${asset.jobId}`);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data.status);
      setResultPaths(data.result_paths || []);
      setVideoPath(data.video_path || null);
      setError(data.error);
      if (data.status === "done" && data.result_paths?.[0]) {
        onAssetDone?.(data.result_paths[0]);
      }
    };
    return () => ws.close();
  }, [asset.jobId]);

  const modelOptions = asset.generation_type === "animation" ? animationModels : imageModels;
  const selectedModel = modelOptions.find((m) => m.model_id === asset.model_id) || null;

  if (!expanded) {
    return (
      <div
        className="border rounded-lg p-3 bg-white shadow cursor-pointer hover:shadow-md transition"
        onClick={() => setExpanded(true)}
      >
        <div className="text-xs text-gray-400 uppercase">{asset.category || "—"}</div>
        <div className="font-semibold truncate">{asset.name || "Untitled asset"}</div>
        {status && status !== "done" && <ProgressBar status={status} />}
        {resultPaths[0] && (
          <img
            src={`http://localhost:8000/${resultPaths[0]}`}
            alt={asset.name}
            className="mt-2 rounded w-full h-20 object-cover"
            style={CHECKERBOARD_STYLE}
          />
        )}
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      onClick={() => setExpanded(false)}
    >
      <div
        className="bg-white rounded-lg p-6 w-[70vw] h-[70vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold">{asset.name || "Untitled asset"}</h3>
          <button className="text-gray-500" onClick={() => setExpanded(false)}>✕ Close</button>
        </div>

        <div className="grid grid-cols-4 gap-2 mb-2">
          <input
            className="border rounded p-2"
            placeholder="Name"
            value={asset.name}
            onChange={(e) => updateAsset(index, "name", e.target.value)}
          />
          <select
            className="border rounded p-2"
            value={asset.category}
            onChange={(e) => updateAsset(index, "category", e.target.value)}
          >
            {CATEGORIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
          <select
            className="border rounded p-2"
            value={asset.generation_type}
            onChange={(e) => {
              updateAsset(index, "generation_type", e.target.value);
              updateAsset(index, "model_id", "");
            }}
          >
            <option value="image">image</option>
            <option value="animation">animation</option>
          </select>
          <input
            className="border rounded p-2"
            type="number"
            min="1"
            max="8"
            placeholder="Number of generations"
            value={asset.num_outputs}
            onChange={(e) => updateAsset(index, "num_outputs", e.target.value)}
          />
        </div>

        <textarea
          className="border rounded p-2 w-full mb-2"
          rows={2}
          placeholder="Base description (your own words)"
          value={asset.description}
          onChange={(e) => updateAsset(index, "description", e.target.value)}
        />

        <div className="flex gap-2 items-start mb-2">
          <textarea
            className="border rounded p-2 w-full"
            rows={2}
            placeholder="AI-enhanced prompt (editable — this is what actually gets sent)"
            value={asset.enhanced_prompt}
            onChange={(e) => updateAsset(index, "enhanced_prompt", e.target.value)}
          />
          <button
            className="border rounded p-2 bg-gray-200 whitespace-nowrap"
            onClick={() => enhancePrompt(index)}
          >
            Enhance ✨
          </button>
        </div>

        <div className="mb-2">
          <label className="text-sm text-gray-600 block mb-1">
            Reference image {asset.generation_type === "animation" ? "(first frame)" : "(style guide)"}
          </label>
          <div className="flex gap-2 items-center flex-wrap">
            <input
              type="file"
              accept="image/*"
              className="text-sm"
              onChange={async (e) => {
                const file = e.target.files[0];
                if (!file) return;
                const path = await uploadReferenceImage(file);
                updateAsset(index, "reference_image_path", path);
              }}
            />
            <button
              type="button"
              className="border rounded px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200"
              onClick={() => setShowReferencePicker(true)}
            >
              Choose from generated assets
            </button>
            {asset.reference_image_path && (
              <div className="flex items-center gap-1">
                <img
                  src={`http://localhost:8000/${asset.reference_image_path}`}
                  alt="reference"
                  className="w-12 h-12 object-cover rounded border"
                />
                <button
                  type="button"
                  className="text-xs text-red-500"
                  onClick={() => updateAsset(index, "reference_image_path", null)}
                >
                  Remove
                </button>
              </div>
            )}
            {asset.reference_image_path && (
              <select
                className="border rounded p-1 text-sm"
                value={asset.reference_strength || "Mid"}
                onChange={(e) => updateAsset(index, "reference_strength", e.target.value)}
              >
                <option value="Low">Style: Low</option>
                <option value="Mid">Style: Mid</option>
                <option value="High">Style: High</option>
                <option value="Ultra">Style: Ultra</option>
                <option value="Max">Style: Max</option>
              </select>
            )}
          </div>
          {showReferencePicker && (
            <ReferencePicker
              onSelect={(path) => {
                updateAsset(index, "reference_image_path", path);
                setShowReferencePicker(false);
              }}
              onClose={() => setShowReferencePicker(false)}
            />
          )}
        </div>

        <div className="grid grid-cols-4 gap-2 mb-2">
          <select
            className="border rounded p-2"
            value={asset.model_id}
            onChange={(e) => {
              updateAsset(index, "model_id", e.target.value);
              const model = modelOptions.find((m) => m.model_id === e.target.value);
              if (model) {
                if (model.resolution_mode === "enumerated" && model.valid_resolutions.length > 0) {
                  updateAsset(index, "width", model.valid_resolutions[0].width);
                  updateAsset(index, "height", model.valid_resolutions[0].height);
                }
                if (model.min_duration != null) {
                  updateAsset(index, "duration_seconds", model.min_duration);
                }
              }
            }}
          >
            <option value="">— Select model —</option>
            {modelOptions.map((m) => (
              <option key={m.model_id} value={m.model_id}>{m.name}</option>
            ))}
          </select>

          <ResolutionControl
            asset={asset}
            index={index}
            updateAsset={updateAsset}
            selectedModel={selectedModel}
          />

          {asset.generation_type === "animation" && (
            <input
              className="border rounded p-2"
              type="number"
              step="0.5"
              placeholder="Duration (sec)"
              min={selectedModel?.min_duration ?? undefined}
              max={selectedModel?.max_duration ?? undefined}
              value={asset.duration_seconds}
              onChange={(e) => updateAsset(index, "duration_seconds", e.target.value)}
            />
          )}
        </div>

        {selectedModel?.min_duration != null && (
          <div className="text-xs text-gray-400 mb-2">
            Duration must be between {selectedModel.min_duration}s and {selectedModel.max_duration}s
          </div>
        )}

        {selectedModel && (
          <div className="text-xs text-gray-400 mb-2">
            {(() => {
              const est = estimateCost(selectedModel, asset.width, asset.height, asset.duration_seconds);
              return est != null
                ? `~$${est.toFixed(3)} estimated (reference: ${selectedModel.reference_note})`
                : "No cost reference available for this model";
            })()}
          </div>
        )}

        <button
          className="border rounded p-2 bg-blue-500 text-white w-full mb-2"
          onClick={() => submitAsset(index)}
        >
          Generate
        </button>

        <div className="border-t pt-3 mb-4">
          <label className="text-sm text-gray-600 block mb-1">
            Or import an already-made asset (skips generation)
          </label>
          <input
            type="file"
            accept={asset.generation_type === "animation" ? "video/*,image/gif" : "image/*"}
            className="text-sm"
            onChange={async (e) => {
              const file = e.target.files[0];
              if (!file) return;
              const result = await importAsset(
                asset.name || "imported_asset",
                asset.category,
                asset.generation_type,
                file
              );
              setStatus("done");
              setResultPaths(result.result_paths);
              updateAsset(index, "jobId", result.job_id);
            }}
          />
        </div>

        {status && (
          <div className="mb-2">
            <ProgressBar status={status} />
            {error && <div className="text-red-500 text-sm mt-1">{error}</div>}
          </div>
        )}

        {videoPath && (
          <div className="mb-3">
            <div className="text-sm text-gray-500 mb-1">Full animation preview</div>
            <video src={`http://localhost:8000/${videoPath}`} controls loop autoPlay className="rounded w-full max-h-64" />
            {resultPaths.length > 0 && (
              <button
                type="button"
                className="border rounded px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 mt-2"
                onClick={() => setShowFrames((prev) => !prev)}
              >
                {showFrames ? "Hide PNG sequence" : `View PNG sequence (${resultPaths.length} frames)`}
              </button>
            )}
          </div>
        )}

        {resultPaths.length > 0 && (!videoPath || showFrames) && (
          <div className="text-sm text-gray-500 mb-1">
            {videoPath ? "Extracted frames (background removed)" : "Results"}
          </div>
        )}
        {(!videoPath || showFrames) && (
          <div className="grid grid-cols-3 gap-2">
            {resultPaths.map((path, idx) => {
              const extension = path.split(".").pop();
              const filename = resultPaths.length > 1
                ? `${asset.name || "asset"}_${idx}.${extension}`
                : `${asset.name || "asset"}.${extension}`;

              return (
                <div key={path} className="relative group">
                  <img
                    src={`http://localhost:8000/${path}?t=${asset.jobId}`}
                    alt={asset.name}
                    className="rounded w-full"
                    style={CHECKERBOARD_STYLE}
                  />
                  <button
                    type="button"
                    className="absolute bottom-1 right-1 bg-black/70 text-white text-xs rounded px-2 py-1 opacity-0 group-hover:opacity-100 transition"
                    onClick={() => downloadFile(path, filename)}
                  >
                    ⬇ Download
                  </button>
                  <button
                    type="button"
                    className="absolute top-1 right-1 bg-black/70 text-white text-xs rounded px-2 py-1 opacity-0 group-hover:opacity-100 transition"
                    onClick={() => setBgPanelIndex(idx)}
                  >
                    ⚙ Background
                  </button>
                </div>
              );
            })}
          </div>
        )}

        {bgPanelIndex !== null && (
          <BackgroundRemovalPanel
            jobId={asset.jobId}
            index={bgPanelIndex}
            onApplied={() => setResultPaths((prev) => [...prev])}
            onClose={() => setBgPanelIndex(null)}
          />
        )}
      </div>
    </div>
  );
}