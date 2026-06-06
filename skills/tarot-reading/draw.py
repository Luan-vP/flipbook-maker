#!/usr/bin/env python3
"""Draw a 3-card Past / Present / Future tarot reading.

A random seed is chosen, then the three cards are drawn with the *same* logic as
``flipbook_maker.tarot.render_tarot_reading`` (``random.Random(seed).sample(
deck, 3)``). So the printed keepsake reproduces this exact reading:

    flipbook-tarot --seed <seed> -o reading.pdf

The draw — not the model — is the source of randomness, so the cards are genuine.

The 78-card deck is read straight from ``src/flipbook_maker/tarot.py`` via AST,
so this script needs no third-party packages (not even Pillow) and the tarot
module stays the single source of truth for the deck.

Usage:
    python draw.py            # fresh random reading
    python draw.py 42         # reproduce the reading for seed 42
"""
from __future__ import annotations

import ast
import json
import random
import sys
from pathlib import Path

_TAROT_SRC = Path(__file__).resolve().parents[2] / "src" / "flipbook_maker" / "tarot" / "deck.py"

POSITIONS = ("Past", "Present", "Future")
PROMPTS = {
    "Past": "What has shaped this moment",
    "Present": "Where you stand now",
    "Future": "Where the current path leads",
}


def load_deck() -> list[tuple[str, str]]:
    """Return [(name, meaning), ...] parsed from TAROT_DECK in tarot.py.

    Order is preserved exactly, so seeded sampling matches render_tarot_reading.
    """
    tree = ast.parse(_TAROT_SRC.read_text())
    for node in ast.walk(tree):
        # TAROT_DECK is annotated (`TAROT_DECK: list[TarotCard] = [...]`), so it
        # parses as AnnAssign; tolerate a plain Assign too.
        if isinstance(node, ast.AnnAssign):
            targets, value = [node.target], node.value
        elif isinstance(node, ast.Assign):
            targets, value = node.targets, node.value
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == "TAROT_DECK" for t in targets):
            continue
        deck: list[tuple[str, str]] = []
        for el in value.elts:  # TarotCard("name", "meaning") calls
            name, meaning = (a.value for a in el.args)
            deck.append((name, meaning))
        return deck
    raise RuntimeError(f"TAROT_DECK not found in {_TAROT_SRC}")


def draw(seed: int | None = None) -> dict:
    """Return {seed, reading:[{position, prompt, card, meaning}, ...]}."""
    if seed is None:
        seed = random.SystemRandom().randrange(2**31)
    deck = load_deck()
    # Mirrors render_tarot_reading: past, present, future = rng.sample(deck, 3)
    cards = random.Random(seed).sample(deck, 3)
    reading = [
        {"position": pos, "prompt": PROMPTS[pos], "card": name, "meaning": meaning}
        for pos, (name, meaning) in zip(POSITIONS, cards)
    ]
    return {"seed": seed, "reading": reading}


if __name__ == "__main__":
    arg = int(sys.argv[1]) if len(sys.argv) > 1 else None
    print(json.dumps(draw(arg), indent=2))
