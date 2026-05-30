/**
 * SettingsScreen — model manager + API key configuration.
 * Shows installed Ollama models with pull/delete, and provider status.
 */
import React, { useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, ScrollView, TouchableOpacity,
  TextInput, Alert, ActivityIndicator,
} from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { Ionicons } from '@expo/vector-icons';
import { listModels, deleteModel } from '../services/api';

const WS_URL = process.env.EXPO_PUBLIC_API_URL?.replace(/^http/, 'ws') || 'ws://localhost:3001';

function ModelRow({ model, onDelete }) {
  const sizeGB = model.size ? (model.size / 1e9).toFixed(1) + ' GB' : '';
  return (
    <View style={styles.modelRow}>
      <View style={styles.modelInfo}>
        <Text style={styles.modelName}>{model.name}</Text>
        {sizeGB ? <Text style={styles.modelMeta}>{sizeGB}</Text> : null}
      </View>
      <TouchableOpacity style={styles.deleteBtn} onPress={() => onDelete(model.name)}>
        <Ionicons name="trash-outline" size={16} color="#f85149" />
      </TouchableOpacity>
    </View>
  );
}

function PullProgress({ model, onDone }) {
  const [status, setStatus] = useState('Starting pull...');
  const [pct, setPct]       = useState(0);

  useEffect(() => {
    const apiUrl = process.env.EXPO_PUBLIC_API_URL || 'http://localhost:3001';
    fetch(`${apiUrl}/api/models/pull`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model }),
    }).then(async (resp) => {
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text = decoder.decode(value);
        const lines = text.split('\n').filter(l => l.startsWith('data:'));
        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(5));
            if (data.status === 'complete') { onDone(); return; }
            setStatus(data.status || '');
            setPct(data.pct || 0);
          } catch {}
        }
      }
      onDone();
    }).catch(e => { Alert.alert('Pull failed', e.message); onDone(); });
  }, [model]);

  return (
    <View style={styles.pullProgress}>
      <Text style={styles.pullStatus}>{status}</Text>
      <View style={styles.progressBar}>
        <View style={[styles.progressFill, { width: `${pct}%` }]} />
      </View>
      <Text style={styles.pullPct}>{pct}%</Text>
    </View>
  );
}

