import { sexualityFlags } from "./sexualityFlags";

export type CategoryId = "gay" | "bisexual" | "lesbian" | "transgender" | "bestiality";

export const categoryOptions = [
  { value: "gay", label: "Gay Male" },
  { value: "bisexual", label: "Bisexual" },
  { value: "lesbian", label: "Lesbian" },
  { value: "transgender", label: "Transgender" },
  { value: "bestiality", label: "Bestiality" }
] as const;

export const subcategoryOptions = [
  { value: "adult-friends", label: "adult-friends" },
  { value: "adult-youth", label: "adult-youth" },
  { value: "athletics", label: "athletics" },
  { value: "authoritarian", label: "authoritarian" },
  { value: "battle", label: "battle" },
  { value: "beginnings", label: "beginnings" },
  { value: "bondage", label: "bondage" },
  { value: "camping", label: "camping" },
  { value: "celebrity", label: "celebrity" },
  { value: "college", label: "college" },
  { value: "encounters", label: "encounters" },
  { value: "highschool", label: "highschool" },
  { value: "historical", label: "historical" },
  { value: "hookers", label: "hookers" },
  { value: "incest", label: "incest" },
  { value: "interracial", label: "interracial" },
  { value: "masturbation", label: "masturbation" },
  { value: "military", label: "military" },
  { value: "misc", label: "misc" },
  { value: "no-sex", label: "no-sex" },
  { value: "non-english", label: "non-english" },
  { value: "relationships", label: "relationships" },
  { value: "rural", label: "rural" },
  { value: "romance", label: "romance" },
  { value: "sf-fantasy", label: "sf-fantasy" },
  { value: "urination", label: "urination" },
  { value: "young-friends", label: "young-friends" },
  { value: "by_authors", label: "by_authors" },
  { value: "chemical", label: "chemical" },
  { value: "control", label: "control" },
  { value: "Joe_Bates_Saga", label: "Joe_Bates_Saga" },
  { value: "Magic-ScFi", label: "Magic-ScFi" },
  { value: "mind-control", label: "mind-control" },
  { value: "Non-TG-Stories", label: "Non-TG-Stories" },
  { value: "she-male", label: "she-male" },
  { value: "surgery", label: "surgery" },
  { value: "teen", label: "teen" },
  { value: "tv", label: "tv" }
] as const;

const buildSlantedStripeBackground = (colors: readonly string[]) => {
  const darkenHex = (hex: string, amount = 0.14) => {
    const normalized = hex.replace("#", "");
    if (normalized.length !== 6) return hex;

    const value = Number.parseInt(normalized, 16);
    const r = Math.round(((value >> 16) & 0xff) * (1 - amount));
    const g = Math.round(((value >> 8) & 0xff) * (1 - amount));
    const b = Math.round((value & 0xff) * (1 - amount));

    return `#${[r, g, b]
      .map((channel) => channel.toString(16).padStart(2, "0"))
      .join("")}`;
  };

  const doubled = [...colors, ...colors];
  const total = doubled.length;
  const stops = doubled.flatMap((color, i) => [
    `${darkenHex(color)} ${(i / total) * 100}%`,
    `${darkenHex(color)} ${((i + 1) / total) * 100}%`
  ]).join(", ");
  return `linear-gradient(135deg, ${stops})`;
};

const categoryStyles: Record<CategoryId, string> = {
  gay: `--badge-bg: ${buildSlantedStripeBackground(sexualityFlags.bear)};`,
  bisexual: `--badge-bg: ${buildSlantedStripeBackground(sexualityFlags.bisexual)};`,
  lesbian: `--badge-bg: ${buildSlantedStripeBackground(sexualityFlags.lesbian)};`,
  transgender: `--badge-bg: ${buildSlantedStripeBackground(sexualityFlags.transgender)};`,
  bestiality: "--badge-bg: linear-gradient(135deg, #f97316, #ea580c);"
};

export const getCategoryBarStyle = (category: string) =>
  categoryStyles[category as CategoryId] ?? "--badge-bg: linear-gradient(135deg, #475569, #334155);";
