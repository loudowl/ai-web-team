import React from 'react';
import { NavigationContainer, DefaultTheme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { StatusBar } from 'expo-status-bar';

import HomeScreen      from './src/screens/HomeScreen';
import NewProjectScreen from './src/screens/NewProjectScreen';
import ProjectScreen   from './src/screens/ProjectScreen';
import SettingsScreen  from './src/screens/SettingsScreen';

const Stack = createNativeStackNavigator();

const DarkTheme = {
  ...DefaultTheme,
  colors: {
    ...DefaultTheme.colors,
    background:  '#0d1117',
    card:        '#161b22',
    text:        '#e6edf3',
    border:      '#30363d',
    notification:'#58a6ff',
  },
};

export default function App() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <NavigationContainer theme={DarkTheme}>
        <StatusBar style="light" />
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          <Stack.Screen name="Home"       component={HomeScreen} />
          <Stack.Screen name="NewProject" component={NewProjectScreen} />
          <Stack.Screen name="Project"    component={ProjectScreen} />
          <Stack.Screen name="Settings"   component={SettingsScreen} />
        </Stack.Navigator>
      </NavigationContainer>
    </GestureHandlerRootView>
  );
}
