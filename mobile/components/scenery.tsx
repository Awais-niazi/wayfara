/**
 * Finnish scenery — the visual moments of the travel identity.
 *
 * Four curated scenes drawn in react-native-svg (ships in the bundle, crisp
 * at any size, no photo licensing): harbour dawn, aurora night, winter
 * forest, lakeside dusk. Every city maps to ONE scene — coastal cities
 * arrive by sea, Lapland gets the aurora, lake-district cities get the lake,
 * a hash covers the rest — so the same city always looks the same.
 *
 * Palette note: these greens/indigos/ice-blues are ILLUSTRATION colors only.
 * UI chrome (buttons, chips, text) stays on the coral/cream tokens in theme/.
 */
import React from "react";
import { View, Text, StyleSheet, type ViewStyle } from "react-native";
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from "react-native-svg";

import { fonts } from "../theme";

export type SceneName = "harbour" | "aurora" | "forest" | "lakeside";

const CITY_SCENES: Record<string, SceneName> = {
  helsinki: "harbour",
  espoo: "harbour",
  turku: "harbour",
  vaasa: "harbour",
  kotka: "harbour",
  porvoo: "harbour",
  rovaniemi: "aurora",
  oulu: "aurora",
  kemi: "aurora",
  tornio: "aurora",
  kajaani: "aurora",
  tampere: "lakeside",
  jyväskylä: "lakeside",
  kuopio: "lakeside",
  lappeenranta: "lakeside",
  joensuu: "lakeside",
  savonlinna: "lakeside",
  mikkeli: "lakeside",
  hämeenlinna: "lakeside",
};

const HASH_FALLBACK: SceneName[] = ["forest", "lakeside", "harbour"];

export function sceneFor(city: string): SceneName {
  const key = (city || "").trim().toLowerCase();
  if (CITY_SCENES[key]) return CITY_SCENES[key];
  let h = 0;
  for (let i = 0; i < key.length; i++) h = (h * 31 + key.charCodeAt(i)) >>> 0;
  return HASH_FALLBACK[h % HASH_FALLBACK.length];
}

/* ─── The four scenes (viewBox 375×160, bottom-anchored slice) ─────────────── */

function HarbourScene({ id }: { id: string }) {
  return (
    <>
      <Defs>
        <LinearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#FFE3CB" />
          <Stop offset="1" stopColor="#F3C6A4" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y="0" width="375" height="160" fill={`url(#${id}-sky)`} />
      <Circle cx="296" cy="52" r="26" fill="#F8A468" opacity={0.9} />
      <Circle cx="296" cy="52" r="38" fill="#F8A468" opacity={0.22} />
      {/* distant skyline + cathedral dome */}
      <Path
        d="M0 96 H40 V82 H64 V96 H96 V74 H104 V66 H112 V74 H120 V96 H160 V84 H186 V96 H375 V126 H0 Z"
        fill="#EDCBA6"
      />
      <Path d="M196 96 C196 80 232 80 232 96 L232 100 H196 Z" fill="#9DB8A5" />
      <Rect x="211" y="70" width="5" height="12" fill="#9DB8A5" />
      <Circle cx="213.5" cy="68" r="3.4" fill="#9DB8A5" />
      {/* terracotta harbour roofline */}
      <Path d="M0 126 V104 L20 92 L40 104 V126 H70 V110 L88 98 L106 110 V126 Z" fill="#D8794E" />
      <Path d="M262 126 V108 L282 94 L302 108 V126 H326 V102 L346 88 L366 102 V126 H375 V126 H262 Z" fill="#CE6A40" />
      {/* water */}
      <Rect x="0" y="124" width="375" height="36" fill="#E8B48D" />
      <Path d="M28 138 H86" stroke="#FFF3E2" strokeWidth="3" strokeLinecap="round" opacity={0.5} />
      <Path d="M160 148 H236" stroke="#FFF3E2" strokeWidth="3" strokeLinecap="round" opacity={0.4} />
      <Path d="M286 136 H322" stroke="#F8A468" strokeWidth="4" strokeLinecap="round" opacity={0.5} />
      {/* sailboat */}
      <Path d="M116 146 L140 146 L135 152 L121 152 Z" fill="#B3542E" />
      <Path d="M127 146 V126 L140 143 Z" fill="#FDF8F0" />
    </>
  );
}

