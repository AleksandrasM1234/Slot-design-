from dataclasses import dataclass
from asset_pipeline.domain.theme import AssetCategory, GenerationType


@dataclass(frozen=True)
class AssetBlueprint:
    key: str
    display_name: str
    role_constant: str
    category: AssetCategory
    available_types: tuple[GenerationType, ...]
    default_num_outputs: int = 1
    default_duration_seconds: float | None = None


BOTH_TYPES = (GenerationType.IMAGE, GenerationType.ANIMATION)
IMAGE_ONLY = (GenerationType.IMAGE,)
ANIMATION_ONLY = (GenerationType.ANIMATION,)


BLUEPRINT_LIBRARY: tuple[AssetBlueprint, ...] = (
    AssetBlueprint("card_q", "Q (low-tier card)",
        "This asset must always depict the letter Q playing-card symbol, styled as a low-tier slot symbol. Never any other letter or character.",
        AssetCategory.LOW_TIER, BOTH_TYPES, default_duration_seconds=2),
    AssetBlueprint("card_k", "K (low-tier card)",
        "This asset must always depict the letter K playing-card symbol, styled as a low-tier slot symbol. Never any other letter or character.",
        AssetCategory.LOW_TIER, BOTH_TYPES, default_duration_seconds=2),
    AssetBlueprint("card_a", "A (low-tier card)",
        "This asset must always depict the letter A playing-card symbol, styled as a low-tier slot symbol. Never any other letter or character.",
        AssetCategory.LOW_TIER, BOTH_TYPES, default_duration_seconds=2),
    AssetBlueprint("special_symbol", "Special themed symbol",
        "This asset must always be a unique, high-value themed symbol tied directly to the game's theme (e.g. a themed creature, object, or character). It is never a wild or scatter.",
        AssetCategory.HIGH_TIER, BOTH_TYPES, default_duration_seconds=2),
    AssetBlueprint("wild", "Wild symbol",
        "This asset must always be the Wild symbol — a single bold icon representing 'WILD', clearly distinct from all other symbols. Never a scatter or standard symbol.",
        AssetCategory.WILD, BOTH_TYPES, default_duration_seconds=2),
    AssetBlueprint("scatter", "Scatter symbol",
        "This asset must always be the Scatter symbol — a single bold icon representing 'SCATTER', clearly distinct from all other symbols. Never a wild or standard symbol.",
        AssetCategory.SCATTER, BOTH_TYPES, default_duration_seconds=2),
    AssetBlueprint("hw_major", "Hold & Win — Major coin",
        "This asset must always be a coin/token labeled or themed as 'MAJOR' for a Hold & Win feature. Never Mini or Mega.",
        AssetCategory.HOLD_AND_WIN, BOTH_TYPES, default_duration_seconds=1.5),
    AssetBlueprint("hw_mega", "Hold & Win — Mega coin",
        "This asset must always be a coin/token labeled or themed as 'MEGA' for a Hold & Win feature. Never Mini or Major.",
        AssetCategory.HOLD_AND_WIN, BOTH_TYPES, default_duration_seconds=1.5),
    AssetBlueprint("hw_mini", "Hold & Win — Mini coin",
        "This asset must always be a coin/token labeled or themed as 'MINI' for a Hold & Win feature. Never Mega or Major.",
        AssetCategory.HOLD_AND_WIN, BOTH_TYPES, default_duration_seconds=1.5),
    AssetBlueprint("hw_coin", "Hold & Win coin (generic)",
        "This asset must always be a generic themed coin/token used inside the Hold & Win feature grid, with no tier text.",
        AssetCategory.HOLD_AND_WIN, BOTH_TYPES, default_duration_seconds=1.5),
    AssetBlueprint("symbol_simple", "Symbol — simple variant",
        "This asset must always be a clean, sharp static version of a slot symbol with no motion blur, suited for the game's default/idle reel state.",
        AssetCategory.SYMBOL, BOTH_TYPES, default_duration_seconds=2),
    AssetBlueprint("symbol_blur", "Symbol — blur variant",
        "This asset must always be a motion-blurred version of a slot symbol, suited for the reels while spinning.",
        AssetCategory.SYMBOL, IMAGE_ONLY),

    AssetBlueprint("background", "Background scene",
        "This asset must always be a full background scene for the game, establishing the game's setting. It is never an isolated object or symbol.",
        AssetCategory.BACKGROUND, IMAGE_ONLY),
    AssetBlueprint("logo_frame", "Logo frame",
        "This asset must always be the game's logo treatment — the game's name/title rendered as a stylized logo graphic. Never a symbol or scene.",
        AssetCategory.UI_ELEMENT, IMAGE_ONLY),
    AssetBlueprint("bitmapfont", "Bitmap font",
        "This asset must always be a stylized alphanumeric font sheet matching the game's theme, suitable for use as an in-game bitmap font. Never a symbol or scene.",
        AssetCategory.UI_ELEMENT, IMAGE_ONLY),
    AssetBlueprint("hw_counter", "Hold & Win counter UI",
        "This asset must always be a UI counter element (e.g. spins-remaining display) themed for the Hold & Win feature. Never a symbol or coin.",
        AssetCategory.UI_ELEMENT, IMAGE_ONLY),
    AssetBlueprint("static", "Static scene asset",
        "This asset must always be a static, non-animated supporting scene or panel element for the game UI.",
        AssetCategory.BACKGROUND, IMAGE_ONLY),

    AssetBlueprint("big_win", "Big Win animation",
        "This asset must always be a 'BIG WIN' celebratory text/graphic animation. Never Mega or Ultra tier wording.",
        AssetCategory.ANIMATION, ANIMATION_ONLY, default_duration_seconds=2),
    AssetBlueprint("mega_win", "Mega Win animation",
        "This asset must always be a 'MEGA WIN' celebratory text/graphic animation. Never Big or Ultra tier wording.",
        AssetCategory.ANIMATION, ANIMATION_ONLY, default_duration_seconds=2),
    AssetBlueprint("ultra_win", "Ultra Win animation",
        "This asset must always be an 'ULTRA WIN' celebratory text/graphic animation. Never Big or Mega tier wording.",
        AssetCategory.ANIMATION, ANIMATION_ONLY, default_duration_seconds=2),
    AssetBlueprint("win_highlight", "Win highlight animation",
        "This asset must always be a short looping highlight/glow animation used to indicate a winning symbol or line.",
        AssetCategory.ANIMATION, ANIMATION_ONLY, default_duration_seconds=1.5),
    AssetBlueprint("reel_win_highlight", "Reel win highlight animation",
        "This asset must always be a short looping highlight animation for an entire winning reel.",
        AssetCategory.ANIMATION, ANIMATION_ONLY, default_duration_seconds=1.5),
    AssetBlueprint("suspense_reel", "Reel suspense animation",
        "This asset must always be a looping suspense/anticipation animation for a spinning reel awaiting its result.",
        AssetCategory.ANIMATION, ANIMATION_ONLY, default_duration_seconds=2),
    AssetBlueprint("suspense_cell", "Cell suspense animation",
        "This asset must always be a looping suspense/anticipation animation for a single reel cell awaiting its result.",
        AssetCategory.ANIMATION, ANIMATION_ONLY, default_duration_seconds=2),
    AssetBlueprint("hw_text_transition", "Hold & Win text transition",
        "This asset must always be a text transition animation used when entering or updating the Hold & Win feature.",
        AssetCategory.ANIMATION, ANIMATION_ONLY, default_duration_seconds=1.5),
)


def find_blueprint(key: str) -> AssetBlueprint:
    for b in BLUEPRINT_LIBRARY:
        if b.key == key:
            return b
    raise ValueError(f"Unknown blueprint key: {key}")