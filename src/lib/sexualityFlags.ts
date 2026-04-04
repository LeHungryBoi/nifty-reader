export const sexualityFlags = {
  rainbow_pride: [
    "#E40303",
    "#FF8C00",
    "#FFED00",
    "#008026",
    "#004DFF",
    "#750787"
  ],
  lesbian: [
    "#D52D00",
    "#EF7627",
    "#FF9A56",
    "#FFFFFF",
    "#D162A4",
    "#B55690",
    "#A30262"
  ],
  transgender: [
    "#5BCEFA",
    "#F5A9B8",
    "#FFFFFF",
    "#F5A9B8",
    "#5BCEFA"
  ],
  gay_mlm: [
    "#078D70",
    "#26CEAA",
    "#98E8C1",
    "#FFFFFF",
    "#7BADE2",
    "#5049CC",
    "#3D1A78"
  ],
  bisexual: [
    "#D60270",
    "#9B4F96",
    "#0038A8"
  ],
  pansexual: [
    "#FF218C",
    "#FFD800",
    "#21B1FF"
  ],
  asexual: [
    "#000000",
    "#A3A3A3",
    "#FFFFFF",
    "#800080"
  ],
  aromantic: [
    "#3DA542",
    "#A7D379",
    "#FFFFFF",
    "#A9A9A9",
    "#000000"
  ],
  non_binary: [
    "#FFF430",
    "#FFFFFF",
    "#9C59D1",
    "#000000"
  ],
  polysexual: [
    "#F61CB9",
    "#07D569",
    "#1C92F6"
  ],
  omnisexual: [
    "#FF9BCD",
    "#FF66B3",
    "#FF0066",
    "#6E0DD0",
    "#4A00FF"
  ],
  bear: [
    "#623804",
    "#D56300",
    "#FEDD63",
    "#FFFFFF",
    "#555555",
    "#000000"
  ]
} as const;

export type SexualityFlagKey = keyof typeof sexualityFlags;
