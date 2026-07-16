/**
 * Motion primitives — one rhythm for the whole app.
 *
 * Built on the core Animated API (works identically on native and web; no
 * worklets/babel setup needed). Durations sit in the 200–360ms band, enter
 * eases out, and everything respects the web caveat: useNativeDriver is
 * native-only.
 */
import React, { useEffect, useRef } from "react";
import {
  Animated,
  Easing,
  Platform,
  Pressable,
  StyleProp,
  ViewStyle,
  PressableProps,
} from "react-native";

const NATIVE = Platform.OS !== "web";

/**
 * Fade + rise on mount. Stagger lists by passing `delay={index * 60}`.
 */
export function FadeInUp({
  children,
  delay = 0,
  dy = 14,
  duration = 360,
  style,
}: {
  children: React.ReactNode;
  delay?: number;
  dy?: number;
  duration?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const opacity = useRef(new Animated.Value(0)).current;
  const shift = useRef(new Animated.Value(dy)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(opacity, {
        toValue: 1,
        duration,
        delay,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: NATIVE,
      }),
      Animated.timing(shift, {
        toValue: 0,
        duration,
        delay,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: NATIVE,
      }),
    ]).start();
  }, [opacity, shift, delay, duration]);

  return (
    <Animated.View style={[style, { opacity, transform: [{ translateY: shift }] }]}>
      {children}
    </Animated.View>
  );
}

/**
 * Pressable with a springy scale-down — the tactile press every card and
 * button shares. Replaces the flat `opacity: 0.85` pattern.
 */
export function PressableScale({
  children,
  style,
  scaleTo = 0.97,
  onPressIn,
  onPressOut,
  ...rest
}: PressableProps & {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  scaleTo?: number;
}) {
  const scale = useRef(new Animated.Value(1)).current;

  const pressIn: PressableProps["onPressIn"] = (e) => {
    Animated.spring(scale, {
      toValue: scaleTo,
      speed: 40,
      bounciness: 0,
      useNativeDriver: NATIVE,
    }).start();
    onPressIn?.(e);
  };
  const pressOut: PressableProps["onPressOut"] = (e) => {
    Animated.spring(scale, {
      toValue: 1,
      speed: 24,
      bounciness: 7,
      useNativeDriver: NATIVE,
    }).start();
    onPressOut?.(e);
  };

  return (
    <Pressable onPressIn={pressIn} onPressOut={pressOut} {...rest}>
      <Animated.View style={[style, { transform: [{ scale }] }]}>{children}</Animated.View>
    </Pressable>
  );
}

/**
 * Progress bar whose fill eases to its value instead of snapping.
 */
export function ProgressBar({
  progress,
  tint,
  track = "#F1E7DA",
  height = 6,
  style,
}: {
  /** 0..1 */
  progress: number;
  tint: string;
  track?: string;
  height?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const anim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(anim, {
      toValue: Math.max(0, Math.min(1, progress)),
      duration: 700,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: false, // width animation is layout-bound
    }).start();
  }, [anim, progress]);

  return (
    <Animated.View
      style={[
        { height, borderRadius: height / 2, backgroundColor: track, overflow: "hidden" },
        style,
      ]}
    >
      <Animated.View
        style={{
          height: "100%",
          borderRadius: height / 2,
          backgroundColor: tint,
          width: anim.interpolate({ inputRange: [0, 1], outputRange: ["0%", "100%"] }),
        }}
      />
    </Animated.View>
  );
}