function AuroraScene({ id }: { id: string }) {
  return (
    <>
      <Defs>
        <LinearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#1E2745" />
          <Stop offset="1" stopColor="#39456B" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y="0" width="375" height="160" fill={`url(#${id}-sky)`} />
      {/* aurora ribbons — stacked translucency instead of blur */}
      <Path d="M-10 74 C70 22 160 66 250 30 C300 12 350 22 385 8 L385 34 C330 48 290 36 244 56 C160 92 80 50 -10 96 Z" fill="#7FD8B4" opacity={0.28} />
      <Path d="M-10 66 C80 22 170 58 260 26 C310 10 352 18 385 6 L385 20 C336 34 300 28 252 44 C168 74 84 42 -10 82 Z" fill="#A5EBCB" opacity={0.4} />
      {/* stars */}
      <Circle cx="46" cy="26" r="1.6" fill="#EAF2FF" opacity={0.9} />
      <Circle cx="120" cy="14" r="1.2" fill="#EAF2FF" opacity={0.7} />
      <Circle cx="205" cy="20" r="1.4" fill="#EAF2FF" opacity={0.8} />
      <Circle cx="332" cy="40" r="1.6" fill="#EAF2FF" opacity={0.9} />
      <Circle cx="290" cy="72" r="1.2" fill="#EAF2FF" opacity={0.6} />
      {/* moon */}
      <Circle cx="330" cy="58" r="12" fill="#F3EAD2" opacity={0.95} />
      {/* pine silhouettes */}
      <Path d="M30 132 L44 96 L58 132 Z M38 118 L44 102 L50 118 Z" fill="#141A30" />
      <Path d="M78 132 L90 104 L102 132 Z" fill="#141A30" />
      <Path d="M256 132 L272 90 L288 132 Z" fill="#141A30" />
      <Path d="M306 132 L318 106 L330 132 Z" fill="#141A30" />
      {/* snow */}
      <Path d="M0 132 C90 122 240 140 375 128 L375 160 L0 160 Z" fill="#E9EDF4" />
      <Path d="M60 144 H150" stroke="#C9D4E6" strokeWidth="3" strokeLinecap="round" opacity={0.6} />
      <Path d="M230 150 H310" stroke="#C9D4E6" strokeWidth="3" strokeLinecap="round" opacity={0.5} />
    </>
  );
}

function ForestScene({ id }: { id: string }) {
  return (
    <>
      <Defs>
        <LinearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#DCEAF2" />
          <Stop offset="1" stopColor="#F4F8F9" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y="0" width="375" height="160" fill={`url(#${id}-sky)`} />
      <Circle cx="86" cy="44" r="20" fill="#FFFFFF" opacity={0.9} />
      <Circle cx="86" cy="44" r="30" fill="#FFFFFF" opacity={0.35} />
      {/* far ridge of pines */}
      <Path
        d="M0 110 L18 96 L36 110 L54 90 L72 110 L92 94 L112 110 L134 88 L156 110 L176 96 L196 110 L218 92 L240 110 L260 98 L280 110 L302 90 L324 110 L344 98 L364 110 L375 104 V126 H0 Z"
        fill="#9BB3AB"
        opacity={0.75}
      />
      {/* near pines */}
      <Path d="M28 128 L48 82 L68 128 Z M40 110 L48 90 L56 110 Z" fill="#48645A" />
      <Path d="M96 128 L112 94 L128 128 Z" fill="#3E5A4E" />
      <Path d="M226 128 L246 78 L266 128 Z M238 108 L246 86 L254 108 Z" fill="#48645A" />
      <Path d="M300 128 L316 96 L332 128 Z" fill="#3E5A4E" />
      {/* frozen lake / snow field */}
      <Path d="M0 128 C110 118 260 136 375 124 L375 160 L0 160 Z" fill="#EFF4F1" />
      <Path d="M84 142 H180" stroke="#CFDEDA" strokeWidth="3" strokeLinecap="round" opacity={0.7} />
      <Path d="M248 150 H330" stroke="#CFDEDA" strokeWidth="3" strokeLinecap="round" opacity={0.55} />
    </>
  );
}

