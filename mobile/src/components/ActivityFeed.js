/**
 * ActivityFeed — scrolling chat-style list of agent events.
 * Shows agent avatars, status messages, and live streaming tokens.
 */
import React, { useRef, useEffect } from 'react';
import { View, Text, StyleSheet, FlatList, Animated } from 'react-native';
import { useProjectStore } from '../store/projectStore';

const SYSTEM_META = { label: 'System', icon: '⚙️', color: '#8b949e' };

function FeedItem({ message }) {
  const { AGENT_META } = useProjectStore();
  const meta = AGENT_META[message.agent] || SYSTEM_META;
  const isError = message.type === 'error';
  const isDone  = message.type === 'done';

  return (
    <View style={[styles.item, isError && styles.itemError]}>
      <View style={[styles.avatar, { backgroundColor: meta.color + '22', borderColor: meta.color }]}>
        <Text style={styles.avatarIcon}>{meta.icon}</Text>
      </View>
      <View style={styles.bubble}>
        <View style={styles.bubbleHeader}>
          <Text style={[styles.agentName, { color: meta.color }]}>{meta.label}</Text>
          <Text style={styles.timestamp}>
            {message.ts?.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
          </Text>
        </View>
        <Text style={[styles.messageText, isDone && styles.doneText, isError && styles.errorText]}>
          {message.text}
        </Text>
      </View>
    </View>
  );
}

function StreamingOutput({ agentKey }) {
  const { agentStates, AGENT_META } = useProjectStore();
  const state = agentStates[agentKey];
  const meta  = AGENT_META[agentKey];

  if (state.status !== 'running' || !state.output) return null;

  // Show last 300 chars to avoid huge renders
  const preview = state.output.slice(-300);

  return (
    <View style={styles.streamingContainer}>
      <View style={[styles.streamingDot, { backgroundColor: meta.color }]} />
      <View style={styles.streamingBubble}>
        <Text style={[styles.agentName, { color: meta.color, marginBottom: 4 }]}>
          {meta.icon} {meta.label} — streaming
        </Text>
        <Text style={styles.streamingText}>{preview}</Text>
        <View style={styles.cursor} />
      </View>
    </View>
  );
}

export default function ActivityFeed() {
  const { feedMessages, activeAgent } = useProjectStore();
  const listRef = useRef(null);

  useEffect(() => {
    if (listRef.current && feedMessages.length) {
      listRef.current.scrollToEnd({ animated: true });
    }
  }, [feedMessages.length]);

  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>ACTIVITY FEED</Text>
      <FlatList
        ref={listRef}
        data={feedMessages}
        keyExtractor={item => String(item.id)}
        renderItem={({ item }) => <FeedItem message={item} />}
        ListFooterComponent={activeAgent ? <StreamingOutput agentKey={activeAgent} /> : null}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0d1117',
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: '#8b949e',
    letterSpacing: 1,
    marginHorizontal: 16,
    marginTop: 12,
    marginBottom: 6,
  },
  list: {
    paddingHorizontal: 12,
    paddingBottom: 16,
  },
  item: {
    flexDirection: 'row',
    marginBottom: 12,
    alignItems: 'flex-start',
  },
  itemError: {
    opacity: 0.85,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
    marginTop: 2,
  },
  avatarIcon: {
    fontSize: 16,
  },
  bubble: {
    flex: 1,
    backgroundColor: '#161b22',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#30363d',
    padding: 10,
  },
  bubbleHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  agentName: {
    fontSize: 12,
    fontWeight: '700',
  },
  timestamp: {
    fontSize: 10,
    color: '#8b949e',
  },
  messageText: {
    fontSize: 13,
    color: '#e6edf3',
    lineHeight: 18,
  },
  doneText: {
    color: '#3fb950',
  },
  errorText: {
    color: '#f85149',
  },

  // Streaming
  streamingContainer: {
    flexDirection: 'row',
    marginBottom: 12,
    alignItems: 'flex-start',
  },
  streamingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginTop: 14,
    marginRight: 8,
    marginLeft: 14,
  },
  streamingBubble: {
    flex: 1,
    backgroundColor: '#161b22',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#30363d',
    padding: 10,
  },
  streamingText: {
    fontSize: 12,
    color: '#8b949e',
    lineHeight: 17,
    fontFamily: 'monospace',
  },
  cursor: {
    width: 8,
    height: 14,
    backgroundColor: '#58a6ff',
    marginTop: 2,
    borderRadius: 1,
    opacity: 0.9,
  },
});
