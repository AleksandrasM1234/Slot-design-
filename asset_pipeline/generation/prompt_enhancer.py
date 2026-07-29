from abc import ABC, abstractmethod
from huggingface_hub import InferenceClient


BACKGROUND_CATEGORIES = {"background", "background_character"}


class PromptEnhancer(ABC):

    @abstractmethod
    def enhance(self, base_prompt: str, art_style: str, palette: list[str],
                is_animation: bool = False, needs_isolation: bool = True) -> str:
        ...


class HuggingFacePromptEnhancer(PromptEnhancer):

    def __init__(self, api_token: str, model: str = "Qwen/Qwen2.5-7B-Instruct"):
        self._client = InferenceClient(model=model, token=api_token)

    def enhance(self, base_prompt: str, art_style: str, palette: list[str],
                is_animation: bool = False, needs_isolation: bool = True) -> str:
        style_context = ", ".join(palette)

        style_rules = (
            "You are an expert AI Prompt Engineer for slot game assets. Your job is to take "
            "a raw user idea and generate a detailed, high-quality prompt.\n\n"
            "MANDATORY CONSTANTS:\n"
        )

        if needs_isolation:
            style_rules += (
                "1. CHROMAKEY BACKGROUND: The subject must ALWAYS be isolated on a flat, solid, "
                "vibrant chroma key green background (use terms like: 'solid chroma key green "
                "background, hex #00FF00, flat green screen, even studio lighting with no shadows "
                "on the background'). State this requirement in two different phrasings, not just "
                "once.\n"
                "2. NO CONTACT SHADOWS: Describe the subject as floating in space rather than "
                "standing on a surface, to avoid ground-contact shadows anchoring it to a floor.\n"
                "3. NO LIGHT SPILL: The subject must have zero glow, light bleed, or particle "
                "effects extending beyond its own edges onto the background. State this "
                "prohibition in two different phrasings.\n"
                "4. CONSISTENT LIGHTING: Use soft, even, top-down studio lighting with no strong "
                "directional shadows, so this asset matches the lighting of other assets in the "
                "same batch.\n"
            )
        else:
            style_rules += (
                "1. FULL SCENE: This is a complete background/environment asset, not an isolated "
                "object. Do NOT put it on a chroma key or green screen — describe it as a full, "
                "self-contained scene.\n"
            )

        style_rules += (
            "5. NO EMBEDDED TEXT: The image must not contain any text, logos, watermarks, or "
            "readable characters.\n"
            "6. PHYSICAL ANALOGIES FOR MOTION: When describing any motion, use physical-world "
            "analogies (e.g. 'pulses like a heartbeat', 'crackles like electricity through wires') "
            "rather than abstract or technical/geometric descriptions.\n"
            "7. KEEP IT SHORT: The final prompt must stay concise, roughly 40 words or fewer. "
            "Simpler, shorter prompts produce more reliable results than long, multi-clause ones.\n"
        )

        if is_animation:
            style_rules += (
                "8. SEAMLESS LOOP: Because this is a video asset, include instructions for a "
                "perfect loop: 'seamlessly looping animation, cyclical motion, starts and ends on "
                "the exact same frame, fluid continuous motion'.\n"
                "9. STATIC CAMERA: The camera must not move, pan, or zoom — only the subject "
                "animates.\n"
            )
        else:
            style_rules += (
                "8. STATIC POSE: Describe a clean, clear static pose suited for sprite "
                "extraction.\n"
            )

        style_rules += (
            "\nIncorporate the provided art style and color palette into your enhanced prompt. "
            "Format the final output as a single comma-separated generative prompt. "
            "Do not write conversational filler—return ONLY the enhanced prompt itself."
        )

        user_prompt = (
            f"Enhance this raw idea: {base_prompt}. "
            f"Art style: {art_style}. Color palette: {style_context}."
        )

        messages = [
            {"role": "system", "content": style_rules},
            {"role": "user", "content": user_prompt},
        ]

        response = self._client.chat_completion(
            messages=messages,
            max_tokens=200,
            temperature=0.5,
        )
        return response.choices[0].message.content


def category_needs_isolation(category: str) -> bool:
    return category not in BACKGROUND_CATEGORIES