function LakesideScene({ id }: { id: string }) {
  return (
    <>
      <Defs>
        <LinearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#F9D8C0" />
          <Stop offset="1" stopColor="#EFB9A0" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y="0" width="375" height="160" fill={`url(#${id}-sky)`} />
      <Circle cx="70" cy="50" r="22" fill="#F49A6C" opacity={0.9} />
      <Circle cx="70" cy="50" r="33" fill="#F49A6C" opacity={0.25} />
      {/* far shore */}
      <Path d="M0 104 C80 94 160 100 240 92 C300 86 350 94 375 90 V118 H0 Z" fill="#C98A6B" opacity={0.55} />
      {/* cabin with a lit window */}
      <Path d="M256 112 V92 L276 78 L296 92 V112 Z" fill="#8A4A38" />
      <Rect x="270" y="96" width="12" height="10" fill="#FFD9A0" />
      <Rect x="288" y="80" width="5" height="12" fill="#6E392B" />
      {/* birches */}
      <Rect x="46" y="76" width="5" height="38" rx="2.5" fill="#FBF3E6" />
      <Path d="M46 84 H51 M46 96 H51 M46 106 H51" stroke="#5A4636" strokeWidth="1.6" />
      <Rect x="66" y="68" width="5" height="46" rx="2.5" fill="#FBF3E6" />
      <Path d="M66 78 H71 M66 90 H71 M66 102 H71" stroke="#5A4636" strokeWidth="1.6" />
      <Path d="M34 78 C42 62 58 60 64 64 C74 54 90 58 92 68 C84 62 44 64 34 78 Z" fill="#B9A26B" opacity={0.9} />
      {/* lake */}
      <Rect x="0" y="114" width="375" height="46" fill="#E3A385" />
      <Path d="M40 130 H120" stroke="#FBE1CB" strokeWidth="3" strokeLinecap="round" opacity={0.55} />
      <Path d="M180 142 H268" stroke="#FBE1CB" strokeWidth="3" strokeLinecap="round" opacity={0.45} />
      <Path d="M58 124 H96" stroke="#F49A6C" strokeWidth="4" strokeLinecap="round" opacity={0.45} />
      {/* rowboat */}
      <Path d="M300 138 L330 138 L324 145 L306 145 Z" fill="#6E392B" />
    </>
  );
}

const SCENES: Record<SceneName, (p: { id: string }) => React.JSX.Element> = {
  harbour: HarbourScene,
  aurora: AuroraScene,
  forest: ForestScene,
  lakeside: LakesideScene,
};

/** Ink that reads on each scene's sky — for text overlaid near the TOP. */
export const SCENE_OVERLAY_INK: Record<SceneName, string> = {
  harbour: "#6E392B",
  aurora: "#EAF2FF",
  forest: "#3E5A4E",
  lakeside: "#6E392B",
};

/* ─── Components ───────────────────────────────────────────────────────────── */

let uid = 0;

/** Full-width panorama strip. Bottom-anchored, crops from the top as height
 *  shrinks. `scene` overrides the city mapping (e.g. a fixed header scene). */
export function CityScape({
  city,
  scene,
  height = 160,
}: {
  city?: string;
  scene?: SceneName;
  height?: number;
}) {
  const name = scene ?? sceneFor(city ?? "");
  const Scene = SCENES[name];
  // Stable per-instance gradient ids — duplicated SVG defs ids bleed between
  // instances on web.
  const id = React.useRef(`sc${uid++}`).current;
  return (
    <Svg width="100%" height={height} viewBox="0 0 375 160" preserveAspectRatio="xMidYMax slice">
      <Scene id={id} />
    </Svg>
  );
}

/** Rounded mini-vignette for list rows: the city's scene with its code
 *  printed on a soft scrim — replaces the abstract letter badge. */
export function CityTile({
  city,
  code,
  size = 48,
  style,
}: {
  city: string;
  code: string;
  size?: number;
  style?: ViewStyle;
}) {
  const name = sceneFor(city);
  const Scene = SCENES[name];
  const id = React.useRef(`ct${uid++}`).current;
  const light = name === "aurora";
  return (
    <View style={[{ width: size, height: size, borderRadius: 14, overflow: "hidden" }, style]}>
      <Svg width={size} height={size} viewBox="60 0 240 160" preserveAspectRatio="xMidYMax slice">
        <Scene id={id} />
      </Svg>
      <View style={[tileStyles.scrim, light && tileStyles.scrimLight]}>
        <Text style={[tileStyles.code, light && tileStyles.codeLight]} numberOfLines={1}>
          {code}
        </Text>
      </View>
    </View>
  );
}

const tileStyles = StyleSheet.create({
  scrim: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingVertical: 2,
    alignItems: "center",
    backgroundColor: "rgba(251,246,239,0.82)",
  },
  scrimLight: { backgroundColor: "rgba(20,26,48,0.55)" },
  code: {
    fontFamily: fonts.monoBold,
    fontSize: 9,
    letterSpacing: 1.2,
    color: "#6E392B",
  },
  codeLight: { color: "#EAF2FF" },
});
