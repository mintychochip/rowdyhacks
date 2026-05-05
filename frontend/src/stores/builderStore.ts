// ============================================================
// Builder Store - Zustand with sessionStorage persistence
// ============================================================

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  BuilderState,
  BuilderMode,
  Project,
  ProjectPlan,
  ProjectType,
  PlanTask,
  ProjectFile,
} from '../types/builder';

const generateId = () =>
  `${Date.now().toString(36)}-${Math.random().toString(36).substring(2, 9)}`;

const initialState = {
  mode: 'chat' as BuilderMode,
  project: null as Project | null,
  currentPlan: null as ProjectPlan | null,
  openFiles: [] as string[],
  currentFileId: null as string | null,
  isPlanPanelOpen: true,
  isFilePanelOpen: true,
};

export const useBuilderStore = create<BuilderState>()(
  persist(
    (set, get) => ({
      ...initialState,

      // Mode
      setMode: (mode) => set({ mode }),

      // Project
      setProject: (project) => set({ project }),

      // Plan
      setCurrentPlan: (currentPlan) => set({ currentPlan }),

      updateTaskStatus: (taskId, status) => {
        const { currentPlan } = get();
        if (!currentPlan) return;

        const updatedTasks = currentPlan.tasks.map((task) =>
          task.id === taskId ? { ...task, status } : task
        );

        set({
          currentPlan: {
            ...currentPlan,
            tasks: updatedTasks,
            updatedAt: new Date().toISOString(),
          },
        });
      },

      // Files
      setOpenFiles: (openFiles) => set({ openFiles }),

      addOpenFile: (fileId) => {
        const { openFiles } = get();
        if (!openFiles.includes(fileId)) {
          set({ openFiles: [...openFiles, fileId] });
        }
      },

      removeOpenFile: (fileId) => {
        const { openFiles, currentFileId } = get();
        const filtered = openFiles.filter((id) => id !== fileId);
        set({
          openFiles: filtered,
          currentFileId: currentFileId === fileId ? filtered[0] || null : currentFileId,
        });
      },

      setCurrentFileId: (currentFileId) => set({ currentFileId }),

      // UI State
      setIsPlanPanelOpen: (isPlanPanelOpen) => set({ isPlanPanelOpen }),
      setIsFilePanelOpen: (isFilePanelOpen) => set({ isFilePanelOpen }),

      // Project Files
      setProjectFiles: (files) => {
        const { project } = get();
        if (!project) return;

        // Add README as a file if provided separately
        const readmeFile = files.find((f) => f.path === 'README.md');
        const allFiles = readmeFile
          ? files
          : [
              ...files,
              {
                id: `readme-${Date.now()}`,
                path: 'README.md',
                content: '', // README content will be set by the caller if needed
                language: 'markdown',
                isModified: false,
                isOpen: false,
              },
            ];

        set({
          project: {
            ...project,
            files: allFiles,
            updatedAt: new Date().toISOString(),
          },
        });
      },

      // Actions
      createProject: (name, description, projectType) => {
        const now = new Date().toISOString();
        const newProject: Project = {
          id: generateId(),
          name,
          description,
          projectType,
          plan: null,
          files: [],
          currentFileId: null,
          isSaved: false,
          createdAt: now,
          updatedAt: now,
        };
        set({
          project: newProject,
          mode: 'plan',
          currentPlan: null,
          openFiles: [],
          currentFileId: null,
        });
      },

      updateFile: (fileId, content) => {
        const { project } = get();
        if (!project) return;

        const updatedFiles = project.files.map((file) =>
          file.id === fileId
            ? { ...file, content, isModified: true }
            : file
        );

        set({
          project: {
            ...project,
            files: updatedFiles,
            isSaved: false,
            updatedAt: new Date().toISOString(),
          },
        });
      },

      markFileModified: (fileId, isModified) => {
        const { project } = get();
        if (!project) return;

        const updatedFiles = project.files.map((file) =>
          file.id === fileId ? { ...file, isModified } : file
        );

        set({
          project: {
            ...project,
            files: updatedFiles,
          },
        });
      },

      reset: () => set(initialState),
    }),
    {
      name: 'builder-storage',
      storage: createJSONStorage(() => sessionStorage),
    }
  )
);
