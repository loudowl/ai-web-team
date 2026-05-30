import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  RefreshControl, StatusBar,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { listProjects } from '../services/api';
import { useProjectStore } from '../store/projectStore';

const STATUS_CHIP = {
  pending: { color: '#8b949e', bg: '#21262d', label: 'Pending' },
  running: { color: '#d29922', bg: '#2d2208', label: 'Running' },
  done:    { color: '#3fb950', bg: '#0d2010', label: 'Done' },
  error:   { color: '#f85149', bg: '#2d0f0f', label: 'Error' },
};

function ProjectCard({ project, onPress }) {
  const chip = STATUS_CHIP[project.status] || STATUS_CHIP.pending;
  return (
    <TouchableOpacity style={styles.card} onPress={onPress} activeOpacity={0.75}>
      <View style={styles.cardTop}>
        <Text style={styles.cardName} numberOfLines={1}>{project.name}</Text>
        <View style={[styles.chip, { backgroundColor: chip.bg, borderColor: chip.color }]}>
          <Text style={[styles.chipText, { color: chip.color }]}>{chip.label}</Text>
        </View>
      </View>
      <Text style={styles.cardBrief} numberOfLines={2}>{project.brief}</Text>
      <View style={styles.cardMeta}>
        <Text style={styles.metaText}>
          {project.provider.toUpperCase()} · {project.model}
        </Text>
        <Text style={styles.metaText}>
          {new Date(project.created_at).toLocaleDateString()}
        </Text>
      </View>
      {project.github_url ? (
        <Text style={styles.githubLink} numberOfLines={1}>⎋ {project.github_url}</Text>
      ) : null}
    </TouchableOpacity>
  );
}

export default function HomeScreen() {
  const navigation = useNavigation();
  const { setProjects, setActiveProject, resetRun } = useProjectStore();
  const [projects, setLocal] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await listProjects();
      setLocal(data);
      setProjects(data);
    } catch (e) {
      console.warn('Failed to load projects', e);
    }
  }, []);

  useEffect(() => { load(); }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await load();
    setRefreshing(false);
  };

  const openProject = (project) => {
    setActiveProject(project);
    resetRun();
    navigation.navigate('Project', { projectId: project.id });
  };

  return (
    <View style={styles.container}>
      <StatusBar barStyle="light-content" />
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>AI Web Team</Text>
          <Text style={styles.headerSub}>Multi-agent project generator</Text>
        </View>
        <TouchableOpacity
          style={styles.settingsBtn}
          onPress={() => navigation.navigate('Settings')}
        >
          <Ionicons name="settings-outline" size={22} color="#8b949e" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={projects}
        keyExtractor={item => item.id}
        renderItem={({ item }) => (
          <ProjectCard project={item} onPress={() => openProject(item)} />
        )}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#58a6ff" />}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyIcon}>🤖</Text>
            <Text style={styles.emptyTitle}>No projects yet</Text>
            <Text style={styles.emptyText}>Tap + to describe a web project and watch your AI team build it.</Text>
          </View>
        }
        contentContainerStyle={styles.list}
      />

      <TouchableOpacity
        style={styles.fab}
        onPress={() => navigation.navigate('NewProject')}
        activeOpacity={0.85}
      >
        <Ionicons name="add" size={28} color="#fff" />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0d1117' },
  header: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 20, paddingTop: 56, paddingBottom: 16,
    backgroundColor: '#161b22', borderBottomWidth: 1, borderBottomColor: '#30363d',
  },
  headerTitle: { fontSize: 22, fontWeight: '700', color: '#e6edf3' },
  headerSub:   { fontSize: 12, color: '#8b949e', marginTop: 2 },
  settingsBtn: { padding: 8 },
  list: { padding: 16, paddingBottom: 100 },
  card: {
    backgroundColor: '#161b22', borderRadius: 12, borderWidth: 1,
    borderColor: '#30363d', padding: 16, marginBottom: 12,
  },
  cardTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 },
  cardName: { fontSize: 16, fontWeight: '700', color: '#e6edf3', flex: 1, marginRight: 8 },
  chip: { borderRadius: 12, borderWidth: 1, paddingHorizontal: 8, paddingVertical: 2 },
  chipText: { fontSize: 10, fontWeight: '700' },
  cardBrief: { fontSize: 13, color: '#8b949e', lineHeight: 18, marginBottom: 10 },
  cardMeta: { flexDirection: 'row', justifyContent: 'space-between' },
  metaText: { fontSize: 11, color: '#484f58' },
  githubLink: { fontSize: 11, color: '#58a6ff', marginTop: 6 },
  empty: { alignItems: 'center', paddingTop: 80, paddingHorizontal: 32 },
  emptyIcon:  { fontSize: 48, marginBottom: 16 },
  emptyTitle: { fontSize: 18, fontWeight: '700', color: '#e6edf3', marginBottom: 8 },
  emptyText:  { fontSize: 14, color: '#8b949e', textAlign: 'center', lineHeight: 20 },
  fab: {
    position: 'absolute', bottom: 32, right: 24,
    width: 56, height: 56, borderRadius: 28,
    backgroundColor: '#238636', alignItems: 'center', justifyContent: 'center',
    shadowColor: '#3fb950', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4, shadowRadius: 8, elevation: 8,
  },
});
