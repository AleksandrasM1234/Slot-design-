import time
import json
import os
import requests
from asset_pipeline.generation.base import (
    ImageGenerationProvider, GenerationRequest, GenerationResult
)
from asset_pipeline.domain.theme import GenerationType
from asset_pipeline.generation.model_catalog import ModelOption
from asset_pipeline.generation.resolution_resolver import resolve_generation_size


class LeonardoProvider(ImageGenerationProvider):

    BASE_URL = "https://cloud.leonardo.ai/api/rest"

    def __init__(self, api_key: str, model: ModelOption,
                 poll_interval: float = 2.0, timeout: float = 180.0):
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._model = model
        self._poll_interval = poll_interval
        self._timeout = timeout

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if self._model.generation_type == GenerationType.ANIMATION:
            if self._model.api_version == "v2":
                return self._generate_video_v2(request)
            raise NotImplementedError(
                f"v1 video generation for model {self._model.model_id} is not implemented."
            )
        if self._model.api_version == "v2":
            return self._generate_image_v2(request)
        return self._generate_image_v1(request)

    def _upload_reference_image(self, local_path: str) -> str:
        extension = os.path.splitext(local_path)[1].lstrip(".") or "png"

        init_response = requests.post(
            f"{self.BASE_URL}/v1/init-image",
            json={"extension": extension},
            headers=self._headers,
        )
        init_response.raise_for_status()
        init_data = init_response.json()["uploadInitImage"]

        upload_url = init_data["url"]
        upload_fields = json.loads(init_data["fields"])
        image_id = init_data["id"]

        with open(local_path, "rb") as f:
            upload_response = requests.post(
                upload_url,
                data=upload_fields,
                files={"file": f},
            )
        upload_response.raise_for_status()

        return image_id

    # -------------------- v1 image (legacy models, e.g. FLUX Dev) --------------------

    def _generate_image_v1(self, request: GenerationRequest) -> GenerationResult:
        width, height = resolve_generation_size(request.width, request.height, self._model)

        init_image_id = None
        if request.reference_image_path:
            init_image_id = self._upload_reference_image(request.reference_image_path)

        payload = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "modelId": self._model.model_id,
            "width": width,
            "height": height,
            "num_images": request.num_outputs,
        }
        if init_image_id:
            payload["init_image_id"] = init_image_id
            payload["init_strength"] = 0.55

        response = requests.post(
            f"{self.BASE_URL}/v1/generations",
            json=payload,
            headers=self._headers,
        )
        response.raise_for_status()
        generation_id = response.json()["sdGenerationJob"]["generationId"]
        return self._poll_v1(generation_id)

    def _poll_v1(self, generation_id: str) -> GenerationResult:
        elapsed = 0.0
        while elapsed < self._timeout:
            response = requests.get(
                f"{self.BASE_URL}/v1/generations/{generation_id}",
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()
            generation = data["generations_by_pk"]

            if generation["status"] == "COMPLETE":
                urls = tuple(img["url"] for img in generation["generated_images"])
                return GenerationResult(asset_urls=urls, provider_name="leonardo", raw_response=data)
            if generation["status"] == "FAILED":
                raise RuntimeError(f"Leonardo v1 generation failed: {data}")

            time.sleep(self._poll_interval)
            elapsed += self._poll_interval

        raise TimeoutError(f"Generation {generation_id} timed out")

    # -------------------- v2 image (Nano Banana 2, FLUX.2 Pro, etc.) --------------------

    def _generate_image_v2(self, request: GenerationRequest) -> GenerationResult:
        width, height = resolve_generation_size(request.width, request.height, self._model)

        parameters = {
            "prompt": request.prompt,
            "width": width,
            "height": height,
            "quantity": request.num_outputs,
        }

        if request.reference_image_path:
            image_id = self._upload_reference_image(request.reference_image_path)
            parameters["guidances"] = {
                "image_reference": [
                    {"image": {"id": image_id, "type": "UPLOADED"}, "strength": "MID"}
                ]
            }

        payload = {"model": self._model.model_id, "public": False, "parameters": parameters}
        return self._submit_and_poll_v2(payload)

    # -------------------- v2 video (Kling 3.0, etc.) --------------------

    def _generate_video_v2(self, request: GenerationRequest) -> GenerationResult:
        width, height = resolve_generation_size(request.width, request.height, self._model)

        parameters = {
            "prompt": request.prompt,
            "width": width,
            "height": height,
            "duration": request.duration_seconds or 5,
            "mode": self._model.video_mode or "RESOLUTION_720",
            "motion_has_audio": False,
        }

        if request.reference_image_path:
            image_id = self._upload_reference_image(request.reference_image_path)
            parameters["guidances"] = {
                "start_frame": [{"image": {"id": image_id, "type": "UPLOADED"}}]
            }

        payload = {"model": self._model.model_id, "public": False, "parameters": parameters}
        return self._submit_and_poll_v2(payload)

    # -------------------- shared v2 submit/poll --------------------

    def _submit_and_poll_v2(self, payload: dict) -> GenerationResult:
        response = requests.post(
            f"{self.BASE_URL}/v2/generations",
            json=payload,
            headers=self._headers,
        )
        response.raise_for_status()
        data = response.json()
        generation_id = data.get("id") or data.get("generationId")
        if not generation_id:
            raise RuntimeError(
                f"Could not find a generation id in the v2 response — verify the actual "
                f"field name against Leonardo's docs. Raw response: {data}"
            )
        return self._poll_v2(generation_id)

    def _poll_v2(self, generation_id: str) -> GenerationResult:
        elapsed = 0.0
        while elapsed < self._timeout:
            response = requests.get(
                f"{self.BASE_URL}/v2/generations/{generation_id}",
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()

            status = data.get("status")
            if status == "COMPLETE":
                urls = tuple(item["url"] for item in data.get("outputs", data.get("generated_images", [])))
                return GenerationResult(asset_urls=urls, provider_name="leonardo", raw_response=data)
            if status == "FAILED":
                raise RuntimeError(f"Leonardo v2 generation failed: {data}")

            time.sleep(self._poll_interval)
            elapsed += self._poll_interval

        raise TimeoutError(f"Generation {generation_id} timed out")