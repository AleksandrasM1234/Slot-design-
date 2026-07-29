import time
import os
import requests
from asset_pipeline.generation.base import (
    ImageGenerationProvider, GenerationRequest, GenerationResult
)
from asset_pipeline.domain.theme import GenerationType


class LeonardoProvider(ImageGenerationProvider):

    BASE_URL = "https://cloud.leonardo.ai/api/rest/v1"

    def __init__(self, api_key: str, model_id: str, poll_interval: float = 2.0,
                 timeout: float = 120.0):
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._model_id = model_id
        self._poll_interval = poll_interval
        self._timeout = timeout

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if request.generation_type == GenerationType.ANIMATION:
            return self._generate_animation(request)
        return self._generate_image(request)

    def _generate_image(self, request: GenerationRequest) -> GenerationResult:
        init_image_id = None
        if request.reference_image_path:
            init_image_id = self._upload_reference_image(request.reference_image_path)

        generation_id = self._submit_image(request, init_image_id)
        return self._poll_image_until_ready(generation_id)

    def _upload_reference_image(self, local_path: str) -> str:
        extension = os.path.splitext(local_path)[1].lstrip(".") or "png"

        init_response = requests.post(
            f"{self.BASE_URL}/init-image",
            json={"extension": extension},
            headers=self._headers,
        )
        init_response.raise_for_status()
        init_data = init_response.json()["uploadInitImage"]

        upload_url = init_data["url"]
        upload_fields = init_data["fields"]
        image_id = init_data["id"]

        with open(local_path, "rb") as f:
            upload_response = requests.post(
                upload_url,
                data=upload_fields,
                files={"file": f},
            )
        upload_response.raise_for_status()

        return image_id

    def _submit_image(self, request: GenerationRequest, init_image_id: str | None) -> str:
        payload = {
            "prompt": request.prompt,
            "negative_prompt": request.negative_prompt,
            "modelId": self._model_id,
            "width": request.width,
            "height": request.height,
            "num_images": request.num_outputs,
        }
        if init_image_id:
            payload["init_image_id"] = init_image_id
            payload["init_strength"] = 0.55

        response = requests.post(
            f"{self.BASE_URL}/generations",
            json=payload,
            headers=self._headers,
        )
        response.raise_for_status()
        data = response.json()
        return data["sdGenerationJob"]["generationId"]

    def _poll_image_until_ready(self, generation_id: str) -> GenerationResult:
        elapsed = 0.0
        while elapsed < self._timeout:
            response = requests.get(
                f"{self.BASE_URL}/generations/{generation_id}",
                headers=self._headers,
            )
            response.raise_for_status()
            data = response.json()
            generation = data["generations_by_pk"]

            if generation["status"] == "COMPLETE":
                image_urls = tuple(img["url"] for img in generation["generated_images"])
                return GenerationResult(
                    asset_urls=image_urls,
                    provider_name="leonardo",
                    raw_response=data,
                )
            if generation["status"] == "FAILED":
                raise RuntimeError(f"Leonardo generation failed: {data}")

            time.sleep(self._poll_interval)
            elapsed += self._poll_interval

        raise TimeoutError(f"Generation {generation_id} timed out")

    def _generate_animation(self, request: GenerationRequest) -> GenerationResult:
        raise NotImplementedError(
            "Leonardo's video/motion generation endpoint is not yet wired in. "
            "Once you have the endpoint and request/response shape, this method "
            "will mirror _generate_image with the correct payload and polling logic. "
            "The reference_image_path on the request should be used as the first frame."
        )