from abc import ABC, abstractmethod
from groq import Groq


BACKGROUND_CATEGORIES = {"background", "background_character"}

GREEN_KEYWORDS = (
    "green", "emerald", "jade", "olive", "lime", "forest", "mint",
    "sage", "chartreuse", "moss", "viridian",
)


def detect_chroma_color(text: str) -> str:
    lowered = text.lower()
    if any(keyword in lowered for keyword in GREEN_KEYWORDS):
        return "magenta"
    return "green"


class PromptEnhancer(ABC):

    @abstractmethod
    def enhance(self, base_prompt: str, art_style: str, palette: list[str],
                is_animation: bool = False, needs_isolation: bool = True,
                master_context: str | None = None, role_constant: str | None = None,
                has_reference_image: bool = False, text_content: str | None = None) -> tuple[str, str]:
        ...

    @abstractmethod
    def enhance_master(self, base_prompt: str, art_style: str, palette: list[str]) -> str:
        ...

    @abstractmethod
    def generate_from_world(self, role_display_name: str, master_context: str,
                             art_style: str, palette: list[str],
                             is_animation: bool = False, needs_isolation: bool = True,
                             text_content: str | None = None) -> tuple[str, str]:
        ...


class GroqPromptEnhancer(PromptEnhancer):

    def __init__(self, api_key: str, model: str = "openai/gpt-oss-20b"):
        self._client = Groq(api_key=api_key)
        self._model = model

    def _chat(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=400,
            reasoning_effort="low",
        )
        content = (response.choices[0].message.content or "").strip()

        if not content:
            retry_response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt + "\n\nRespond with the prompt text only."},
                ],
                temperature=min(temperature + 0.2, 1.0),
                max_tokens=400,
                reasoning_effort="low",
            )
            content = (retry_response.choices[0].message.content or "").strip()

        return content

    def enhance(self, base_prompt: str, art_style: str, palette: list[str],
                is_animation: bool = False, needs_isolation: bool = True,
                master_context: str | None = None, role_constant: str | None = None,
                has_reference_image: bool = False, text_content: str | None = None) -> tuple[str, str]:
        style_context = ", ".join(palette)

        chroma_color = detect_chroma_color(f"{base_prompt} {master_context or ''} {role_constant or ''}")
        chroma_hex = "#FF00FF" if chroma_color == "magenta" else "#00FF00"

        style_rules = (
            "You are an expert AI Prompt Engineer for slot game assets. Your job is to take "
            "a raw user idea and generate a detailed, high-quality prompt.\n\n"
        )

        if role_constant:
            style_rules += (
                f"ASSET IDENTITY (highest priority — never violate this): {role_constant}\n\n"
            )

        if master_context:
            style_rules += (
                f"WORLD CONTEXT: This asset belongs to a game with the following world/story "
                f"context — use it to inform tone and imagery, but do not describe the world "
                f"itself in the output, only the asset: \"{master_context}\"\n\n"
            )

        style_rules += "MANDATORY CONSTANTS:\n"

        if needs_isolation:
            style_rules += (
                f"1. CHROMAKEY BACKGROUND: The subject must ALWAYS be isolated on a flat, solid, "
                f"vibrant chroma key {chroma_color} background (use terms like: 'solid chroma key "
                f"{chroma_color} background, hex {chroma_hex}, flat {chroma_color} screen, even "
                f"studio lighting with no shadows on the background'). State this requirement in "
                f"two different phrasings, not just once.\n"
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

        if text_content:
            style_rules += (
                f"5. REQUIRED TEXT: The image MUST clearly and legibly render the exact text "
                f"\"{text_content}\" as a readable design element, spelled correctly, styled to "
                f"match the art direction. State this requirement in two different phrasings.\n"
            )
        else:
            style_rules += (
                "5. NO EMBEDDED TEXT: The image must not contain any text, logos, watermarks, or "
                "readable characters.\n"
            )

        style_rules += (
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
                "10. PRESERVE IDENTITY: The animated subject must remain recognizably the exact "
                "same object or character described above — do not let it morph, change shape, or "
                "gain new features. Only add motion, glow, particles, or energy effects around or "
                "through it.\n"
                "11. REWARDING ENERGY: If this animation represents a win, celebration, or reward "
                "moment, make it feel exciting, vivid, and entertaining — dynamic motion, sparkle, "
                "pulsing light — never flat or static-feeling.\n"
                "12. NO LIGHT OR PARTICLE BLEED: Any glow, sparks, or particle effects must stay "
                "tightly contained to the subject's silhouette and never spread onto or beyond the "
                "background.\n"
                "13. FLAT 2D ASSET: This is a flat 2D game sprite, not a 3D render. Explicitly state "
                "'flat 2D illustration, no depth, no parallax, no camera dolly or rotation'.\n"
                "14. NO SHADOWS OR INCIDENTAL MOVEMENT: The subject itself must stay physically "
                "static — no swaying, no idle sway, no background elements drifting, no shadows "
                "appearing, moving, or flickering. The only motion allowed is the specific effect "
                "described in the prompt (e.g. a glow pulsing, a spark trail) — nothing else in the "
                "frame may move.\n"
            )

            if has_reference_image:
                style_rules += (
                    "15. LOCKED FIRST FRAME: A reference image has been provided as the exact "
                    "starting frame. State explicitly in the prompt that the animation must begin "
                    "from this exact image with no changes to its shape, proportions, colors, or "
                    "design — describe the motion as happening TO this fixed subject, not as a new "
                    "reinterpretation of it. Repeat this constraint in two different phrasings.\n"
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

        enhanced_text = self._chat(style_rules, user_prompt, temperature=0.5)
        return enhanced_text, chroma_color

    def enhance_master(self, base_prompt: str, art_style: str, palette: list[str]) -> str:
        style_context = ", ".join(palette)

        system_prompt = (
            "You are a creative writer helping define the world and story behind a slot game. "
            "Take the user's raw idea and expand it into a vivid, specific 2-4 sentence world "
            "description — setting, tone, key characters or forces at play. This will be used as "
            "shared creative context for generating many individual game assets, so favor concrete, "
            "evocative imagery over vague mood words. Do not describe specific assets, symbols, or "
            "UI elements — only the world itself. Return ONLY the description, no conversational "
            "filler."
        )
        user_prompt = (
            f"Raw idea: {base_prompt}. Art style: {art_style}. Color palette: {style_context}."
        )

        return self._chat(system_prompt, user_prompt, temperature=0.7)

    def generate_from_world(self, role_display_name: str, master_context: str,
                             art_style: str, palette: list[str],
                             is_animation: bool = False, needs_isolation: bool = True,
                             text_content: str | None = None) -> tuple[str, str]:
        style_context = ", ".join(palette)

        chroma_color = detect_chroma_color(f"{role_display_name} {master_context}")

        system_prompt = (
            f"You are an expert AI Prompt Engineer for slot game assets. Given a game's world "
            f"context and the specific role of one asset, invent a concrete, specific visual "
            f"description for that asset that fits naturally into the world. Do not restate the "
            f"world description itself — describe only this one asset.\n\n"
            f"WORLD CONTEXT: \"{master_context}\"\n\n"
            f"ASSET ROLE: {role_display_name}\n\n"
        )

        if needs_isolation:
            system_prompt += (
                "MANDATORY CONSTANTS:\n"
                f"1. CHROMAKEY BACKGROUND: isolated on a flat, solid, vibrant chroma key "
                f"{chroma_color} background, stated in two different phrasings.\n"
                "2. NO CONTACT SHADOWS: describe as floating in space.\n"
                "3. NO LIGHT SPILL: zero glow or particles extending beyond the subject's edges, "
                "stated in two different phrasings.\n"
                "4. CONSISTENT LIGHTING: soft, even, top-down studio lighting.\n"
            )
        else:
            system_prompt += (
                "MANDATORY CONSTANT: this is a full scene/background asset, not an isolated "
                "object — do not put it on a chroma key.\n"
            )

        if text_content:
            system_prompt += (
                f"5. REQUIRED TEXT: must clearly and legibly render the exact text "
                f"\"{text_content}\" as a readable design element, spelled correctly, stated in "
                f"two different phrasings.\n"
            )
        else:
            system_prompt += "5. NO EMBEDDED TEXT.\n"

        system_prompt += (
            "6. PHYSICAL ANALOGIES FOR MOTION where relevant.\n"
            "7. KEEP IT SHORT: roughly 40 words or fewer.\n"
        )

        if is_animation:
            system_prompt += (
                "8. SEAMLESS LOOP, STATIC CAMERA.\n"
                "9. PRESERVE IDENTITY: the subject must stay recognizably the same object/character, "
                "only animating motion and effects around it, never morphing its form.\n"
                "10. REWARDING ENERGY: if this represents a win or reward, make it vivid and "
                "entertaining — dynamic motion, sparkle, pulsing light.\n"
            )
        else:
            system_prompt += "8. STATIC POSE suited for sprite extraction.\n"

        system_prompt += (
            f"\nIncorporate the art style ({art_style}) and color palette ({style_context}). "
            "Return ONLY the final comma-separated generative prompt, no conversational filler."
        )

        user_prompt = f"Generate the asset description for: {role_display_name}"

        generated_text = self._chat(system_prompt, user_prompt, temperature=0.7)
        return generated_text, chroma_color


def category_needs_isolation(category: str) -> bool:
    return category not in BACKGROUND_CATEGORIES


def category_needs_isolation(category: str) -> bool:
    return category not in BACKGROUND_CATEGORIES