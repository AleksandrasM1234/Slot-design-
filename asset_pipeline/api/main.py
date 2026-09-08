import os
import uuid
import io
import zipfile
from PIL import Image
from asset_pipeline.postprocessing.config import PostProcessingConfig
from asset_pipeline.postprocessing.frame_pipeline import build_frame_pipeline, build_reprocess_pipeline
from asset_pipeline.api.schemas import ReprocessRequest
from fastapi.responses import StreamingResponse
from asset_pipeline.generation.model_catalog import models_for_type, find_model
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from asset_pipeline.config.paths import (
    OUTPUT_DIR, REFERENCE_IMAGES_DIR, ensure_data_dirs
)
from asset_pipeline.api.schemas import (
    CreateAssetRequest, SaveThemeRequest, EnhancePromptRequest,
    EnhancePromptResponse, SaveFrameworkRequest, EnhanceMasterPromptRequest, GenerateFromWorldRequest, ExportZipRequest
)
from asset_pipeline.config.exchange_rate import record_observation, get_usd_per_credit
from asset_pipeline.generation.leonardo_provider import LeonardoProvider
from asset_pipeline.generation.model_catalog import IMAGE_MODELS
from asset_pipeline.domain.theme_factory import theme_from_request
from asset_pipeline.domain.theme_serializer import theme_to_dict
from asset_pipeline.domain.theme import GenerationType
from asset_pipeline.domain.job import AssetJob, JobStatus
from asset_pipeline.domain.asset_blueprint import BLUEPRINT_LIBRARY
from asset_pipeline.domain.framework_preset import FrameworkPreset, FRAMEWORK_PRESETS
from asset_pipeline.generation.factory import GenerationProviderFactory
from asset_pipeline.generation.prompt_builder import LeonardoPromptBuilder
from asset_pipeline.generation.prompt_enhancer import GroqPromptEnhancer, category_needs_isolation
from asset_pipeline.generation.model_catalog import models_for_type, find_model
from asset_pipeline.postprocessing.config import PostProcessingConfig
from asset_pipeline.postprocessing.frame_pipeline import build_frame_pipeline
from asset_pipeline.orchestration.asset_pipeline import AssetGenerationPipeline
from asset_pipeline.orchestration.job_repository import JsonFileJobRepository
from asset_pipeline.orchestration.job_broadcaster import JobEventBroadcaster
from asset_pipeline.orchestration.job_runner import AssetJobRunner
from asset_pipeline.config.theme_repository import JsonFileThemeRepository
from asset_pipeline.config.framework_repository import JsonFileFrameworkRepository
from asset_pipeline.config.settings import LEONARDO_API_KEY, GROQ_API_KEY, ALLOWED_ORIGINS
from asset_pipeline.config.paths import OUTPUT_DIR, REFERENCE_IMAGES_DIR, ensure_data_dirs


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ensure_data_dirs()
app.mount("/data/output", StaticFiles(directory=OUTPUT_DIR), name="output")
app.mount("/data/reference_images", StaticFiles(directory=REFERENCE_IMAGES_DIR), name="reference_images")

repository = JsonFileJobRepository()
broadcaster = JobEventBroadcaster()
theme_repository = JsonFileThemeRepository()
framework_repository = JsonFileFrameworkRepository()

API_KEYS_BY_PROVIDER = {
    "leonardo": LEONARDO_API_KEY,
}


def build_pipeline(model_id: str, target_width: int, target_height: int,
                    chroma_color: str = "green") -> AssetGenerationPipeline:
    model_option = find_model(model_id)
    api_key = API_KEYS_BY_PROVIDER[model_option.provider]
    provider = GenerationProviderFactory.create(model_option.provider, api_key=api_key, model=model_option)
    frame_pipeline = build_frame_pipeline(
        PostProcessingConfig(chroma=chroma_color), target_width, target_height
    )
    return AssetGenerationPipeline(LeonardoPromptBuilder(), provider, frame_pipeline)


@app.post("/assets")
async def create_asset(payload: CreateAssetRequest, background_tasks: BackgroundTasks):
    theme = theme_from_request(payload.theme)

    if payload.unique_id:
        asset = next((a for a in theme.assets if a.unique_id == payload.unique_id), None)
        if asset is None:
            raise HTTPException(status_code=404, detail="Asset not found by unique_id.")
    else:
        matching = [a for a in theme.assets if a.name == payload.asset_name]
        if not matching:
            raise HTTPException(status_code=404, detail="Asset not found by name.")
        asset = matching[0]
        
    job = AssetJob(asset_name=asset.name, theme_name=theme.name)
    repository.save(job)

    pipeline = build_pipeline(
    payload.model_id, asset.settings.width, asset.settings.height, asset.chroma_color
    )
    def check_credits():
        provider = LeonardoProvider(api_key=LEONARDO_API_KEY, model=IMAGE_MODELS[0])
        return provider.get_remaining_balance()["credits_remaining"]

    runner = AssetJobRunner(
    pipeline, repository, broadcaster,
    credits_checker=check_credits, rate_tracker=record_observation,
)
    background_tasks.add_task(runner.run, job, theme, asset)

    return {"job_id": job.id}


