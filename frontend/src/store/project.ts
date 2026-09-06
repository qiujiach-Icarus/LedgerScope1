import { create } from 'zustand';
import axios from 'axios';

export interface ProjectSummary {
  id: string;
  name: string;
  dataset_count: number;
  memory_count: number;
  total_count: number;
  anomaly_count: number;
  avg_risk_score: number;
  last_file?: string;
  created_at?: string;
  updated_at?: string;
}

interface ProjectState {
  activeProjectId: string | null;
  projects: ProjectSummary[];
  loading: boolean;
  dataVersion: number;
  loadProjects: () => Promise<void>;
  setActiveProject: (id: string) => Promise<void>;
  createProject: (name: string) => Promise<void>;
  bumpDataVersion: () => void;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  activeProjectId: null,
  projects: [],
  loading: false,
  dataVersion: 0,

  loadProjects: async () => {
    set({ loading: true });
    try {
      const res = await axios.get('/api/projects');
      const projects: ProjectSummary[] = res.data?.projects || [];
      const active = res.data?.active_project_id || projects[0]?.id || null;
      set({ projects, activeProjectId: active });
    } catch {
      // 后端未就绪时保持空态
    } finally {
      set({ loading: false });
    }
  },

  setActiveProject: async (id: string) => {
    set({ activeProjectId: id });
    try {
      await axios.post('/api/projects/active', { project_id: id });
    } catch {
      // 本地切换失败不阻断 UI
    }
  },

  createProject: async (name: string) => {
    const res = await axios.post('/api/projects', { name });
    const created: ProjectSummary = res.data;
    set({ activeProjectId: created.id });
    await get().loadProjects();
  },

  bumpDataVersion: () => set(s => ({ dataVersion: s.dataVersion + 1 })),
}));
