/**
 * Wayfara design tokens — extracted from the "Wayfara Mobile Screens" design.
 *
 * The mockup is coral-first (#F8593C) with a warm cream canvas and a
 * Space Grotesk / Manrope type pairing. These tokens are the single source of
 * truth for the screens under `screens/`; import from here instead of hardcoding
 * hex values so a theme swap (coral → amber → terracotta) is one line.
 */

// ─── Brand accent (the mockup exposes three; coral is the default) ───────────
export const accents = {
  coral: "#F8593C",
  amber: "#F49A1A",
  terracotta: "#C7502F",
} as const;

export type AccentName = keyof typeof accents;

export const colors = {
  accent: accents.coral,
  accentSoft: "#FBEEE7", // tinted accent surface (chips, secondary buttons)

  // Canvas / surfaces
  canvas: "#FBF6EF", // app background (warm cream)
  surface: "#FFFFFF",
  ink: "#2A2119", // primary text / near-black brown

  // Muted text ramp (dark → light)
  textMuted: "#6F5F50",
  textSubtle: "#7C6C5C",
  textFaint: "#8A7A69",
  textFaintest: "#A2917F",

  // Hairlines / borders
  border: "#EAD9C6",
  borderSoft: "#F0E5D8",
  borderField: "#E6D6C3",

  // Accent role colors used in the mockup
  success: "#1F8A5B", // match % badges
  warning: "#F49A1A",
  warningBg: "#FDF4D9",
  warningBorder: "#F4E4B0",
  warningInk: "#6B4E12",
  warningInkSoft: "#B4841A",

  white: "#FFFFFF",
} as const;

// ─── Type ────────────────────────────────────────────────────────────────────
// Family names below match the keys we load in App.tsx via expo-font.
export const fonts = {
  // Space Grotesk — display / headings / numerals
  display: "SpaceGrotesk_700Bold",
  displaySemi: "SpaceGrotesk_600SemiBold",
  displayMedium: "SpaceGrotesk_500Medium",
  // Manrope — body / labels
  body: "Manrope_500Medium",
  bodyRegular: "Manrope_400Regular",
  bodySemi: "Manrope_600SemiBold",
  bodyBold: "Manrope_700Bold",
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 18,
  "2xl": 20,
  "3xl": 22,
  card: 26,
  pill: 999,
} as const;

export const spacing = {
  screenX: 24,
} as const;

/** Resolve the accent hex for a named theme (falls back to coral). */
export function accentFor(name: AccentName = "coral"): string {
  return accents[name] ?? accents.coral;
}