@app.post("/assets/import")
async def import_asset(
    name: str = Form(...),
    category: str = Form(...),
    generation_type: str = Form("image"),
    file: UploadFile = File(...),
):
    extension = os.path.splitext(file.filename)[1] or ".png"
    filename = f"{uuid.uuid4()}{extension}"
    path = f"{OUTPUT_DIR}/{filename}"

    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)

    job = AssetJob(asset_name=name, theme_name="imported")
    job.status = JobStatus.DONE
    job.result_paths = [path]
    repository.save(job)

    return {"job_id": job.id, "result_paths": job.result_paths}


@app.get("/assets")
def list_assets():
    return [job.__dict__ for job in repository.list_all()]

def _serialize_model(m):
    return {
        "name": m.display_name,
        "model_id": m.model_id,
        "resolution_mode": m.resolution_mode,
        "valid_resolutions": [
            {"width": w, "height": h, "ratio": label}
            for w, h, _, label in m.valid_resolutions
        ],
        "min_width": m.min_width,
        "max_width": m.max_width,
        "min_height": m.min_height,
        "max_height": m.max_height,
        "step": m.step,
        "min_duration": m.min_duration,
        "max_duration": m.max_duration,
        "reference_cost_usd": m.reference_cost_usd,
        "reference_note": m.reference_note,
        "reference_width": m.reference_width,
        "reference_height": m.reference_height,
        "reference_duration": m.reference_duration,
    }

@app.post("/export/zip")
def export_zip(payload: ExportZipRequest):
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for job_id in payload.job_ids:
            job = repository.get(job_id)
            if not job or job.status != JobStatus.DONE:
                continue

            for idx, path in enumerate(job.result_paths):
                if not os.path.exists(path):
                    continue
                extension = os.path.splitext(path)[1]
                suffix = f"_{idx}" if len(job.result_paths) > 1 else ""
                arcname = f"{job.asset_name}{suffix}{extension}"
                zf.write(path, arcname=arcname)

    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=assets.zip"},
    )

@app.get("/models")
def list_models():
    return {
        "image": [_serialize_model(m) for m in models_for_type(GenerationType.IMAGE)],
        "animation": [_serialize_model(m) for m in models_for_type(GenerationType.ANIMATION)],
    }


@app.get("/blueprints")
def list_blueprints():
    return [
        {
            "key": b.key,
            "display_name": b.display_name,
            "role_constant": b.role_constant,
            "category": b.category.value,
            "available_types": [t.value for t in b.available_types],
            "default_num_outputs": b.default_num_outputs,
            "default_duration_seconds": b.default_duration_seconds,
        }
        for b in BLUEPRINT_LIBRARY
    ]


@app.get("/frameworks")
def list_frameworks():
    builtin_keys = {p.key for p in FRAMEWORK_PRESETS}
    all_presets = list(FRAMEWORK_PRESETS) + framework_repository.list_all()
    return [
        {
            "key": p.key,
            "display_name": p.display_name,
            "description": p.description,
            "blueprint_keys": list(p.blueprint_keys),
            "is_builtin": p.key in builtin_keys,
        }
        for p in all_presets
    ]


@app.post("/frameworks")
def save_framework(payload: SaveFrameworkRequest):
    preset = FrameworkPreset(
        key=payload.key,
        display_name=payload.display_name,
        description=payload.description,
        blueprint_keys=tuple(payload.blueprint_keys),
    )
    framework_repository.save(preset)
    return {"status": "saved", "key": preset.key}


@app.post("/uploads/reference-image")
async def upload_reference_image(file: UploadFile = File(...)):
    extension = os.path.splitext(file.filename)[1] or ".png"
    filename = f"{uuid.uuid4()}{extension}"
    path = f"{REFERENCE_IMAGES_DIR}/{filename}"

    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)

    return {"path": path}


@app.post("/prompts/enhance", response_model=EnhancePromptResponse)
def enhance_prompt(payload: EnhancePromptRequest):
    enhancer = GroqPromptEnhancer(api_key=GROQ_API_KEY)
    try:
        enhanced, chroma_color = enhancer.enhance(
            payload.base_prompt,
            payload.art_style,
            payload.palette,
            is_animation=payload.is_animation,
            needs_isolation=category_needs_isolation(payload.category),
            master_context=payload.master_context,
            role_constant=payload.role_constant,
            has_reference_image=payload.has_reference_image,
            text_content=payload.text_content,
        )
    except Exception as exc:
        error_text = str(exc).lower()
        if "429" in error_text or "rate_limit" in error_text or "insufficient_quota" in error_text or "quota" in error_text:
            raise HTTPException(status_code=429, detail=f"GROQ_OUT_OF_CREDITS: {exc}")
        raise HTTPException(status_code=502, detail=f"Prompt enhancement failed: {exc}")


