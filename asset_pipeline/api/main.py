import os
import uuid
from fastapi import Form
from fastapi import UploadFile, File
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from asset_pipeline.domain.job import JobStatus
from asset_pipeline.domain.asset_blueprint import BLUEPRINT_LIBRARY
from asset_pipeline.generation.prompt_enhancer import HuggingFacePromptEnhancer, category_needs_isolation
from asset_pipeline.config.settings import HUGGINGFACE_API_KEY
from asset_pipeline.api.schemas import EnhancePromptRequest, EnhancePromptResponse
from asset_pipeline.api.schemas import CreateAssetRequest, SaveThemeRequest
from asset_pipeline.domain.theme_factory import theme_from_request
from asset_pipeline.domain.theme_serializer import theme_to_dict
from asset_pipeline.domain.theme import GenerationType
from asset_pipeline.generation.factory import GenerationProviderFactory
from asset_pipeline.generation.prompt_builder import LeonardoPromptBuilder
from asset_pipeline.generation.model_catalog import models_for_type, find_model
from asset_pipeline.postprocessing.config import PostProcessingConfig
from asset_pipeline.postprocessing.frame_pipeline import build_frame_pipeline
from asset_pipeline.orchestration.asset_pipeline import AssetGenerationPipeline
from asset_pipeline.orchestration.job_repository import InMemoryJobRepository
from asset_pipeline.orchestration.job_broadcaster import JobEventBroadcaster
from asset_pipeline.orchestration.job_runner import AssetJobRunner
from asset_pipeline.domain.job import AssetJob
from asset_pipeline.config.theme_repository import JsonFileThemeRepository
from asset_pipeline.config.settings import LEONARDO_API_KEY

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("output", exist_ok=True)
app.mount("/output", StaticFiles(directory="output"), name="output")
os.makedirs("reference_images", exist_ok=True)
app.mount("/reference_images", StaticFiles(directory="reference_images"), name="reference_images")

repository = InMemoryJobRepository()
broadcaster = JobEventBroadcaster()
theme_repository = JsonFileThemeRepository()

API_KEYS_BY_PROVIDER = {
    "leonardo": LEONARDO_API_KEY,
}


def build_pipeline(model_id: str) -> AssetGenerationPipeline:
    model_option = find_model(model_id)
    api_key = API_KEYS_BY_PROVIDER[model_option.provider]
    provider = GenerationProviderFactory.create(model_option.provider, api_key=api_key, model_id=model_id)
    frame_pipeline = build_frame_pipeline(PostProcessingConfig())
    return AssetGenerationPipeline(LeonardoPromptBuilder(), provider, frame_pipeline)


@app.post("/assets")
async def create_asset(payload: CreateAssetRequest, background_tasks: BackgroundTasks):
    theme = theme_from_request(payload.theme)
    asset = next(a for a in theme.assets if a.name == payload.asset_name)

    job = AssetJob(asset_name=asset.name, theme_name=theme.name)
    repository.save(job)

    pipeline = build_pipeline(payload.model_id)
    runner = AssetJobRunner(pipeline, repository, broadcaster)
    background_tasks.add_task(runner.run, job, theme, asset)

    return {"job_id": job.id}


@app.get("/assets")
def list_assets():
    return [job.__dict__ for job in repository.list_all()]


@app.get("/models")
def list_models():
    return {
        "image": [
            {"name": m.display_name, "model_id": m.model_id}
            for m in models_for_type(GenerationType.IMAGE)
        ],
        "animation": [
            {"name": m.display_name, "model_id": m.model_id}
            for m in models_for_type(GenerationType.ANIMATION)
        ],
    }


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


@app.websocket("/ws/assets/{job_id}")
async def asset_updates(websocket: WebSocket, job_id: str):
    await websocket.accept()
    broadcaster.subscribe(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        broadcaster.unsubscribe(job_id, websocket)

@app.post("/prompts/enhance", response_model=EnhancePromptResponse)
def enhance_prompt(payload: EnhancePromptRequest):
    enhancer = HuggingFacePromptEnhancer(api_token=HUGGINGFACE_API_KEY)
    enhanced = enhancer.enhance(
        payload.base_prompt,
        payload.art_style,
        payload.palette,
        is_animation=payload.is_animation,
        needs_isolation=category_needs_isolation(payload.category),
    )
    return EnhancePromptResponse(enhanced_prompt=enhanced)

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

@app.post("/uploads/reference-image")
async def upload_reference_image(file: UploadFile = File(...)):
    extension = os.path.splitext(file.filename)[1] or ".png"
    filename = f"{uuid.uuid4()}{extension}"
    path = f"reference_images/{filename}"

    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)

    return {"path": path}

@app.post("/assets/import")
async def import_asset(
    name: str = Form(...),
    category: str = Form(...),
    generation_type: str = Form("image"),
    file: UploadFile = File(...),
):
    extension = os.path.splitext(file.filename)[1] or ".png"
    filename = f"{uuid.uuid4()}{extension}"
    path = f"output/{filename}"

    contents = await file.read()
    with open(path, "wb") as f:
        f.write(contents)

    job = AssetJob(asset_name=name, theme_name="imported")
    job.status = JobStatus.DONE
    job.result_paths = [path]
    repository.save(job)

    return {"job_id": job.id, "result_paths": job.result_paths}