import { useEffect, useState } from "react";
import AssetCard from "./AssetCard";

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
};

export default function App() {
  const [gameName, setGameName] = useState("");
  const [artStyle, setArtStyle] = useState("");
  const [palette, setPalette] = useState("");
  const [assets, setAssets] = useState([]);
  const [savedThemeNames, setSavedThemeNames] = useState([]);
  const [selectedThemeName, setSelectedThemeName] = useState("");
  const [imageModels, setImageModels] = useState([]);
  const [animationModels, setAnimationModels] = useState([]);
  const [activeTab, setActiveTab] = useState("image");
  const [blueprints, setBlueprints] = useState([]);
  const [showPicker, setShowPicker] = useState(false);

  useEffect(() => {
    refreshThemeList();
    refreshModelList();
    refreshBlueprints();
  }, []);

  const refreshModelList = async () => {
    const res = await fetch("http://localhost:8000/models");
    const data = await res.json();
    setImageModels(data.image);
    setAnimationModels(data.animation);
  };

  const refreshBlueprints = async () => {
    const res = await fetch("http://localhost:8000/blueprints");
    setBlueprints(await res.json());
  };

  const updateAsset = (index, field, value) => {
    setAssets((prev) =>
      prev.map((a, i) => (i === index ? { ...a, [field]: value } : a))
    );
  };

  const addAssetFromBlueprint = (blueprint, generationType) => {
    const existingCount = assets.filter((a) => a.blueprintKey === blueprint.key).length;
    setAssets((prev) => [
      ...prev,
      {
        ...emptyAsset,
        name: existingCount > 0 ? `${blueprint.key}_${existingCount + 1}` : blueprint.key,
        category: blueprint.category,
        generation_type: generationType,
        role_constant: blueprint.role_constant,
        blueprintKey: blueprint.key,
        num_outputs: blueprint.default_num_outputs,
        duration_seconds: blueprint.default_duration_seconds ?? 4,
      },
    ]);
  
    setShowPicker(false);
    setActiveTab(generationType);
  };

  const buildThemePayload = () => ({
    name: gameName,
    art_style: artStyle,
    palette: palette.split(",").map((p) => p.trim()).filter(Boolean),
    assets: assets.map((a) => ({
      name: a.name,
      category: a.category,
      description: a.description,
      enhanced_prompt: a.enhanced_prompt || null,
      role_constant: a.role_constant || null,
      style_keywords: a.style_keywords.split(",").map((k) => k.trim()).filter(Boolean),
      reference_image_path: a.reference_image_path || null,
      settings: {
        generation_type: a.generation_type,
        width: Number(a.width),
        height: Number(a.height),
        duration_seconds: a.generation_type === "animation" ? Number(a.duration_seconds) : null,
        num_outputs: Number(a.num_outputs),
      },
    })),
  });

  const refreshThemeList = async () => {
    const res = await fetch("http://localhost:8000/themes");
    setSavedThemeNames(await res.json());
  };

  const saveTheme = async () => {
    const theme = buildThemePayload();
    await fetch("http://localhost:8000/themes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ theme }),
    });
    await refreshThemeList();
  };

  const loadTheme = async (name) => {
    const res = await fetch(`http://localhost:8000/themes/${name}`);
    const theme = await res.json();
    setGameName(theme.name);
    setArtStyle(theme.art_style);
    setPalette(theme.palette.join(", "));
    setAssets(
      theme.assets.map((a) => ({
        name: a.name,
        category: a.category,
        description: a.description,
        enhanced_prompt: a.enhanced_prompt || "",
        role_constant: a.role_constant || null,
        blueprintKey: null,
        style_keywords: a.style_keywords.join(", "),
        generation_type: a.settings.generation_type,
        model_id: "",
        width: a.settings.width,
        height: a.settings.height,
        duration_seconds: a.settings.duration_seconds ?? 4,
        num_outputs: a.settings.num_outputs,
        jobId: null,
        reference_image_path: a.reference_image_path || null,
      }))
    );
  };

  const enhancePrompt = async (index) => {
    const asset = assets[index];
    const res = await fetch("http://localhost:8000/prompts/enhance", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        base_prompt: asset.description,
        art_style: artStyle,
        palette: palette.split(",").map((p) => p.trim()).filter(Boolean),
        category: asset.category,
        is_animation: asset.generation_type === "animation",
      }),
    });
    const data = await res.json();
    updateAsset(index, "enhanced_prompt", data.enhanced_prompt);
  };

  const submitAsset = async (index) => {
    const assetForm = assets[index];
    const theme = buildThemePayload();

    const res = await fetch("http://localhost:8000/assets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        theme,
        asset_name: assetForm.name,
        model_id: assetForm.model_id,
      }),
    });
    const data = await res.json();
    updateAsset(index, "jobId", data.job_id);
  };

  const visibleAssets = assets
    .map((asset, originalIndex) => ({ asset, originalIndex }))
    .filter(({ asset }) => asset.generation_type === activeTab);

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Slot Asset Generator</h1>

      <div className="grid grid-cols-2 gap-4 mb-4">
        <input className="border rounded p-2" placeholder="Game name"
          value={gameName} onChange={(e) => setGameName(e.target.value)} />
        <input className="border rounded p-2" placeholder="Art style"
          value={artStyle} onChange={(e) => setArtStyle(e.target.value)} />
        <input className="border rounded p-2 col-span-2" placeholder="Palette, comma separated"
          value={palette} onChange={(e) => setPalette(e.target.value)} />
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
            activeTab === "image"
              ? "border-b-2 border-blue-500 text-blue-600"
              : "text-gray-500"
          }`}
          onClick={() => setActiveTab("image")}
        >
          Images ({assets.filter((a) => a.generation_type === "image").length})
        </button>
        <button
          className={`px-4 py-2 font-semibold ${
            activeTab === "animation"
              ? "border-b-2 border-blue-500 text-blue-600"
              : "text-gray-500"
          }`}
          onClick={() => setActiveTab("animation")}
        >
          Animations ({assets.filter((a) => a.generation_type === "animation").length})
        </button>
      </div>

      <div className="mb-4">
        <button className="border rounded p-2 bg-gray-200" onClick={() => setShowPicker(true)}>
          + Add block
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
          <button
            className="border rounded px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200"
            onClick={() => addAssetFromBlueprint(b, "image")}
          >
            + Image
          </button>
        )}
        {b.available_types.includes("animation") && (
          <button
            className="border rounded px-2 py-1 text-sm bg-gray-100 hover:bg-gray-200"
            onClick={() => addAssetFromBlueprint(b, "animation")}
          >
            + Animation
          </button>
        )}
      </div>
    </div>
  ))}
</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-6 gap-3">
        {visibleAssets.map(({ asset, originalIndex }) => (
          <AssetCard
            key={originalIndex}
            asset={asset}
            index={originalIndex}
            updateAsset={updateAsset}
            enhancePrompt={enhancePrompt}
            submitAsset={submitAsset}
            imageModels={imageModels}
            animationModels={animationModels}
          />
        ))}
      </div>

      {visibleAssets.length === 0 && (
        <div className="text-gray-400 text-sm mt-8 text-center">
          No {activeTab === "image" ? "image" : "animation"} assets yet — click "+ Add block" above.
        </div>
      )}
    </div>
  );
}