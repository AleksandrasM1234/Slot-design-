import { useEffect, useState } from "react";
import AssetCard from "./AssetCard";
import OutOfCreditsModal from "./OutOfCreditsModal";
import { API_BASE, DEFAULT_MODEL_ID, pickResolutionForCategory } from "./config";

const emptyAsset = {
  name: "",
  category: "symbol",
  description: "",
  enhanced_prompt: "",
  style_keywords: "",
  generation_type: "image",
  model_id: "",
  width: 768,
  height: 768,
  duration_seconds: 4,
  num_outputs: 1,
  jobId: null,
  role_constant: null,
  blueprintKey: null,
  reference_image_path: null,
  reference_strength: "Mid",
  chroma_color: "green",
  text_content: "",
  uniqueId: null,
};

const AUTO_REFERENCE_CATEGORIES = ["low_tier", "high_tier"];

const STORAGE_KEY = "slot_asset_generator_state";

function loadPersistedState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

const makeUniqueId = () => `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;

const estimateAssetCost = (asset, imageModels, animationModels, soundModels) => {
  const modelOptions =
    asset.generation_type === "animation" ? animationModels :
    asset.generation_type === "sound" ? soundModels :
    imageModels;
  const model = modelOptions.find((m) => m.model_id === asset.model_id);
  if (!model?.reference_cost_usd || !model.reference_width || !model.reference_height) return null;

  const areaRatio = (asset.width * asset.height) / (model.reference_width * model.reference_height);
  let cost = model.reference_cost_usd * areaRatio;
  if (model.reference_duration && asset.duration_seconds) {
    cost *= asset.duration_seconds / model.reference_duration;
  }
  return cost * (asset.num_outputs || 1);
};

export default function App() {
  const persisted = loadPersistedState();
  const backfilledAssets = (persisted?.assets ?? []).map((a) =>
    a.uniqueId ? a : { ...a, uniqueId: makeUniqueId() }
  );

  const [gameName, setGameName] = useState(persisted?.gameName ?? "");
  const [artStyle, setArtStyle] = useState(persisted?.artStyle ?? "");
  const [palette, setPalette] = useState(persisted?.palette ?? "");
  const [assets, setAssets] = useState(backfilledAssets);
  const [savedThemeNames, setSavedThemeNames] = useState([]);
  const [selectedThemeName, setSelectedThemeName] = useState(persisted?.selectedThemeName ?? "");
  const [imageModels, setImageModels] = useState([]);
  const [animationModels, setAnimationModels] = useState([]);
  const [soundModels, setSoundModels] = useState([]);
  const [activeTab, setActiveTab] = useState(persisted?.activeTab ?? "image");
  const [blueprints, setBlueprints] = useState([]);
  const [showPicker, setShowPicker] = useState(false);
  const [frameworks, setFrameworks] = useState([]);
  const [showFrameworkPicker, setShowFrameworkPicker] = useState(false);
  const [showCreateFramework, setShowCreateFramework] = useState(false);
  const [newFrameworkName, setNewFrameworkName] = useState("");
  const [newFrameworkDescription, setNewFrameworkDescription] = useState("");
  const [newFrameworkCounts, setNewFrameworkCounts] = useState({});
  const [masterPrompt, setMasterPrompt] = useState(persisted?.masterPrompt ?? "");
  const [masterPromptEnhanced, setMasterPromptEnhanced] = useState(persisted?.masterPromptEnhanced ?? "");
  const [lastGeneratedPath, setLastGeneratedPath] = useState(persisted?.lastGeneratedPath ?? null);
  const [batchStatus, setBatchStatus] = useState(null);
  const [leonardoBalance, setLeonardoBalance] = useState(null);
  const [leonardoEstimatedUsd, setLeonardoEstimatedUsd] = useState(null);
  const [sessionCost, setSessionCost] = useState(0);
  const [showDownloadPicker, setShowDownloadPicker] = useState(false);
  const [outOfCreditsService, setOutOfCreditsService] = useState(null);
  const [worldFillStatus, setWorldFillStatus] = useState(null);

  useEffect(() => {
    refreshThemeList();
    refreshModelList();
    refreshBlueprints();
    refreshFrameworks();
    refreshBalance();

    const interval = setInterval(refreshBalance, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const stateToSave = {
      gameName, artStyle, palette, assets, selectedThemeName,
      activeTab, masterPrompt, masterPromptEnhanced, lastGeneratedPath,
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
  }, [gameName, artStyle, palette, assets, selectedThemeName, activeTab, masterPrompt, masterPromptEnhanced, lastGeneratedPath]);

  const checkForCreditsError = (message) => {
    if (!message) return false;
    if (message.includes("LEONARDO_OUT_OF_CREDITS")) {
      setOutOfCreditsService("leonardo");
      return true;
    }
    if (message.includes("GROQ_OUT_OF_CREDITS")) {
      setOutOfCreditsService("groq");
      return true;
    }
    return false;
  };

  const refreshBalance = async () => {
    try {
      const [balanceRes, sessionRes] = await Promise.all([
        fetch(`${API_BASE}/leonardo/balance`),
        fetch(`${API_BASE}/leonardo/session-cost`),
      ]);
      if (balanceRes.ok) {
        const data = await balanceRes.json();
        setLeonardoBalance(data.credits_remaining);
        setLeonardoEstimatedUsd(data.estimated_usd);
      }
      if (sessionRes.ok) {
        const data = await sessionRes.json();
        setSessionCost(data.total_usd);
      }
    } catch {
      // ignore
    }
  };

  const handleAssetDone = (path, category, blueprintKey) => {
    if (AUTO_REFERENCE_CATEGORIES.includes(category) && blueprintKey) {
      setAssets((prev) =>
        prev.map((a) =>
          a.blueprintKey === blueprintKey &&
          a.generation_type === "animation" &&
          !a.reference_image_path
            ? { ...a, reference_image_path: path }
            : a
        )
      );
    }
  };

  const refreshModelList = async () => {
    const res = await fetch(`${API_BASE}/models`);
    const data = await res.json();
    setImageModels(data.image);
    setAnimationModels(data.animation);
    setSoundModels(data.sound || []);
  };

  const refreshBlueprints = async () => {
    const res = await fetch(`${API_BASE}/blueprints`);
    setBlueprints(await res.json());
  };

  const refreshFrameworks = async () => {
    const res = await fetch(`${API_BASE}/frameworks`);
    setFrameworks(await res.json());
  };

  const updateAsset = (index, field, value) => {
    setAssets((prev) =>
      prev.map((a, i) => (i === index ? { ...a, [field]: value } : a))
    );
  };

  const addAssetFromBlueprint = (blueprint, generationType, overrides = {}) => {
    const existingCount = assets.filter((a) => a.blueprintKey === blueprint.key).length;

    const modelList =
      generationType === "animation" ? animationModels :
      generationType === "sound" ? soundModels :
      imageModels;
    const defaultModelId = overrides.model_id ?? DEFAULT_MODEL_ID[generationType];
    const modelObj = modelList.find((m) => m.model_id === defaultModelId);
    const defaultRes = pickResolutionForCategory(modelObj, blueprint.category);

    setAssets((prev) => [
      ...prev,
      {
        ...emptyAsset,
        name: existingCount > 0 ? `${blueprint.key}_${existingCount + 1}` : blueprint.key,
        category: blueprint.category,
        generation_type: generationType,
        role_constant: blueprint.role_constant,
        blueprintKey: blueprint.key,
        num_outputs: overrides.num_outputs ?? blueprint.default_num_outputs,
        duration_seconds: overrides.duration_seconds ?? blueprint.default_duration_seconds ?? 4,
        reference_image_path: null,
        model_id: defaultModelId,
        width: overrides.width ?? defaultRes?.width ?? emptyAsset.width,
        height: overrides.height ?? defaultRes?.height ?? emptyAsset.height,
        uniqueId: makeUniqueId(),
      },
    ]);
    setShowPicker(false);
  };

  const loadFramework = (framework) => {
    framework.blueprint_keys.forEach((entry) => {
      let key, explicitType, overrides = {};

      if (typeof entry === "string") {
        [key, explicitType] = entry.split(":");
      } else {
        key = entry.key;
        explicitType = entry.type;
        overrides = {
          model_id: entry.model_id,
          width: entry.width,
          height: entry.height,
          duration_seconds: entry.duration_seconds,
          num_outputs: entry.num_outputs,
        };
      }

      const blueprint = blueprints.find((b) => b.key === key);
      if (!blueprint) return;

      let generationType = explicitType;
      if (!generationType || !blueprint.available_types.includes(generationType)) {
        generationType = blueprint.available_types.includes("image") ? "image" : "animation";
      }
      addAssetFromBlueprint(blueprint, generationType, overrides);
    });
    setShowFrameworkPicker(false);
  };

  const adjustFrameworkCount = (key, delta) => {
    setNewFrameworkCounts((prev) => {
      const next = { ...prev, [key]: Math.max(0, (prev[key] || 0) + delta) };
      return next;
    });
  };

  const saveNewFramework = async () => {
    const blueprintKeys = [];
    Object.entries(newFrameworkCounts).forEach(([key, count]) => {
      for (let i = 0; i < count; i++) blueprintKeys.push(key);
    });
    if (!newFrameworkName || blueprintKeys.length === 0) return;

    const key = newFrameworkName.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_");
    await fetch(`${API_BASE}/frameworks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        key,
        display_name: newFrameworkName,
        description: newFrameworkDescription,
        blueprint_keys: blueprintKeys,
      }),
    });

    setNewFrameworkName("");
    setNewFrameworkDescription("");
    setNewFrameworkCounts({});
    setShowCreateFramework(false);
    await refreshFrameworks();
  };

  const exportFramework = (framework) => {
    const blob = new Blob([JSON.stringify(framework, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${framework.key}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const deleteFramework = async (framework) => {
    const confirmed = window.confirm(
      `Delete "${framework.display_name}"? This cannot be undone.`
    );
    if (!confirmed) return;

    await fetch(`${API_BASE}/frameworks/${framework.key}`, {
      method: "DELETE",
    });
    await refreshFrameworks();
  };

  const importFramework = async (file) => {
    const text = await file.text();
    const framework = JSON.parse(text);
    await fetch(`${API_BASE}/frameworks`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        key: framework.key,
        display_name: framework.display_name,
        description: framework.description || "",
        blueprint_keys: framework.blueprint_keys,
      }),
    });
    await refreshFrameworks();
  };

  const buildThemePayload = () => ({
    name: gameName,
    art_style: artStyle,
    palette: palette.split(",").map((p) => p.trim()).filter(Boolean),
    master_prompt: masterPrompt,
    master_prompt_enhanced: masterPromptEnhanced || null,
    assets: assets.map((a) => ({
      name: a.name,
      category: a.category,
      description: a.description,
      enhanced_prompt: a.enhanced_prompt || null,
      role_constant: a.role_constant || null,
      reference_image_path: a.reference_image_path || null,
      reference_strength: a.reference_strength || "Mid",
      chroma_color: a.chroma_color || "green",
      text_content: a.text_content || null,
      unique_id: a.uniqueId,
      style_keywords: a.style_keywords.split(",").map((k) => k.trim()).filter(Boolean),
      settings: {
        generation_type: a.generation_type,
        width: Number(a.width),
        height: Number(a.height),
        duration_seconds: (a.generation_type === "animation" || a.generation_type === "sound") ? Number(a.duration_seconds) : null,
        num_outputs: Number(a.num_outputs),
      },
    })),
  });

  const refreshThemeList = async () => {
    const res = await fetch(`${API_BASE}/themes`);
    setSavedThemeNames(await res.json());
  };

  const saveTheme = async () => {
    const theme = buildThemePayload();
    await fetch(`${API_BASE}/themes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme }),
    });
    await refreshThemeList();
  };

  const loadTheme = async (name) => {
    const res = await fetch(`${API_BASE}/themes/${name}`);
    const theme = await res.json();
    setGameName(theme.name);
    setArtStyle(theme.art_style);
    setPalette(theme.palette.join(", "));
    setMasterPrompt(theme.master_prompt || "");
    setMasterPromptEnhanced(theme.master_prompt_enhanced || "");
    setAssets(
      theme.assets.map((a) => ({
        name: a.name,
        category: a.category,
        description: a.description,
        enhanced_prompt: a.enhanced_prompt || "",
        role_constant: a.role_constant || null,
        blueprintKey: null,
        reference_image_path: a.reference_image_path || null,
        reference_strength: a.reference_strength || "Mid",
        chroma_color: a.chroma_color || "green",
        text_content: a.text_content || "",
        style_keywords: a.style_keywords.join(", "),
        generation_type: a.settings.generation_type,
        model_id: "",
        width: a.settings.width,
        height: a.settings.height,
        duration_seconds: a.settings.duration_seconds ?? 4,
        num_outputs: a.settings.num_outputs,
        jobId: null,
        uniqueId: makeUniqueId(),
      }))
    );
  };

  const enhancePrompt = async (index) => {
  const asset = assets[index];

  if (asset.generation_type === "sound") {
    const res = await fetch(`${API_BASE}/prompts/enhance-sound`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_prompt: asset.description,
        role_constant: asset.role_constant || null,
        duration: Number(asset.duration_seconds) || null,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (!checkForCreditsError(data.detail)) {
        alert(`Enhance failed: ${data.detail || "unknown error"}`);
      }
      return;
    }
    updateAsset(index, "enhanced_prompt", data.enhanced_prompt);
    return;
  }

  const res = await fetch(`${API_BASE}/prompts/enhance`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_prompt: asset.description,
        art_style: artStyle,
        palette: palette.split(",").map((p) => p.trim()).filter(Boolean),
        category: asset.category,
        is_animation: asset.generation_type === "animation",
        master_context: masterPromptEnhanced || masterPrompt || null,
        role_constant: asset.role_constant || null,
        has_reference_image: Boolean(asset.reference_image_path),
        text_content: asset.text_content || null,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (!checkForCreditsError(data.detail)) {
        alert(`Enhance failed: ${data.detail || "unknown error"}`);
      }
      return;
    }
    updateAsset(index, "enhanced_prompt", data.enhanced_prompt);
    updateAsset(index, "chroma_color", data.chroma_color);
  };

  const enhanceMasterPrompt = async () => {
    const res = await fetch(`${API_BASE}/prompts/enhance-master`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_prompt: masterPrompt,
        art_style: artStyle,
        palette: palette.split(",").map((p) => p.trim()).filter(Boolean),
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      if (!checkForCreditsError(data.detail)) {
        alert(`Enhance failed: ${data.detail || "unknown error"}`);
      }
      return;
    }
    setMasterPromptEnhanced(data.enhanced_prompt);
  };

  const autoFillFromWorld = async () => {
    const context = masterPromptEnhanced || masterPrompt;
    if (!context) {
      alert("Write and/or enhance a game world description first.");
      return;
    }

    const targetIds = assets.map((a) => a.uniqueId);
    let completed = 0;
    let skipped = 0;

    setWorldFillStatus({ done: 0, total: targetIds.length, currentName: "" });

    for (const id of targetIds) {
      const currentIndex = assets.findIndex((a) => a.uniqueId === id);
      if (currentIndex === -1) {
        completed++;
        setWorldFillStatus({ done: completed, total: targetIds.length, currentName: "" });
        continue;
      }

      const asset = assets[currentIndex];

      if (asset.generation_type === "sound") {
        completed++;
        setWorldFillStatus({ done: completed, total: targetIds.length, currentName: "" });
        continue;
      }

      const blueprint = blueprints.find((b) => b.key === asset.blueprintKey);
      const roleName = blueprint ? blueprint.display_name : asset.name || asset.category;

      setWorldFillStatus({ done: completed, total: targetIds.length, currentName: roleName });

      const hasOwnDescription =
        asset.description.trim() !== "" &&
        !asset.description.startsWith("(auto-filled from world)");

      if (hasOwnDescription) {
        const res = await fetch(`${API_BASE}/prompts/enhance`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            base_prompt: asset.description,
            art_style: artStyle,
            palette: palette.split(",").map((p) => p.trim()).filter(Boolean),
            category: asset.category,
            is_animation: asset.generation_type === "animation",
            master_context: context,
            role_constant: asset.role_constant || null,
            has_reference_image: Boolean(asset.reference_image_path),
            text_content: asset.text_content || null,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          if (checkForCreditsError(data.detail)) {
            setWorldFillStatus(null);
            return;
          }
          console.warn(`Enhance failed for "${roleName}"`, data);
          skipped++;
        } else if (!data.enhanced_prompt) {
          console.warn(`Enhance returned empty content for "${roleName}"`, data);
          skipped++;
        } else {
          const idx = assets.findIndex((a) => a.uniqueId === id);
          if (idx !== -1) {
            updateAsset(idx, "enhanced_prompt", data.enhanced_prompt);
            updateAsset(idx, "chroma_color", data.chroma_color);
          }
        }
      } else {
        const res = await fetch(`${API_BASE}/prompts/generate-from-world`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role_display_name: roleName,
            category: asset.category,
            is_animation: asset.generation_type === "animation",
            art_style: artStyle,
            palette: palette.split(",").map((p) => p.trim()).filter(Boolean),
            master_context: context,
            text_content: asset.text_content || null,
          }),
        });
        const data = await res.json();
        if (!res.ok) {
          if (checkForCreditsError(data.detail)) {
            setWorldFillStatus(null);
            return;
          }
          console.warn(`Generation failed for "${roleName}"`, data);
          skipped++;
        } else if (!data.enhanced_prompt) {
          console.warn(`Generation returned empty content for "${roleName}"`, data);
          skipped++;
        } else {
          const idx = assets.findIndex((a) => a.uniqueId === id);
          if (idx !== -1) {
            updateAsset(idx, "enhanced_prompt", data.enhanced_prompt);
            updateAsset(idx, "description", `(auto-filled from world) ${roleName}`);
            updateAsset(idx, "chroma_color", data.chroma_color);
          }
        }
      }

      completed++;
      setWorldFillStatus({ done: completed, total: targetIds.length, currentName: "" });
    }

    setWorldFillStatus({ done: completed, total: targetIds.length, currentName: "", finished: true, skipped });
    setTimeout(() => setWorldFillStatus(null), 4000);
  };

  const submitAsset = async (index) => {
    const assetForm = assets[index];
    const theme = buildThemePayload();

    const res = await fetch(`${API_BASE}/assets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        theme,
        asset_name: assetForm.name,
        unique_id: assetForm.uniqueId,
        model_id: assetForm.model_id,
      }),
    });
    const data = await res.json();
    updateAsset(index, "jobId", data.job_id);
    return data.job_id;
  };

  const pollJobUntilDone = async (jobId) => {
    while (true) {
      const res = await fetch(`${API_BASE}/assets/${jobId}`);
      const data = await res.json();
      if (data.status === "done" || data.status === "failed") return data;
      await new Promise((resolve) => setTimeout(resolve, 2000));
    }
  };

  const generateAll = async () => {
    const readyAssets = assets
      .map((asset, i) => ({ asset, i }))
      .filter(({ asset }) => asset.model_id);

    if (readyAssets.length === 0) {
      alert("No assets have a model selected yet — open each card and pick a model first.");
      return;
    }

    let totalEstimate = 0;
    let missingEstimateCount = 0;
    readyAssets.forEach(({ asset }) => {
      const cost = estimateAssetCost(asset, imageModels, animationModels, soundModels);
      if (cost == null) {
        missingEstimateCount++;
      } else {
        totalEstimate += cost;
      }
    });

    const missingNote = missingEstimateCount > 0
      ? `\n\n(${missingEstimateCount} asset(s) have no cost reference and aren't included in this total.)`
      : "";
    const confirmed = window.confirm(
      `This will generate ${readyAssets.length} asset(s) for an estimated total of ~$${totalEstimate.toFixed(2)}.${missingNote}\n\nContinue?`
    );
    if (!confirmed) return;

    setBatchStatus({ phase: "submitting", done: 0, total: readyAssets.length, failed: 0 });

    const jobIds = [];
    for (const { i } of readyAssets) {
      const jobId = await submitAsset(i);
      jobIds.push(jobId);
    }

    setBatchStatus({ phase: "waiting", done: 0, total: jobIds.length, failed: 0 });

    let doneCount = 0;
    let failedCount = 0;

    await Promise.all(
      jobIds.map(async (jobId) => {
        const result = await pollJobUntilDone(jobId);
        if (result.status === "done") {
          doneCount++;
        } else {
          failedCount++;
        }
        setBatchStatus({ phase: "waiting", done: doneCount, total: jobIds.length, failed: failedCount });
      })
    );

    setBatchStatus(null);
    await refreshBalance();
  };

  const downloadZip = async (scope) => {
    let scoped = assets;
    if (scope === "image") scoped = assets.filter((a) => a.generation_type === "image");
    if (scope === "animation") scoped = assets.filter((a) => a.generation_type === "animation");
    if (scope === "sound") scoped = assets.filter((a) => a.generation_type === "sound");

    const jobIds = scoped.map((a) => a.jobId).filter(Boolean);

    if (jobIds.length === 0) {
      alert("No completed assets in this scope yet.");
      return;
    }

    setShowDownloadPicker(false);
    setBatchStatus({ phase: "zipping", done: 0, total: jobIds.length, failed: 0 });

    const res = await fetch(`${API_BASE}/export/zip`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_ids: jobIds }),
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${gameName || "assets"}_${scope}.zip`;
    a.click();
    URL.revokeObjectURL(url);

    setBatchStatus(null);
  };

  const visibleAssets = assets
    .map((asset, originalIndex) => ({ asset, originalIndex }))
    .filter(({ asset }) => asset.generation_type === activeTab);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Slot Asset Generator</h1>

      <div className="text-sm text-gray-500 mb-4">
        {typeof leonardoEstimatedUsd === "number" ? (
          <>Leonardo balance (estimated): <span className="font-semibold">${leonardoEstimatedUsd.toFixed(2)}</span></>
        ) : typeof leonardoBalance === "number" ? (
          <>Leonardo credits: <span className="font-semibold">{leonardoBalance.toLocaleString()}</span> (generate once to calibrate $ estimate)</>
        ) : null}
        {" · "}Spent this session: <span className="font-semibold">${sessionCost.toFixed(2)}</span>
        {" · "}
        <a href="https://app.leonardo.ai/api-access" target="_blank" rel="noreferrer" className="underline">
          Verify exact balance
        </a>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <input className="border rounded p-2" placeholder="Game name"
          value={gameName} onChange={(e) => setGameName(e.target.value)} />
        <input className="border rounded p-2" placeholder="Art style"
          value={artStyle} onChange={(e) => setArtStyle(e.target.value)} />
        <input className="border rounded p-2 col-span-2" placeholder="Palette, comma separated"
          value={palette} onChange={(e) => setPalette(e.target.value)} />
      </div>

      <div className="border rounded p-3 mb-4 bg-gray-50">
        <label className="text-sm font-semibold block mb-1">Game world / story (optional)</label>
        <textarea className="border rounded p-2 w-full mb-2" rows={2}
          placeholder="e.g. A forgotten desert kingdom where ancient pharaohs' treasures are sealed behind cursed golden vaults"
          value={masterPrompt} onChange={(e) => setMasterPrompt(e.target.value)} />
        <div className="flex gap-2 items-start mb-2">
          <textarea className="border rounded p-2 w-full" rows={2}
            placeholder="AI-enhanced world description (used as context for every block's Enhance button)"
            value={masterPromptEnhanced} onChange={(e) => setMasterPromptEnhanced(e.target.value)} />
          <button className="border rounded p-2 bg-gray-200 whitespace-nowrap" onClick={enhanceMasterPrompt}>
            Enhance ✨
          </button>
        </div>
        {(masterPromptEnhanced || masterPrompt) && assets.length > 0 && (
          <button className="border rounded p-2 bg-blue-500 text-white text-sm"
            onClick={() => {
              const confirmed = window.confirm(
                "This will regenerate prompts for ALL blocks, overwriting anything you've already written. Continue?"
              );
              if (confirmed) autoFillFromWorld();
            }}>
            Regenerate all from world ✨
          </button>
        )}
      </div>

      <div className="flex gap-2 items-center mb-4">
        <select
          className="border rounded p-2 flex-1"
          value={selectedThemeName}
          onChange={(e) => {
            setSelectedThemeName(e.target.value);
            if (e.target.value) loadTheme(e.target.value);
          }}
        >
          <option value="">— Load a saved theme —</option>
          {savedThemeNames.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        <button className="border rounded p-2 bg-gray-200" onClick={saveTheme}>
          Save current theme
        </button>
      </div>

      <div className="flex gap-1 mb-4 border-b">
        <button
          className={`px-4 py-2 font-semibold ${
            activeTab === "image" ? "border-b-2 border-blue-500 text-blue-600" : "text-gray-500"
          }`}
          onClick={() => setActiveTab("image")}
        >
          Images ({assets.filter((a) => a.generation_type === "image").length})
        </button>
        <button
          className={`px-4 py-2 font-semibold ${
            activeTab === "animation" ? "border-b-2 border-blue-500 text-blue-600" : "text-gray-500"
          }`}
          onClick={() => setActiveTab("animation")}
        >
          Animations ({assets.filter((a) => a.generation_type === "animation").length})
        </button>
        <button
          className={`px-4 py-2 font-semibold ${
            activeTab === "sound" ? "border-b-2 border-blue-500 text-blue-600" : "text-gray-500"
          }`}
          onClick={() => setActiveTab("sound")}
        >
          Sounds ({assets.filter((a) => a.generation_type === "sound").length})
        </button>
      </div>

      <div className="mb-4 flex gap-2 flex-wrap items-center">
        <button className="border rounded p-2 bg-gray-200" onClick={() => setShowPicker(true)}>
          + Add block
        </button>
        <button className="border rounded p-2 bg-gray-200" onClick={() => setShowFrameworkPicker(true)}>
          Load framework
        </button>
        <button className="border rounded p-2 bg-gray-200" onClick={() => setShowCreateFramework(true)}>
          + Create framework
        </button>
        <label className="border rounded p-2 bg-gray-200 cursor-pointer">
          Import framework
          <input type="file" accept="application/json" className="hidden"
            onChange={(e) => {
              const file = e.target.files[0];
              if (file) importFramework(file);
            }} />
        </label>
        <button
          className="border rounded p-2 bg-green-600 text-white disabled:opacity-50"
          onClick={generateAll}
          disabled={batchStatus !== null || assets.length === 0}
        >
          {batchStatus ? "Working..." : "Generate All"}
        </button>
        <button
          className="border rounded p-2 bg-gray-700 text-white disabled:opacity-50"
          onClick={() => setShowDownloadPicker(true)}
          disabled={batchStatus !== null || assets.length === 0}
        >
          Download ZIP
        </button>
        {batchStatus && (
          <span className="text-sm text-gray-500">
            {batchStatus.phase === "submitting" && `Submitting ${batchStatus.total} jobs...`}
            {batchStatus.phase === "waiting" &&
              `${batchStatus.done + batchStatus.failed}/${batchStatus.total} finished (${batchStatus.failed} failed)`}
            {batchStatus.phase === "zipping" && "Building ZIP..."}
          </span>
        )}
        <button
          className="border rounded p-2 bg-red-100 text-red-700 text-sm"
          onClick={() => {
            if (window.confirm("Clear all current work? This cannot be undone.")) {
              localStorage.removeItem(STORAGE_KEY);
              window.location.reload();
            }
          }}
        >
          Clear session
        </button>
      </div>

      {showPicker && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowPicker(false)}>
          <div className="bg-white rounded-lg p-6 w-[60vw] max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Choose a block</h3>
              <button className="text-gray-500" onClick={() => setShowPicker(false)}>✕</button>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {blueprints.map((b) => (
                <div key={b.key} className="border rounded p-3">
                  <div className="font-semibold mb-2">{b.display_name}</div>
                  <div className="flex gap-2">
                    {b.available_types.includes("image") && (
                      <button className="border rounded px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200"
                        onClick={() => addAssetFromBlueprint(b, "image")}>
                        + Image
                      </button>
                    )}
                    {b.available_types.includes("animation") && (
                      <button className="border rounded px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200"
                        onClick={() => addAssetFromBlueprint(b, "animation")}>
                        + Animation
                      </button>
                    )}
                    {b.available_types.includes("sound") && (
                      <button className="border rounded px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200"
                        onClick={() => addAssetFromBlueprint(b, "sound")}>
                        + Sound
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {showFrameworkPicker && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowFrameworkPicker(false)}>
          <div className="bg-white rounded-lg p-6 w-[50vw] max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Choose a framework</h3>
              <button className="text-gray-500" onClick={() => setShowFrameworkPicker(false)}>✕</button>
            </div>
            <div className="flex flex-col gap-2">
              {frameworks.map((f) => (
                <div key={f.key} className="border rounded p-3 flex justify-between items-start gap-2">
                  <button className="text-left flex-1 hover:bg-gray-50 -m-1 p-1 rounded"
                    onClick={() => loadFramework(f)}>
                    <div className="font-semibold">{f.display_name}</div>
                    <div className="text-sm text-gray-500">{f.description}</div>
                    <div className="text-xs text-gray-400 mt-1">
                      {f.blueprint_keys.length} blocks {f.is_builtin && "· built-in"}
                    </div>
                  </button>
                  <div className="flex flex-col gap-1 items-end">
                    <button className="text-sm text-blue-600 whitespace-nowrap"
                      onClick={() => exportFramework(f)}>
                      Export
                    </button>
                    {!f.is_builtin && (
                      <button className="text-sm text-red-600 whitespace-nowrap"
                        onClick={() => deleteFramework(f)}>
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {showCreateFramework && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowCreateFramework(false)}>
          <div className="bg-white rounded-lg p-6 w-[60vw] max-h-[80vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Create a framework</h3>
              <button className="text-gray-500" onClick={() => setShowCreateFramework(false)}>✕</button>
            </div>

            <input className="border rounded p-2 w-full mb-2" placeholder="Framework name"
              value={newFrameworkName} onChange={(e) => setNewFrameworkName(e.target.value)} />
            <input className="border rounded p-2 w-full mb-4" placeholder="Description"
              value={newFrameworkDescription} onChange={(e) => setNewFrameworkDescription(e.target.value)} />

            <div className="grid grid-cols-3 gap-2 mb-4">
              {blueprints.map((b) => (
                <div key={b.key} className="border rounded p-2 flex justify-between items-center">
                  <span className="text-sm">{b.display_name}</span>
                  <div className="flex items-center gap-1">
                    <button className="border rounded w-6 h-6"
                      onClick={() => adjustFrameworkCount(b.key, -1)}>-</button>
                    <span className="w-4 text-center text-sm">{newFrameworkCounts[b.key] || 0}</span>
                    <button className="border rounded w-6 h-6"
                      onClick={() => adjustFrameworkCount(b.key, 1)}>+</button>
                  </div>
                </div>
              ))}
            </div>

            <button className="border rounded p-2 bg-blue-500 text-white w-full"
              onClick={saveNewFramework}>
              Save framework
            </button>
          </div>
        </div>
      )}

      {showDownloadPicker && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onClick={() => setShowDownloadPicker(false)}>
          <div className="bg-white rounded-lg p-6 w-[30vw]"
            onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Download ZIP</h3>
              <button className="text-gray-500" onClick={() => setShowDownloadPicker(false)}>✕</button>
            </div>
            <div className="flex flex-col gap-2">
              <button className="border rounded p-2 bg-gray-100 hover:bg-gray-200"
                onClick={() => downloadZip("image")}>
                All images
              </button>
              <button className="border rounded p-2 bg-gray-100 hover:bg-gray-200"
                onClick={() => downloadZip("animation")}>
                All animations
              </button>
              <button className="border rounded p-2 bg-gray-100 hover:bg-gray-200"
                onClick={() => downloadZip("sound")}>
                All sounds
              </button>
              <button className="border rounded p-2 bg-gray-100 hover:bg-gray-200"
                onClick={() => downloadZip("all")}>
                Everything
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-6 gap-3">
        {visibleAssets.map(({ asset, originalIndex }) => (
          <AssetCard
            key={asset.uniqueId || originalIndex}
            asset={asset}
            index={originalIndex}
            updateAsset={updateAsset}
            enhancePrompt={enhancePrompt}
            submitAsset={submitAsset}
            imageModels={imageModels}
            animationModels={animationModels}
            soundModels={soundModels}
            onAssetDone={handleAssetDone}
          />
        ))}
      </div>

      {visibleAssets.length === 0 && (
        <div className="text-gray-400 text-sm mt-8 text-center">
          No {activeTab} assets yet — click "+ Add block" above.
        </div>
      )}

      {worldFillStatus && (
        <div className="fixed bottom-4 right-4 bg-white border shadow-lg rounded-lg p-4 w-80 z-40">
          {worldFillStatus.finished ? (
            <div className="text-sm font-semibold text-green-600">
              ✓ Done — {worldFillStatus.done}/{worldFillStatus.total} processed
              {worldFillStatus.skipped > 0 && ` (${worldFillStatus.skipped} skipped, see console)`}
            </div>
          ) : (
            <>
              <div className="text-sm font-semibold mb-1">
                Regenerating from world... {worldFillStatus.done}/{worldFillStatus.total}
              </div>
              {worldFillStatus.currentName && (
                <div className="text-xs text-gray-500 mb-2 truncate">
                  Working on: {worldFillStatus.currentName}
                </div>
              )}
              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                <div
                  className="h-2 bg-blue-500 rounded-full transition-all duration-300"
                  style={{ width: `${(worldFillStatus.done / worldFillStatus.total) * 100}%` }}
                />
              </div>
            </>
          )}
        </div>
      )}

      {outOfCreditsService && (
        <OutOfCreditsModal
          service={outOfCreditsService}
          onClose={() => setOutOfCreditsService(null)}
        />
      )}
    </div>
  );
}