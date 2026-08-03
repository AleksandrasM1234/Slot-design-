from dataclasses import dataclass


@dataclass(frozen=True)
class FrameworkPreset:
    key: str
    display_name: str
    description: str
    blueprint_keys: tuple[str, ...]


FRAMEWORK_PRESETS: tuple[FrameworkPreset, ...] = (
    FrameworkPreset(
        "classic_5x3",
        "Classic 5x3 Slot",
        "Q, K, A, two special symbols, Wild, Scatter, and three Hold & Win tiers.",
        (
            "card_q", "card_k", "card_a",
            "special_symbol", "special_symbol",
            "wild", "scatter",
            "hw_major", "hw_mega", "hw_mini",
        ),
    ),
    FrameworkPreset(
        "hold_and_win_full",
        "Full Hold & Win Slot",
        "Everything from Classic 5x3 plus win celebration and suspense animations.",
        (
            "card_q", "card_k", "card_a",
            "special_symbol", "special_symbol", "special_symbol",
            "wild", "scatter",
            "hw_major", "hw_mega", "hw_mini", "hw_coin", "hw_counter",
            "background", "logo_frame", "bitmapfont",
            "big_win", "mega_win", "ultra_win",
            "win_highlight", "reel_win_highlight",
            "suspense_reel", "suspense_cell",
            "hw_text_transition",
        ),
    ),
)


def find_preset(key: str) -> FrameworkPreset:
    for p in FRAMEWORK_PRESETS:
        if p.key == key:
            return p
    raise ValueError(f"Unknown framework preset key: {key}")