/**
 * AgentKanban — top section of the project screen.
 * Shows 4 agent cards in a horizontal row with status indicators.
 */
import React from 'react';
import { View, Text, StyleSheet, ScrollView, TouchableOpacity, Animated } from 'react-native';
import { useProjectStore } from '../store/projectStore';

const STATUS_COLORS = {
  pending:  '#30363d',
  running:  '#d29922',
  done:     '#3fb950',
  error:    '#f85149',
};

const STATUS_LABELS = {
  pending:  'Waiting',
  running:  'Working…',
  done:     'Done ✓',
  error:    'Error ✗',
};

export default function AgentKanban({ onAgentPress }) {
  const { AGENTS, AGENT_META, agentStates, activeAgent } = useProjectStore();

  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>AGENT STATUS</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {AGENTS.map(agentKey => {
          const meta   = AGENT_META[agentKey];
          const state  = agentStates[agentKey];
          const isActive = agentKey === activeAgent;
          const progress = state.status === 'running';

          return (
            <TouchableOpacity
              key={agentKey}
              style={[
                styles.card,
                { borderColor: meta.color },
                isActive && styles.cardActive,
              ]}
              onPress={() => onAgentPress && onAgentPress(agentKey)}
              activeOpacity={0.8}
            >
              {/* Glow border when active */}
              {isActive && (
                <View style={[styles.activeBorder, { backgroundColor: meta.color + '33' }]} />
              )}

              <Text style={styles.icon}>{meta.icon}</Text>
              <Text style={[styles.label, { color: meta.color }]}>{meta.label}</Text>

              <View style={[styles.statusBadge, { backgroundColor: STATUS_COLORS[state.status] + '33', borderColor: STATUS_COLORS[state.status] }]}>
                <Text style={[styles.statusText, { color: STATUS_COLORS[state.status] }]}>
                  {STATUS_LABELS[state.status]}
                </Text>
              </View>

              {/* Progress bar */}
              {progress && (
                <View style={styles.progressBar}>
                  <View style={[styles.progressFill, { backgroundColor: meta.color }]} />
                </View>
              )}

              {/* Output preview */}
              {state.output.length > 0 && (
                <Text style={styles.preview} numberOfLines={2}>
                  {state.output.slice(0, 80)}…
                </Text>
              )}
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingTop: 12,
    paddingBottom: 8,
    backgroundColor: '#161b22',
    borderBottomWidth: 1,
    borderBottomColor: '#30363d',
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: '#8b949e',
    letterSpacing: 1,
    marginLeft: 16,
    marginBottom: 8,
  },
  row: {
    paddingHorizontal: 12,
    gap: 10,
  },
  card: {
    width: 150,
    backgroundColor: '#0d1117',
    borderRadius: 10,
    borderWidth: 1.5,
    padding: 12,
    minHeight: 110,
    overflow: 'hidden',
  },
  cardActive: {
    shadowColor: '#58a6ff',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.4,
    shadowRadius: 8,
    elevation: 6,
  },
  activeBorder: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    borderRadius: 8,
  },
  icon: {
    fontSize: 22,
    marginBottom: 4,
  },
  label: {
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 6,
  },
  statusBadge: {
    borderRadius: 20,
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 2,
    alignSelf: 'flex-start',
    marginBottom: 6,
  },
  statusText: {
    fontSize: 10,
    fontWeight: '600',
  },
  progressBar: {
    height: 3,
    backgroundColor: '#21262d',
    borderRadius: 2,
    overflow: 'hidden',
    marginBottom: 6,
  },
  progressFill: {
    height: '100%',
    width: '60%',
    borderRadius: 2,
    opacity: 0.8,
  },
  preview: {
    fontSize: 9,
    color: '#8b949e',
    lineHeight: 13,
  },
});
