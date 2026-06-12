export interface TarotCard {
  name: string;
  description: string;
}

export const MAJOR_ARCANA: TarotCard[] = [
  { name: "The Fool", description: "New beginnings, innocence, spontaneity, a free spirit." },
  { name: "The Magician", description: "Willpower, desire, creation, manifestation." },
  { name: "The High Priestess", description: "Intuition, sacred knowledge, divine feminine, the subconscious." },
  { name: "The Empress", description: "Femininity, beauty, nature, nurturing, abundance." },
  { name: "The Emperor", description: "Authority, establishment, structure, fatherly figure." },
  { name: "The Hierophant", description: "Spiritual wisdom, tradition, conformity, morality." },
  { name: "The Lovers", description: "Love, harmony, relationships, values, choices." },
  { name: "The Chariot", description: "Control, willpower, success, ambition, determination." },
  { name: "Strength", description: "Strength, courage, patience, control, compassion." },
  { name: "The Hermit", description: "Soul-searching, introspection, being alone, inner guidance." },
  { name: "Wheel of Fortune", description: "Good luck, karma, life cycles, destiny, turning point." },
  { name: "Justice", description: "Justice, fairness, truth, cause and effect, law." },
  { name: "The Hanged Man", description: "Suspension, restriction, letting go, sacrifice." },
  { name: "Death", description: "Endings, change, transformation, transition." },
  { name: "Temperance", description: "Balance, moderation, patience, purpose, meaning." },
  { name: "The Devil", description: "Shadow self, attachment, addiction, restriction, sexuality." },
  { name: "The Tower", description: "Sudden change, upheaval, chaos, revelation, awakening." },
  { name: "The Star", description: "Hope, faith, purpose, renewal, spirituality." },
  { name: "The Moon", description: "Illusion, fear, the unconscious, confusion, complexity." },
  { name: "The Sun", description: "Positivity, fun, warmth, success, vitality." },
  { name: "Judgement", description: "Judgement, rebirth, inner calling, absolution." },
  { name: "The World", description: "Completion, integration, accomplishment, travel." },
];

const SUITS = ["Wands", "Cups", "Swords", "Pentacles"] as const;
const SUIT_THEMES: Record<string, string> = {
  Wands: "fire, passion, ambition",
  Cups: "water, emotion, intuition",
  Swords: "air, intellect, conflict",
  Pentacles: "earth, material, work",
};
const RANK_NAMES: Record<number, string> = {
  1: "Ace", 11: "Page", 12: "Knight", 13: "Queen", 14: "King",
};

function buildMinorArcana(): TarotCard[] {
  const cards: TarotCard[] = [];
  for (const suit of SUITS) {
    for (let rank = 1; rank <= 14; rank++) {
      const rankName = RANK_NAMES[rank] ?? String(rank);
      cards.push({
        name: `${rankName} of ${suit}`,
        description: `${rankName} of ${suit} — themes of ${SUIT_THEMES[suit]}.`,
      });
    }
  }
  return cards;
}

export const TAROT_DECK: TarotCard[] = [...MAJOR_ARCANA, ...buildMinorArcana()];

export function drawCards(count: number, seed?: number): TarotCard[] {
  const deck = [...TAROT_DECK];
  // Seeded shuffle via mulberry32
  let s = seed ?? Math.floor(Math.random() * 2 ** 32);
  function rand(): number {
    s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }
  for (let i = deck.length - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [deck[i], deck[j]] = [deck[j], deck[i]];
  }
  return deck.slice(0, count);
}
