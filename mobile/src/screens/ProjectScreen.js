/**
 * ProjectScreen — the main "mission control" view.
 * Top: AgentKanban (status board)
 * Middle: ActivityFeed (streaming chat)
 * Bottom: action bar (view output, push to GitHub)
 */
import React, { useEffect, useRef, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, Alert,
  Modal, ScrollView, Share, ActivityIndicator,
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import Markdown from 'react-native-markdown-display';

import AgentKanban from '../components/AgentKanban';
import ActivityFeed from '../components/ActivityFeed';
import { connectWS, getProject, pushToGitHub } from '../services/api';
import { useProjectStore } from '../store/projectStore';

export default function ProjectScreen() {
  const navigation = useNavigation();
  const route = useRoute();
  const { projectId } = route.params;

  const {
    activeProject, setActiveProject,
    agentStates, feedMessages, handleWsEvent, setWs, resetRun,
    AGENTS, AGENT_META,
  } = useProjectStore();

  const wsRef = useRef(null);
  const [project, setProject]     = useState(activeProject);
  const [modalAgent, setModalAgent] = useState(null); // agent key for output modal
  const [pushing, setPushing]      = useState(false);

  // Load project and connect WS
  useEffect(() => {
    let mounted = true;
    getProject(projectId).then(p => { if (mounted) { setProject(p); setActiveProject(p); } });

    const ws = connectWS(
      projectId,
      (event) => { handleWsEvent(event); },
      () => {
        // On close, refresh project
        getProject(projectId).then(p => { if (mounted) { setProject(p); setActiveProject(p); } });
      }
    );
    wsRef.current = ws;
    setWs(ws);

    return () => {
      mounted = false;
      ws.close();
    };
  }, [projectId]);

  const handlePushToGitHub = async () => {
    if (!project?.github_url === false && project?.status !== 'done') {
      Alert.alert('Not ready', 'Wait for all agents to finish before pushing to GitHub.');
      return;
    }
    if (project?.github_url) {
      await Share.share({ message: project.github_url, url: project.github_url });
      return;
    }
    Alert.alert(
      'Push to GitHub',
      `Create a new GitHub repo and push the generated project?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Push', onPress: async () => {
            setPushing(true);
            try {
              const result = await pushToGitHub(projectId);
              const updated = await getProject(projectId);
              setProject(updated);
              setActiveProject(updated);
              Alert.alert('✅ Pushed!', result.github_url, [
                { text: 'Share', onPress: () => Share.share({ message: result.github_url, url: result.github_url }) },
                { text: 'OK' },
              ]);
            } catch (e) {
              Alert.alert('Error', e.response?.data?.detail || e.message);
            } finally {
              setPushing(false);
            }
          }
        },
      ]
    );
  };

  const isDone    = project?.status === 'done';
  const isRunning = project?.status === 'running';

  return (
    <View style={styles.container}>
      {/* Nav bar */}
      <View style={styles.navBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color="#58a6ff" />
        </TouchableOpacity>
        <View style={styles.navCenter}>
          <Text style={styles.navTitle} numberOfLines={1}>{project?.name || 'Project'}</Text>
          <View style={[styles.statusDot, { backgroundColor: isRunning ? '#d29922' : isDone ? '#3fb950' : '#8b949e' }]} />
        </View>
        <TouchableOpacity style={styles.navBtn} onPress={() => navigation.navigate('Settings')}>
          <Ionicons name="settings-outline" size={20} color="#8b949e" />
        </TouchableOpacity>
      </View>

      {/* Kanban board */}
      <AgentKanban onAgentPress={key => setModalAgent(key)} />

      {/* Activity feed */}
      <View style={styles.feedContainer}>
        <ActivityFeed />
      </View>

      {/* Action bar */}
      <View style={styles.actionBar}>
        <TouchableOpacity
          style={styles.outlineBtn}
          onPress={() => {
            // Show last agent with output
            const lastDone = [...AGENTS].reverse().find(a => agentStates[a].output);
            if (lastDone) setModalAgent(lastDone);
          }}
        >
          <Ionicons name="document-text-outline" size={18} color="#58a6ff" />
          <Text style={styles.outlineBtnText}>View Output</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.primaryBtn, (!isDone && !project?.github_url) && styles.btnDisabled]}
          onPress={handlePushToGitHub}
          disabled={pushing}
        >
          {pushing ? (
            <ActivityIndicator color="#fff" size="small" />
          ) : (
            <>
              <Ionicons name={project?.github_url ? "open-outline" : "logo-github"} size={18} color="#fff" />
              <Text style={styles.primaryBtnText}>
                {project?.github_url ? 'View on GitHub' : 'Push to GitHub'}
              </Text>
            </>
          )}
        </TouchableOpacity>
      </View>

      {/* Output modal */}
      <Modal
        visible={!!modalAgent}
        animationType="slide"
        onRequestClose={() => setModalAgent(null)}
      >
        <View style={styles.modal}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitle}>
              {modalAgent ? `${AGENT_META[modalAgent]?.icon} ${AGENT_META[modalAgent]?.label} Output` : ''}
            </Text>
            <TouchableOpacity onPress={() => setModalAgent(null)} style={styles.closeBtn}>
              <Ionicons name="close" size={24} color="#e6edf3" />
            </TouchableOpacity>
          </View>

          {/* Agent tabs */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.agentTabs}>
            {AGENTS.map(a => (
              <TouchableOpacity
                key={a}
                style={[styles.agentTab, modalAgent === a && styles.agentTabActive]}
                onPress={() => setModalAgent(a)}
              >
                <Text style={[styles.agentTabText, modalAgent === a && { color: '#58a6ff' }]}>
                  {AGENT_META[a].icon} {AGENT_META[a].label}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>

          <ScrollView style={styles.modalBody}>
            {modalAgent && (
              <Markdown style={markdownStyles}>
                {agentStates[modalAgent]?.output || '_No output yet._'}
              </Markdown>
            )}
          </ScrollView>
        </View>
      </Modal>
    </View>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: '#0d1117' },
  navBar: {
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: 12, paddingTop: 52, paddingBottom: 10,
    backgroundColor: '#161b22', borderBottomWidth: 1, borderBottomColor: '#30363d',
  },
  backBtn:   { padding: 8 },
  navCenter: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 },
  navTitle:  { fontSize: 16, fontWeight: '700', color: '#e6edf3' },
  statusDot: { width: 8, height: 8, borderRadius: 4 },
  navBtn:    { padding: 8 },
  feedContainer: { flex: 1 },
  actionBar: {
    flexDirection: 'row', gap: 10, padding: 14,
    paddingBottom: 28, backgroundColor: '#161b22',
    borderTopWidth: 1, borderTopColor: '#30363d',
  },
  outlineBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 12, borderRadius: 10,
    borderWidth: 1.5, borderColor: '#58a6ff', backgroundColor: 'transparent',
  },
  outlineBtnText: { color: '#58a6ff', fontSize: 14, fontWeight: '700' },
  primaryBtn: {
    flex: 1.5, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 6, paddingVertical: 12, borderRadius: 10, backgroundColor: '#238636',
  },
  primaryBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  btnDisabled:    { opacity: 0.45 },

  // Modal
  modal:       { flex: 1, backgroundColor: '#0d1117' },
  modalHeader: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    padding: 16, paddingTop: 56, backgroundColor: '#161b22',
    borderBottomWidth: 1, borderBottomColor: '#30363d',
  },
  modalTitle:  { fontSize: 16, fontWeight: '700', color: '#e6edf3' },
  closeBtn:    { padding: 6 },
  agentTabs: {
    backgroundColor: '#161b22', borderBottomWidth: 1, borderBottomColor: '#30363d',
    paddingHorizontal: 8, paddingVertical: 6,
  },
  agentTab: {
    paddingHorizontal: 14, paddingVertical: 7, borderRadius: 20,
    marginRight: 6, backgroundColor: '#21262d',
  },
  agentTabActive:  { backgroundColor: '#0d1d2e' },
  agentTabText:    { fontSize: 12, fontWeight: '600', color: '#8b949e' },
  modalBody:       { flex: 1, padding: 16 },
});

const markdownStyles = {
  body:     { color: '#e6edf3', fontSize: 14, lineHeight: 22 },
  heading1: { color: '#58a6ff', fontSize: 22, fontWeight: '700', marginTop: 16, marginBottom: 8 },
  heading2: { color: '#58a6ff', fontSize: 18, fontWeight: '700', marginTop: 14, marginBottom: 6 },
  heading3: { color: '#d29922', fontSize: 15, fontWeight: '700', marginTop: 10, marginBottom: 4 },
  code_inline: { backgroundColor: '#161b22', color: '#3fb950', fontFamily: 'monospace', fontSize: 12 },
  fence:    { backgroundColor: '#161b22', padding: 12, borderRadius: 8, marginVertical: 8 },
  code_block: { color: '#e6edf3', fontFamily: 'monospace', fontSize: 11 },
  blockquote: { borderLeftColor: '#d29922', borderLeftWidth: 3, paddingLeft: 10, color: '#8b949e' },
  bullet_list_icon: { color: '#58a6ff' },
  hr:       { backgroundColor: '#30363d' },
  strong:   { color: '#e6edf3', fontWeight: '700' },
  link:     { color: '#58a6ff' },
};