@app.post("/prompts/enhance-master", response_model=EnhancePromptResponse)
def enhance_master_prompt(payload: EnhanceMasterPromptRequest):
    enhancer = GroqPromptEnhancer(api_key=GROQ_API_KEY)
    try:
        enhanced = enhancer.enhance_master(payload.base_prompt, payload.art_style, payload.palette)
    except Exception as exc:
        error_text = str(exc).lower()
        if "429" in error_text or "rate_limit" in error_text or "insufficient_quota" in error_text or "quota" in error_text:
            raise HTTPException(status_code=429, detail=f"GROQ_OUT_OF_CREDITS: {exc}")
        raise HTTPException(status_code=502, detail=f"Prompt enhancement failed: {exc}")
    return EnhancePromptResponse(enhanced_prompt=enhanced)

@app.post("/themes")
def save_theme(payload: SaveThemeRequest):
    theme = theme_from_request(payload.theme)
    theme_repository.save(theme)
    return {"status": "saved", "name": theme.name}


@app.get("/themes")
def list_themes():
    return theme_repository.list_names()


@app.get("/themes/{name}")
def get_theme(name: str):
    theme = theme_repository.load(name)
    return theme_to_dict(theme)

@app.get("/leonardo/balance")
def get_leonardo_balance():
    provider = LeonardoProvider(api_key=LEONARDO_API_KEY, model=IMAGE_MODELS[0])
    try:
        result = provider.get_remaining_balance()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Could not fetch Leonardo balance: {exc}")

    rate = get_usd_per_credit()
    result["estimated_usd"] = round(result["credits_remaining"] * rate, 2)
    return result
@app.get("/leonardo/session-cost")
def get_session_cost():
    total = sum(j.cost_usd or 0 for j in repository.list_all())
    return {"total_usd": round(total, 4)}

@app.websocket("/ws/assets/{job_id}")
async def asset_updates(websocket: WebSocket, job_id: str):
    await websocket.accept()
    broadcaster.subscribe(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.unsubscribe(job_id, websocket)

@app.delete("/frameworks/{key}")
def delete_framework(key: str):
    is_builtin = any(p.key == key for p in FRAMEWORK_PRESETS)
    if is_builtin:
        raise HTTPException(status_code=400, detail="Cannot delete a built-in framework.")

    deleted = framework_repository.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Framework not found.")

    return {"status": "deleted", "key": key}

@app.post("/prompts/generate-from-world", response_model=EnhancePromptResponse)
def generate_from_world(payload: GenerateFromWorldRequest):
    enhancer = GroqPromptEnhancer(api_key=GROQ_API_KEY)
    try:
        generated, chroma_color = enhancer.generate_from_world(
            payload.role_display_name,
            payload.master_context,
            payload.art_style,
            payload.palette,
            is_animation=payload.is_animation,
            needs_isolation=category_needs_isolation(payload.category),
            text_content=payload.text_content,
        )
    except Exception as exc:
        error_text = str(exc).lower()
        if "429" in error_text or "rate_limit" in error_text or "insufficient_quota" in error_text or "quota" in error_text:
            raise HTTPException(status_code=429, detail=f"GROQ_OUT_OF_CREDITS: {exc}")
        raise HTTPException(status_code=502, detail=f"Prompt generation failed: {exc}")
    return EnhancePromptResponse(enhanced_prompt=generated, chroma_color=chroma_color)

@app.get("/assets/{job_id}")
def get_asset(job_id: str):
    job = repository.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return {
        "id": job.id,
        "status": job.status.value,
        "result_paths": job.result_paths,
        "video_path": job.video_path,
        "error": job.error,
    }

@app.get("/api/output-files")
def list_output_files():
    files = sorted(os.listdir(OUTPUT_DIR))
    return [
        {"path": f"{OUTPUT_DIR}/{f}", "filename": f}
        for f in files
        if os.path.isfile(f"{OUTPUT_DIR}/{f}")
    ]

@app.get("/leonardo/session-cost")
def get_session_cost():
    total = sum(j.cost_usd or 0 for j in repository.list_all())
    return {"total_usd": round(total, 4)}

@app.post("/assets/{job_id}/reprocess")
def reprocess_asset(job_id: str, payload: ReprocessRequest):
    job = repository.get(job_id)
    if not job or not job.raw_paths or payload.index >= len(job.raw_paths):
        raise HTTPException(status_code=404, detail="Raw asset not found for reprocessing.")

    raw_image = Image.open(job.raw_paths[payload.index]).convert("RGBA")

    config = PostProcessingConfig(
        edge_tolerance=payload.edge_tolerance,
        interior_tolerance=payload.interior_tolerance,
        soft_edge_margin=payload.soft_edge_margin,
        feather_radius=payload.feather_radius,
        chroma=payload.chroma,
        removal_mode=payload.removal_mode,
        ml_model=payload.ml_model,
        upscale_strategy=payload.upscale_strategy,
        scale_factor=payload.scale_factor,
    )
    pipeline = build_reprocess_pipeline(config)
    processed = pipeline.run(raw_image)

    if payload.commit:
        target_path = job.result_paths[payload.index]
        processed.save(target_path)
        return {"path": target_path, "committed": True}

    preview_path = f"{OUTPUT_DIR}/{job_id}_preview_{payload.index}.png"
    processed.save(preview_path)
    return {"path": preview_path, "committed": False}