from asyncio import timeout
import time
import json
import os
from urllib import response
import requests
from asset_pipeline.generation.base import (
    ImageGenerationProvider, GenerationRequest, GenerationResult
)
from asset_pipeline.domain.theme import GenerationType
from asset_pipeline.generation.model_catalog import ModelOption
from asset_pipeline.generation.resolution_resolver import resolve_generation_size


class LeonardoProvider(ImageGenerationProvider):

    BASE_URL = "https://cloud.leonardo.ai/api/rest"
    STYLE_REFERENCE_PREPROCESSOR_ID = 67

    def __init__(self, api_key: str, model: ModelOption,
                 poll_interval: float = 3.0, timeout: float = 180.0,
                 video_timeout: float = 600.0):
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        self._model = model
        self._poll_interval = poll_interval
        self._timeout = timeout
        self._video_timeout = video_timeout

    def generate(self, request: GenerationRequest) -> GenerationResult:
        if self._model.generation_type == GenerationType.ANIMATION:
            return self._generate_video(request)
        return self._generate_image(request)

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

    def get_remaining_balance(self) -> dict:
        response = requests.get(f"{self.BASE_URL}/v1/me", headers=self._headers)
        response.raise_for_status()
        data = response.json()

        user_details = data.get("user_details", [{}])[0]
        credits = user_details.get("apiPaidTokens", 0)

        return {"credits_remaining": credits}

    def estimate_cost(self, model_id: str, service_type: str, num_images: int = 1,
                   width: int | None = None, height: int | None = None) -> float | None:
        payload = {
            "serviceType": service_type,
            "modelId": model_id,
            "numImages": num_images,
        }  
        if width and height:
            payload["width"] = width
            payload["height"] = height

        response = requests.post(
            f"{self.BASE_URL}/v1/pricing-calculator",
            json=payload,
            headers=self._headers,
        )
        if not response.ok:
            return None
        data = response.json()
        return data.get("calculateProductionApiServiceCost", {}).get("cost")
    # -------------------- image generation --------------------

    def _generate_image(self, request: GenerationRequest) -> GenerationResult:
        width, height, mode = resolve_generation_size(request.width, request.height, self._model)

        init_image_id = None
        if request.reference_image_path:
            init_image_id = self._upload_reference_image(request.reference_image_path)

        if self._model.api_version == "v2":
            payload = {
                "model": self._model.model_id,
                "public": False,
                "parameters": {
                    "prompt": request.prompt,
                    "width": width,
                    "height": height,
                    "quantity": request.num_outputs,
                },
            }
            if init_image_id:
                payload["parameters"]["guidances"] = {
                    "image_reference": [
                        {
                            "image": {"id": init_image_id, "type": "UPLOADED"},
                            "strength": request.reference_strength.upper(),
                        }
                    ]
                }
            url = f"{self.BASE_URL}/v2/generations"
        else:
            payload = {
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "modelId": self._model.model_id,
                "width": width,
                "height": height,
                "num_images": request.num_outputs,
            }
            if init_image_id:
                payload["controlnets"] = [
                    {
                        "initImageId": init_image_id,
                        "initImageType": "UPLOADED",
                        "preprocessorId": self.STYLE_REFERENCE_PREPROCESSOR_ID,
                        "strengthType": request.reference_strength,
                    }
                ]
            url = f"{self.BASE_URL}/v1/generations"

        return self._submit_and_poll(url, payload)

    # -------------------- video generation --------------------

    def _generate_video(self, request: GenerationRequest) -> GenerationResult:
        width, height, mode = resolve_generation_size(request.width, request.height, self._model)

        init_image_id = None
        if request.reference_image_path:
            init_image_id = self._upload_reference_image(request.reference_image_path)

        payload = {
            "model": self._model.model_id,
            "public": False,
            "parameters": {
                "prompt": request.prompt,
                "width": width,
                "height": height,
                "duration": request.duration_seconds or 5,
                "mode": mode or "RESOLUTION_720",
                "motion_has_audio": False,
            },
        }
        if init_image_id:
            payload["parameters"]["guidances"] = {
                "start_frame": [{"image": {"id": init_image_id, "type": "UPLOADED"}}]
            }

        url = f"{self.BASE_URL}/v2/generations"
        print(f"[DEBUG] Video generation payload: {payload}")
        return self._submit_and_poll(url, payload, timeout=self._video_timeout, expect_video=True)

    # -------------------- shared submit/poll --------------------

    def _submit_and_poll(self, url: str, payload: dict, timeout: float | None = None,
                      expect_video: bool = False) -> GenerationResult:
        response = requests.post(url, json=payload, headers=self._headers)
        if not response.ok:
            body_lower = response.text.lower()
            if response.status_code in (402, 403) or "insufficient" in body_lower or "credit" in body_lower:
                raise RuntimeError(f"LEONARDO_OUT_OF_CREDITS: {response.text}")
            raise RuntimeError(
                f"Leonardo rejected the generation request with status "
                f"{response.status_code}: {response.text}"
            )
        data = response.json()

        generation_id = None
        if "sdGenerationJob" in data:
            generation_id = data["sdGenerationJob"].get("generationId")
        elif "generate" in data:
            generation_id = data["generate"].get("generationId")
        elif "id" in data:
            generation_id = data["id"]
        elif "generationId" in data:
            generation_id = data["generationId"]

        if not generation_id:
            raise RuntimeError(
                f"Could not find a generation id in the response. Raw response: {data}"
            )

        return self._poll(generation_id, timeout or self._timeout, expect_video=expect_video)

    def _poll(self, generation_id: str, timeout: float, expect_video: bool = False) -> GenerationResult:
        poll_url = f"{self.BASE_URL}/v1/generations/{generation_id}"

        elapsed = 0.0
        while elapsed < timeout:
            response = requests.get(poll_url, headers=self._headers)
            if not response.ok:
                raise RuntimeError(
                    f"Polling failed with status {response.status_code}: {response.text}"
                )
            data = response.json()

            generation = data.get("generations_by_pk", data)
            status = generation.get("status")

            if status == "COMPLETE":
                print(f"[DEBUG] Completed generation raw response: {data}")
                images = generation.get("generated_images") or generation.get("outputs") or []

                if expect_video:
                    urls = tuple(
                        img.get("motionMP4URL") for img in images if img.get("motionMP4URL")
                    )
                else:
                    urls = tuple(img.get("url") for img in images if img.get("url"))

                if not urls:
                    raise RuntimeError(
                        f"Generation completed but no {'video' if expect_video else 'image'} "
                        f"URLs were found. Raw response: {data}"
                    )
                cost = data.get("cost", {}).get("amount") if isinstance(data.get("cost"), dict) else None

                return GenerationResult(asset_urls=urls, provider_name="leonardo", raw_response=data,is_video=expect_video, cost_usd=cost)
            if status == "FAILED":
                raise RuntimeError(f"Leonardo generation failed: {data}")

            time.sleep(self._poll_interval)
            elapsed += self._poll_interval

        raise TimeoutError(
            f"Generation {generation_id} timed out after {timeout:.0f}s. "
            f"Video generations can take several minutes — if this keeps happening, "
            f"the timeout may need to be increased further."
        )

    