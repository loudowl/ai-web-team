import React, { useState, useEffect } from 'react';
import {
  View, Text, StyleSheet, TextInput, TouchableOpacity,
  ScrollView, KeyboardAvoidingView, Platform, Alert,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { createProject, listModels } from '../services/api';
import { useProjectStore } from '../store/projectStore';

const PROVIDERS = [
  { key: 'openai',    label: 'OpenAI',    icon: '🤖', desc: 'GPT-4o — best quality' },
  { key: 'anthropic', label: 'Anthropic', icon: '🧠', desc: 'Claude — strong reasoning' },
  { key: 'ollama',    label: 'Ollama',    icon: '🦙', desc: 'Local — free & private' },
];

const EXAMPLE_BRIEFS = [
  "A task management app with AI-powered priority suggestions and natural language task entry",
  "A recipe generator that creates weekly meal plans based on dietary restrictions and pantry items",
  "A personal finance dashboard that categorizes spending with AI and predicts future expenses",
  "A collaborative whiteboard tool with AI sketch-to-component generation",
];

export default function NewProjectScreen() {
  const navigation = useNavigation();
  const { setActiveProject, resetRun } = useProjectStore();

  const [name, setName]           = useState('');
  const [brief, setBrief]         = useState('');
  const [provider, setProvider]   = useState('openai');
  const [models, setModels]       = useState({});
  const [loading, setLoading]     = useState(false);

  useEffect(() => {
    listModels().then(setModels).catch(() => {});
  }, []);

  const providerAvailable = (key) => {
    if (key === 'ollama') return true;
    return models.providers?.[key]?.available ?? false;
  };

  const handleCreate = async () => {
    if (!name.trim())  { Alert.alert('Name required', 'Give your project a name.'); return; }
    if (!brief.trim()) { Alert.alert('Brief required', 'Describe what you want to build.'); return; }

    setLoading(true);
    try {
      const project = await createProject({ name: name.trim(), brief: brief.trim(), provider });
      setActiveProject(project);
      resetRun();
      navigation.replace('Project', { projectId: project.id });
    } catch (e) {
      Alert.alert('Error', e.message || 'Failed to create project');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.navBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color="#58a6ff" />
        </TouchableOpacity>
        <Text style={styles.navTitle}>New Project</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">

        {/* Project name */}
        <Text style={styles.label}>Project Name</Text>
        <TextInput
          style={styles.input}
          placeholder="e.g. Recipe Generator App"
          placeholderTextColor="#484f58"
          value={name}
          onChangeText={setName}
          returnKeyType="next"
          autoFocus
        />

        {/* Brief */}
        <Text style={styles.label}>Project Brief</Text>
        <TextInput
          style={[styles.input, styles.textarea]}
          placeholder="Describe what you want to build. The more detail, the better the output."
          placeholderTextColor="#484f58"
          value={brief}
          onChangeText={setBrief}
          multiline
          numberOfLines={5}
          textAlignVertical="top"
        />

        {/* Example briefs */}
        <Text style={styles.sublabel}>Examples — tap to use:</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.examples}>
          {EXAMPLE_BRIEFS.map((ex, i) => (
            <TouchableOpacity
              key={i}
              style={styles.exampleChip}
              onPress={() => { setBrief(ex); if (!name) setName(ex.split(' ').slice(0, 4).join(' ')); }}
            >
              <Text style={styles.exampleText} numberOfLines={2}>{ex}</Text>
            </TouchableOpacity>
          ))}
        </ScrollView>

        {/* Provider */}
        <Text style={styles.label}>AI Provider</Text>
        <View style={styles.providerRow}>
          {PROVIDERS.map(p => {
            const available = providerAvailable(p.key);
            const selected  = provider === p.key;
            return (
              <TouchableOpacity
                key={p.key}
                style={[styles.providerCard, selected && styles.providerSelected, !available && styles.providerDisabled]}
                onPress={() => available && setProvider(p.key)}
                activeOpacity={available ? 0.75 : 1}
              >
                <Text style={styles.providerIcon}>{p.icon}</Text>
                <Text style={[styles.providerLabel, selected && { color: '#58a6ff' }]}>{p.label}</Text>
                <Text style={styles.providerDesc}>{p.desc}</Text>
                {!available && <Text style={styles.notConfigured}>Not configured</Text>}
              </TouchableOpacity>
            );
          })}
        </View>

        {/* Create button */}
        <TouchableOpacity
          style={[styles.createBtn, loading && styles.createBtnDisabled]}
          onPress={handleCreate}
          disabled={loading}
          activeOpacity={0.85}
        >
          <Text style={styles.createBtnText}>
            {loading ? 'Creating…' : '🚀 Launch AI Team'}
          </Text>
        </TouchableOpacity>

      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container:    { flex: 1, backgroundColor: '#0d1117' },
  navBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 12, paddingTop: 54, paddingBottom: 12,
    backgroundColor: '#161b22', borderBottomWidth: 1, borderBottomColor: '#30363d',
  },
  backBtn:    { padding: 8 },
  navTitle:   { fontSize: 17, fontWeight: '700', color: '#e6edf3' },
  content:    { padding: 20, paddingBottom: 60 },
  label:      { fontSize: 13, fontWeight: '700', color: '#8b949e', marginTop: 20, marginBottom: 8, textTransform: 'uppercase', letterSpacing: 0.6 },
  sublabel:   { fontSize: 11, color: '#484f58', marginTop: 8, marginBottom: 8 },
  input: {
    backgroundColor: '#161b22', borderRadius: 10, borderWidth: 1,
    borderColor: '#30363d', padding: 14, color: '#e6edf3', fontSize: 15,
  },
  textarea:   { height: 120, lineHeight: 22 },
  examples:   { marginBottom: 4 },
  exampleChip: {
    backgroundColor: '#161b22', borderRadius: 8, borderWidth: 1,
    borderColor: '#30363d', padding: 10, marginRight: 8, width: 200,
  },
  exampleText: { fontSize: 12, color: '#8b949e', lineHeight: 17 },
  providerRow: { flexDirection: 'row', gap: 10 },
  providerCard: {
    flex: 1, backgroundColor: '#161b22', borderRadius: 10,
    borderWidth: 1.5, borderColor: '#30363d', padding: 12, alignItems: 'center',
  },
  providerSelected: { borderColor: '#58a6ff', backgroundColor: '#0d1d2e' },
  providerDisabled: { opacity: 0.4 },
  providerIcon:  { fontSize: 22, marginBottom: 4 },
  providerLabel: { fontSize: 13, fontWeight: '700', color: '#e6edf3', marginBottom: 2 },
  providerDesc:  { fontSize: 10, color: '#8b949e', textAlign: 'center', lineHeight: 14 },
  notConfigured: { fontSize: 9, color: '#f85149', marginTop: 4 },
  createBtn: {
    backgroundColor: '#238636', borderRadius: 12, padding: 18,
    alignItems: 'center', marginTop: 32,
    shadowColor: '#3fb950', shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3, shadowRadius: 8, elevation: 6,
  },
  createBtnDisabled: { opacity: 0.6 },
  createBtnText: { fontSize: 17, fontWeight: '700', color: '#fff' },
});
