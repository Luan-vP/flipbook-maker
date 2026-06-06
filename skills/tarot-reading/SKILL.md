---
name: tarot-reading
description: Draw and reveal an interactive 3-card Past/Present/Future tarot reading, one card at a time. Use when the user asks to "draw tarot", "do a tarot reading", "pull three cards", "read my fortune", or wants a past/present/future spread. Optionally prints the same reading as a foldable zine.
---

# tarot-reading

Pull three random cards from the 78-card Rider–Waite deck and reveal them, one at
a time, as a Past / Present / Future spread — then offer the printable keepsake.

## When to use

- The user asks for a tarot reading, a card pull, or a past/present/future spread.
- They want the *experience* of a reading in chat, not a print job. (For the
  printable fold-zine on its own, use `flipbook-tarot` directly — see the
  [flipbook] sibling skill area and `flipbook-tarot --help`.)

## Draw the cards

Run the draw script **once** at the start of a reading. It is the source of
randomness — never pick or substitute cards yourself.

```bash
python skills/tarot-reading/draw.py
```

It prints JSON: a `seed` and the three positions, each with `card` and `meaning`.
Keep the full result to yourself and reveal it progressively (below). The `seed`
reproduces this exact reading on paper, so hold onto it.

Cards are **upright only** — read each `meaning` as written; do not invent
reversed interpretations.

## Reveal, one at a time

The ritual is in the pacing. Do not dump all three cards at once.

1. **Set the scene.** Three cards lie face-down — Past, Present, Future. Invite
   the user to take a breath before you turn the first.
2. **Past.** Reveal the card name and its meaning, then give 1–2 sentences tying
   it to what has shaped this moment. Stop. Invite the user to sit with it and
   tell you when they're ready for the next.
3. **Present.** On their go-ahead, reveal the second card the same way — where
   they stand now.
4. **Future.** Then the third — where the current path leads.
5. **Synthesis.** Once all three are face-up, weave them into a short arc: how
   the past feeds the present and tilts toward that future. A few sentences, not
   an essay.

Keep the same three cards throughout — do **not** re-run `draw.py` between
reveals. Match the user's tone; if they want it brisk, tighten the pauses, but
still turn the cards in order.

## Offer the printable keepsake

After the synthesis, offer to print the identical reading as a one-sheet foldable
zine. The seed from the draw reproduces the same three cards:

```bash
flipbook-tarot --seed <seed> -o reading.pdf      # white-on-black
flipbook-tarot --seed <seed> -p -o reading.pdf   # print-friendly, saves ink
```

The PDF folds into an 8-page t-fold booklet: a cover, each position facing the
card drawn for it, then a back page (`fold · cut centre · read in order`).

## How it stays honest

- `draw.py` reads `TAROT_DECK` straight from `src/flipbook_maker/tarot/deck.py` (via
  AST, no Pillow needed) and draws with `random.Random(seed).sample(deck, 3)` —
  the *same* logic as `render_tarot_reading`. That's why `--seed` reproduces the
  reading exactly. If the deck in `tarot.py` changes, the skill follows
  automatically.
