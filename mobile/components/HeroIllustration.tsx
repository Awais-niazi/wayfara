/**
 * Welcome-screen hero: a warm Helsinki harbour scene (sun, cathedral, harbour
 * roofline, water) drawn in react-native-svg so it ships with the bundle —
 * no photo licensing, crisp at any size, and always on-palette. Replace with
 * a real campus/student photograph when brand assets land.
 */
import React from "react";
import Svg, { Circle, Defs, LinearGradient, Path, Rect, Stop } from "react-native-svg";

export function HeroIllustration() {
  return (
    <Svg width="100%" height="100%" viewBox="0 0 375 258" preserveAspectRatio="xMidYMax slice">
      <Defs>
        <LinearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#FFE3CB" />
          <Stop offset="0.7" stopColor="#F9D3B4" />
          <Stop offset="1" stopColor="#F3C6A4" />
        </LinearGradient>
        <LinearGradient id="water" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor="#E8B48D" />
          <Stop offset="1" stopColor="#DCA57E" />
        </LinearGradient>
      </Defs>

      {/* sky + low sun */}
      <Rect x="0" y="0" width="375" height="258" fill="url(#sky)" />
      <Circle cx="292" cy="74" r="34" fill="#F8A468" opacity="0.9" />
      <Circle cx="292" cy="74" r="48" fill="#F8A468" opacity="0.25" />

      {/* distant skyline */}
      <Path
        d="M0 150 H28 V128 H52 V150 H80 V118 H88 V110 H96 V118 H104 V150 H140 V132 H166 V150 H375 V196 H0 Z"
        fill="#EDCBA6"
      />

      {/* Helsinki Cathedral — centred, ivory with pale-green domes */}
      <Rect x="146" y="152" width="110" height="46" fill="#FBF3E6" />
      <Rect x="140" y="192" width="122" height="6" fill="#F3E7D3" />
      {/* colonnade */}
      <Rect x="156" y="160" width="7" height="32" fill="#EBDDC5" />
      <Rect x="172" y="160" width="7" height="32" fill="#EBDDC5" />
      <Rect x="188" y="160" width="7" height="32" fill="#EBDDC5" />
      <Rect x="204" y="160" width="7" height="32" fill="#EBDDC5" />
      <Rect x="220" y="160" width="7" height="32" fill="#EBDDC5" />
      <Rect x="236" y="160" width="7" height="32" fill="#EBDDC5" />
      {/* pediment + main dome */}
      <Path d="M146 152 L201 136 L256 152 Z" fill="#F7EDDA" />
      <Path d="M178 138 C178 118 224 118 224 138 L224 142 H178 Z" fill="#9DB8A5" />
      <Rect x="198" y="106" width="6" height="16" fill="#9DB8A5" />
      <Circle cx="201" cy="104" r="4" fill="#9DB8A5" />
      {/* side domes */}
      <Path d="M148 146 C148 136 168 136 168 146 L168 152 H148 Z" fill="#9DB8A5" />
      <Path d="M234 146 C234 136 254 136 254 146 L254 152 H234 Z" fill="#9DB8A5" />

      {/* harbour roofline, terracotta */}
      <Path
        d="M0 198 V166 L20 154 L40 166 V198 H64 V172 L82 160 L100 172 V198 H120 V178 H136 V198 Z"
        fill="#D8794E"
      />
      <Path
        d="M262 198 V176 L282 162 L302 176 V198 H322 V170 L344 156 L366 170 V198 H375 V198 H262 Z"
        fill="#CE6A40"
      />

      {/* water */}
      <Rect x="0" y="196" width="375" height="62" fill="url(#water)" />
      <Path d="M24 214 H92" stroke="#FFF3E2" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
      <Path d="M150 226 H240" stroke="#FFF3E2" strokeWidth="3" strokeLinecap="round" opacity="0.45" />
      <Path d="M286 212 H332" stroke="#FFF3E2" strokeWidth="3" strokeLinecap="round" opacity="0.55" />
      <Path d="M60 240 H124" stroke="#FFF3E2" strokeWidth="3" strokeLinecap="round" opacity="0.3" />
      <Path d="M252 244 H310" stroke="#FFF3E2" strokeWidth="3" strokeLinecap="round" opacity="0.3" />
      {/* sun glint on the water */}
      <Path d="M276 206 H308" stroke="#F8A468" strokeWidth="4" strokeLinecap="round" opacity="0.5" />
      <Path d="M282 218 H302" stroke="#F8A468" strokeWidth="4" strokeLinecap="round" opacity="0.35" />

      {/* sailboat */}
      <Path d="M118 236 L146 236 L140 244 L124 244 Z" fill="#B3542E" />
      <Path d="M131 236 V210 L146 232 Z" fill="#FDF8F0" />
      <Path d="M129 236 V214 L118 232 Z" fill="#F7EDDA" />
    </Svg>
  );
}
