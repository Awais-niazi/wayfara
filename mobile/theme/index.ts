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
import { Platform } from "react-native";

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
  // Space Mono — the travel-document voice: ticket fields, uni codes,
  // deadlines, stamps. Tabular by nature, so numbers never jitter.
  mono: "SpaceMono_400Regular",
  monoBold: "SpaceMono_700Bold",
  // Dashboard greeting (product decision, July 2026): Times New Roman heading
  // + Zapfino quote. Both are real system fonts on iOS only; elsewhere we ship
  // the standard stand-ins loaded in App.tsx — Tinos (metric-identical to
  // Times New Roman) and Great Vibes (Zapfino-style calligraphy).
  welcomeSerif: Platform.OS === "ios" ? "Times New Roman" : "Tinos_400Regular",
  welcomeScript: Platform.OS === "ios" ? "Zapfino" : "GreatVibes_400Regular",
} as const;

// ─── Elevation (one scale — pick from here, never ad-hoc shadows) ────────────
export const shadow = {
  /** Resting cards: barely-there lift off the cream canvas. */
  card: {
    shadowColor: "#5A3719",
    shadowOpacity: 0.08,
    shadowRadius: 14,
    shadowOffset: { width: 0, height: 6 },
    elevation: 2,
  },
  /** Floating chrome (tab dock, sticky CTAs) and hero cards. */
  raised: {
    shadowColor: "#5A3719",
    shadowOpacity: 0.16,
    shadowRadius: 22,
    shadowOffset: { width: 0, height: 10 },
    elevation: 6,
  },
  /** The primary button's coral glow. */
  accent: {
    shadowColor: "#F8593C",
    shadowOpacity: 0.35,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 10 },
    elevation: 6,
  },
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
  /** Bottom padding for tab screens so content scrolls clear of the floating dock. */
  tabClearance: 110,
} as const;

/** Resolve the accent hex for a named theme (falls back to coral). */
export function accentFor(name: AccentName = "coral"): string {
  return accents[name] ?? accents.coral;
}
