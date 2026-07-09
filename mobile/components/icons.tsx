/**
 * Icon set for the Wayfara screens — react-native-svg reimplementations of the
 * inline SVGs in the design mockup. Each icon takes { size, color } and, for
 * stroke icons, inherits sensible round caps/joins to match the source.
 */
import React from "react";
import Svg, { Path, Circle, Rect, G } from "react-native-svg";

export interface IconProps {
  size?: number;
  color?: string;
  strokeWidth?: number;
}

const stroke = (color: string, strokeWidth: number) => ({
  fill: "none" as const,
  stroke: color,
  strokeWidth,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export function PinIcon({ size = 12, color = "#fff", strokeWidth = 2.2 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M12 21 C12 21 5 14.5 5 9.5 A7 7 0 0 1 19 9.5 C19 14.5 12 21 12 21 Z" {...stroke(color, strokeWidth)} />
      <Circle cx="12" cy="9.5" r="2.4" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function ChevronLeftIcon({ size = 18, color = "#4A3D31", strokeWidth = 2.4 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M15 5 L8 12 L15 19" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function ChevronRightIcon({ size = 20, color = "#B4841A", strokeWidth = 2.4 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M9 5 L16 12 L9 19" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function AppleIcon({ size = 17, color = "#fff" }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path
        d="M16.4 12.6 c0-2.5 2-3.7 2.1-3.8 -1.1-1.7-2.9-1.9-3.5-1.9 -1.5-.15-2.9.87-3.6.87 -.75 0-1.9-.85-3.1-.83 -1.6.03-3.1.93-3.9 2.36 -1.66 2.9-.42 7.2 1.2 9.5 .8 1.13 1.75 2.4 3 2.35 1.2-.05 1.65-.78 3.1-.78 1.45 0 1.85.78 3.1.75 1.28-.02 2.1-1.15 2.9-2.28 .9-1.3 1.28-2.57 1.3-2.63 -.03-.02-2.5-.96-2.5-3.83 Z M14 4.9 c.66-.8 1.1-1.9.98-3 -.95.04-2.1.63-2.78 1.43 -.6.7-1.13 1.83-.99 2.9 1.06.08 2.14-.54 2.79-1.33 Z"
        fill={color}
      />
    </Svg>
  );
}

export function EyeIcon({ size = 20, color = "#A2917F", strokeWidth = 1.9 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M2 12 C4 6.5 8 4.5 12 4.5 C16 4.5 20 6.5 22 12 C20 17.5 16 19.5 12 19.5 C8 19.5 4 17.5 2 12 Z" {...stroke(color, strokeWidth)} />
      <Circle cx="12" cy="12" r="3" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function BellIcon({ size = 20, color = "#4A3D31", strokeWidth = 1.9 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M6 16 V10 A6 6 0 0 1 18 10 V16 L20 18.5 H4 Z" {...stroke(color, strokeWidth)} />
      <Path d="M10 18.5 A2 2 0 0 0 14 18.5" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function UploadIcon({ size = 20, color = "#fff", strokeWidth = 2 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M12 16 V5 M8 9 L12 5 L16 9" {...stroke(color, strokeWidth)} />
      <Path d="M5 15 V18 A1 1 0 0 0 6 19 H18 A1 1 0 0 0 19 18 V15" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

// ── Quick-action icons ───────────────────────────────────────────────────────
export function VisaIcon({ size = 21, color = "#F8593C", strokeWidth = 1.9 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Rect x="5" y="3" width="14" height="18" rx="2.5" {...stroke(color, strokeWidth)} />
      <Circle cx="12" cy="10" r="2.6" {...stroke(color, strokeWidth)} />
      <Path d="M9 15.5 H15" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function PlaneIcon({ size = 21, color = "#2A6FDB" }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path
        d="M21 16 L13.4 12.8 V6.4 A1.4 1.4 0 0 0 10.6 6.4 V12.8 L3 16 V17.6 L10.6 15.4 V19 L8.4 20.5 V21.6 L12 20.6 L15.6 21.6 V20.5 L13.4 19 V15.4 L21 17.6 Z"
        fill={color}
      />
    </Svg>
  );
}

export function HousingIcon({ size = 21, color = "#1F8A5B", strokeWidth = 1.9 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M4 18 V8 M4 13 H15 A4 4 0 0 1 19 17 V18 M19 18 V13 M7.5 11.5 H10.5" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function SparkleIcon({ size = 21, color = "#7B4FD6" }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M12 3 L13.6 9.2 L20 11 L13.6 12.8 L12 19 L10.4 12.8 L4 11 L10.4 9.2 Z" fill={color} />
    </Svg>
  );
}

// ── Tab bar icons ────────────────────────────────────────────────────────────
export function HomeIcon({ size = 24, color = "#A99B8D", strokeWidth = 2 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M3 11 L12 3.5 L21 11" {...stroke(color, strokeWidth)} />
      <Path d="M5.5 9.3 V20.5 H18.5 V9.3" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function CompassIcon({ size = 24, color = "#A99B8D", strokeWidth = 2 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Circle cx="12" cy="12" r="9" {...stroke(color, strokeWidth)} />
      <Path d="M15.5 8.5 L13 13 L8.5 15.5 L11 11 Z" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function AppsIcon({ size = 24, color = "#A99B8D", strokeWidth = 2 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Rect x="5" y="3" width="14" height="18" rx="2.5" {...stroke(color, strokeWidth)} />
      <Path d="M9 9 H15 M9 13 H15 M9 17 H13" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function ChatIcon({ size = 24, color = "#A99B8D", strokeWidth = 2 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M20 4 H4 A1 1 0 0 0 3 5 V15 A1 1 0 0 0 4 16 H7 V20 L11.5 16 H20 A1 1 0 0 0 21 15 V5 A1 1 0 0 0 20 4 Z" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

export function ProfileIcon({ size = 24, color = "#A99B8D", strokeWidth = 2 }: IconProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Circle cx="12" cy="8" r="3.6" {...stroke(color, strokeWidth)} />
      <Path d="M5 20 A7 7 0 0 1 19 20" {...stroke(color, strokeWidth)} />
    </Svg>
  );
}

/**
 * The Wayfara "Pin Waypoint" mark — a destination pin carrying a five-waypoint
 * route that resolves into a "W". Bare mark (no container); defaults to the
 * white-on-coral treatment used inside the brand badge. Colors are overridable
 * so it also works as a monochrome/knock-out mark.
 */
export function WayfaraPin({
  size = 24,
  pin = "#FFFFFF",
  shadow = "#FDCFC1",
  route = "#F8593C",
  dotA = "#F8593C",
  dotB = "#F49A1A",
}: {
  size?: number;
  pin?: string;
  shadow?: string;
  route?: string;
  dotA?: string;
  dotB?: string;
}) {
  return (
    <Svg width={size} height={size} viewBox="0 0 66 66">
      {/* pin body + right-half shadow for depth */}
      <Path d="M33 6 C20 6 10 15.8 10 28 C10 42 33 60 33 60 C33 60 56 42 56 28 C56 15.8 46 6 33 6 Z" fill={pin} />
      <Path d="M33 6 C46 6 56 15.8 56 28 C56 42 33 60 33 60 Z" fill={shadow} />
      {/* five-waypoint route forming a W */}
      <Path
        d="M19 18 L25.5 35.5 L33 23 L40.5 35.5 L47 18"
        fill="none"
        stroke={route}
        strokeWidth={3.6}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <Circle cx="19" cy="18" r="3.6" fill={dotA} />
      <Circle cx="25.5" cy="35.5" r="3.6" fill={dotB} />
      <Circle cx="33" cy="23" r="3.6" fill={dotA} />
      <Circle cx="40.5" cy="35.5" r="3.6" fill={dotB} />
      <Circle cx="47" cy="18" r="3.6" fill={dotA} />
    </Svg>
  );
}

/** Google's four-color wordmark dot (approximated as a conic swatch). */
export function GoogleDot({ size = 19 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <G>
        <Path d="M12 12 L12 0 A12 12 0 0 1 22.39 6 Z" fill="#EA4335" />
        <Path d="M12 12 L22.39 6 A12 12 0 0 1 22.39 18 Z" fill="#FBBC05" />
        <Path d="M12 12 L22.39 18 A12 12 0 0 1 1.61 18 Z" fill="#34A853" />
        <Path d="M12 12 L1.61 18 A12 12 0 0 1 12 0 Z" fill="#4285F4" />
        <Circle cx="12" cy="12" r="5" fill="#fff" />
      </G>
    </Svg>
  );
}
