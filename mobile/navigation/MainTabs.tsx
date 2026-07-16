/**
 * The signed-in tab dock — a floating pill bar that persists across Home,
 * Explore, Apps, Chat and Profile. Replaces the old hand-drawn bar that only
 * existed on Home (tapping a "tab" used to push a stack screen and the bar
 * vanished — the number-one structural cause of the app feeling off).
 */
import React from "react";
import { View, Text, StyleSheet, Pressable, Platform } from "react-native";
import { createBottomTabNavigator, type BottomTabBarProps } from "@react-navigation/bottom-tabs";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { colors, fonts, shadow } from "../theme";
import {
  HomeIcon,
  CompassIcon,
  AppsIcon,
  ChatIcon,
  ProfileIcon,
  type IconProps,
} from "../components/icons";
import type { TabParamList } from "./types";
import HomeScreen from "../screens/HomeScreen";
import MatchesScreen from "../screens/MatchesScreen";
import ApplicationsScreen from "../screens/ApplicationsScreen";
import ChatScreen from "../screens/ChatScreen";
import ProfileScreen from "../screens/ProfileScreen";

const Tab = createBottomTabNavigator<TabParamList>();

const TAB_ICONS: Record<keyof TabParamList, (p: IconProps) => React.JSX.Element> = {
  Home: HomeIcon,
  Explore: CompassIcon,
  Apps: AppsIcon,
  Chat: ChatIcon,
  Profile: ProfileIcon,
};

function TravelTabBar({ state, descriptors, navigation }: BottomTabBarProps) {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.dockWrap, { paddingBottom: Math.max(insets.bottom, 10) }]} pointerEvents="box-none">
      <View style={styles.dock}>
        {state.routes.map((route, index) => {
          const focused = state.index === index;
          const label = descriptors[route.key].options.title ?? route.name;
          const Icon = TAB_ICONS[route.name as keyof TabParamList];
          const tint = focused ? colors.accent : "#A99B8D";
          return (
            <Pressable
              key={route.key}
              accessibilityRole="button"
              accessibilityState={{ selected: focused }}
              accessibilityLabel={label}
              onPress={() => {
                const event = navigation.emit({
                  type: "tabPress",
                  target: route.key,
                  canPreventDefault: true,
                });
                if (!focused && !event.defaultPrevented) {
                  navigation.navigate(route.name);
                }
              }}
              style={({ pressed }) => [styles.tab, pressed && { opacity: 0.7 }]}
            >
              <View style={[styles.tabInner, focused && styles.tabInnerActive]}>
                <Icon size={22} color={tint} />
                <Text style={[styles.tabLabel, { color: tint }, focused && { fontFamily: fonts.bodyBold }]}>
                  {label}
                </Text>
              </View>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
}

export default function MainTabs() {
  return (
    <Tab.Navigator
      tabBar={(props) => <TravelTabBar {...props} />}
      screenOptions={{
        headerShown: false,
        sceneStyle: { backgroundColor: colors.canvas },
      }}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Explore" component={MatchesScreen} />
      <Tab.Screen name="Apps" component={ApplicationsScreen} />
      <Tab.Screen name="Chat" component={ChatScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  dockWrap: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 16,
    alignItems: "center",
  },
  dock: {
    flexDirection: "row",
    width: "100%",
    maxWidth: 560, // desktop web: dock stays hand-sized, centered
    backgroundColor: Platform.OS === "web" ? "rgba(255,255,255,0.96)" : "#FFFFFF",
    borderWidth: 1,
    borderColor: colors.borderSoft,
    borderRadius: 28,
    paddingVertical: 8,
    paddingHorizontal: 8,
    ...shadow.raised,
  },
  tab: { flex: 1 },
  tabInner: {
    alignItems: "center",
    justifyContent: "center",
    gap: 3,
    paddingVertical: 6,
    borderRadius: 20,
  },
  tabInnerActive: { backgroundColor: colors.accentSoft },
  tabLabel: { fontFamily: fonts.bodySemi, fontSize: 10 },
});