export default function SettingsScreen() {
  const navigation = useNavigation();
  const [models, setModels]         = useState(null);
  const [pullModel, setPullModel]   = useState('');
  const [pulling, setPulling]       = useState(false);
  const [loading, setLoading]       = useState(true);

  const load = () => {
    setLoading(true);
    listModels().then(m => { setModels(m); setLoading(false); }).catch(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleDelete = (modelName) => {
    Alert.alert('Delete model', `Remove ${modelName} from Ollama?`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete', style: 'destructive', onPress: async () => {
          try {
            await deleteModel(modelName);
            load();
          } catch (e) {
            Alert.alert('Error', e.message);
          }
        }
      }
    ]);
  };

  const startPull = () => {
    if (!pullModel.trim()) return;
    setPulling(true);
  };

  return (
    <View style={styles.container}>
      <View style={styles.navBar}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Ionicons name="chevron-back" size={24} color="#58a6ff" />
        </TouchableOpacity>
        <Text style={styles.navTitle}>Settings & Models</Text>
        <View style={{ width: 40 }} />
      </View>

      <ScrollView contentContainerStyle={styles.content}>

        {/* Providers */}
        <Text style={styles.section}>AI Providers</Text>
        {models?.providers ? Object.entries(models.providers).map(([key, info]) => (
          <View key={key} style={styles.providerRow}>
            <View style={[styles.dot, { backgroundColor: info.available ? '#3fb950' : '#f85149' }]} />
            <View style={{ flex: 1 }}>
              <Text style={styles.providerName}>{key.charAt(0).toUpperCase() + key.slice(1)}</Text>
              <Text style={styles.providerModel}>{info.model}</Text>
            </View>
            <Text style={[styles.providerStatus, { color: info.available ? '#3fb950' : '#f85149' }]}>
              {info.available ? 'Ready' : 'No key'}
            </Text>
          </View>
        )) : loading ? <ActivityIndicator color="#58a6ff" /> : null}

        {/* Ollama models */}
        <Text style={styles.section}>Ollama Models</Text>
        {loading ? (
          <ActivityIndicator color="#58a6ff" style={{ marginTop: 16 }} />
        ) : models?.ollama?.length ? (
          models.ollama.map((m) => (
            <ModelRow key={m.name} model={m} onDelete={handleDelete} />
          ))
        ) : (
          <Text style={styles.emptyText}>No models installed. Pull one below.</Text>
        )}

        {/* Pull model */}
        <Text style={styles.section}>Pull New Model</Text>
        <View style={styles.pullRow}>
          <TextInput
            style={styles.pullInput}
            placeholder="e.g. llama3.2, mistral, codellama"
            placeholderTextColor="#484f58"
            value={pullModel}
            onChangeText={setPullModel}
            autoCapitalize="none"
            autoCorrect={false}
          />
          <TouchableOpacity style={styles.pullBtn} onPress={startPull} disabled={pulling}>
            {pulling ? <ActivityIndicator color="#fff" size="small" /> : <Text style={styles.pullBtnText}>Pull</Text>}
          </TouchableOpacity>
        </View>

        {pulling && (
          <PullProgress
            model={pullModel.trim()}
            onDone={() => { setPulling(false); setPullModel(''); load(); }}
          />
        )}

        <Text style={styles.hint}>
          Popular models: llama3.2 (fast), mistral (balanced), codellama (code), deepseek-coder (code), phi3 (lightweight)
        </Text>

        {/* API URL */}
        <Text style={styles.section}>Backend URL</Text>
        <Text style={styles.configValue}>{process.env.EXPO_PUBLIC_API_URL || 'http://localhost:3001'}</Text>
        <Text style={styles.hint}>Set EXPO_PUBLIC_API_URL in your .env file to change.</Text>

      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container:  { flex: 1, backgroundColor: '#0d1117' },
  navBar: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
    paddingHorizontal: 12, paddingTop: 54, paddingBottom: 12,
    backgroundColor: '#161b22', borderBottomWidth: 1, borderBottomColor: '#30363d',
  },
  backBtn:    { padding: 8 },
  navTitle:   { fontSize: 17, fontWeight: '700', color: '#e6edf3' },
  content:    { padding: 20, paddingBottom: 60 },
  section:    { fontSize: 11, fontWeight: '700', color: '#8b949e', textTransform: 'uppercase', letterSpacing: 1, marginTop: 24, marginBottom: 10 },
  providerRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#161b22', borderRadius: 10, borderWidth: 1, borderColor: '#30363d', padding: 12, marginBottom: 8 },
  dot:         { width: 10, height: 10, borderRadius: 5, marginRight: 12 },
  providerName:  { fontSize: 14, fontWeight: '600', color: '#e6edf3' },
  providerModel: { fontSize: 11, color: '#8b949e', marginTop: 2 },
  providerStatus: { fontSize: 12, fontWeight: '600' },
  modelRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: '#161b22', borderRadius: 10, borderWidth: 1, borderColor: '#30363d', padding: 12, marginBottom: 8 },
  modelInfo:  { flex: 1 },
  modelName:  { fontSize: 14, fontWeight: '600', color: '#e6edf3' },
  modelMeta:  { fontSize: 11, color: '#8b949e', marginTop: 2 },
  deleteBtn:  { padding: 8 },
  emptyText:  { color: '#8b949e', fontSize: 13, fontStyle: 'italic' },
  pullRow: { flexDirection: 'row', gap: 10 },
  pullInput: {
    flex: 1, backgroundColor: '#161b22', borderRadius: 10, borderWidth: 1,
    borderColor: '#30363d', padding: 12, color: '#e6edf3', fontSize: 14,
  },
  pullBtn:     { backgroundColor: '#238636', borderRadius: 10, paddingHorizontal: 18, justifyContent: 'center' },
  pullBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  pullProgress: { marginTop: 12, backgroundColor: '#161b22', borderRadius: 10, padding: 12 },
  pullStatus:  { color: '#8b949e', fontSize: 12, marginBottom: 6 },
  progressBar: { height: 4, backgroundColor: '#21262d', borderRadius: 2, overflow: 'hidden', marginBottom: 4 },
  progressFill:{ height: '100%', backgroundColor: '#3fb950', borderRadius: 2 },
  pullPct:     { color: '#3fb950', fontSize: 11, fontWeight: '700' },
  hint:        { fontSize: 11, color: '#484f58', marginTop: 8, lineHeight: 16 },
  configValue: { fontSize: 13, color: '#58a6ff', fontFamily: 'monospace' },
});
