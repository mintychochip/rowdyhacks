// ============================================================
// Builder Mode Types - AI Assistant Project Builder
// ============================================================

export type BuilderMode = 'chat' | 'plan' | 'build';

export type ProjectType =
  | 'web-app'
  | 'mobile-app'
  | 'api'
  | 'script'
  | 'component'
  | 'landing-page'
  | 'other';

export interface ProjectFile {
  id: string;
  path: string;
  content: string;
  language: string;
  isModified: boolean;
  isOpen: boolean;
}

export interface PlanTask {
  id: string;
  description: string;
  status: 'pending' | 'in-progress' | 'completed' | 'error';
  filePath?: string;
  dependencies: string[];
}

export interface ProjectPlan {
  id: string;
  title: string;
  description: string;
  projectType: ProjectType;
  tasks: PlanTask[];
  createdAt: string;
  updatedAt: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  projectType: ProjectType;
  plan: ProjectPlan | null;
  files: ProjectFile[];
  currentFileId: string | null;
  isSaved: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface BuilderState {
  // Mode
  mode: BuilderMode;
  setMode: (mode: BuilderMode) => void;

  // Current Project
  project: Project | null;
  setProject: (project: Project | null) => void;

  // Plan
  currentPlan: ProjectPlan | null;
  setCurrentPlan: (plan: ProjectPlan | null) => void;
  updateTaskStatus: (
    taskId: string,
    status: PlanTask['status']
  ) => void;

  // Files
  openFiles: string[];
  setOpenFiles: (fileIds: string[]) => void;
  addOpenFile: (fileId: string) => void;
  removeOpenFile: (fileId: string) => void;
  currentFileId: string | null;
  setCurrentFileId: (fileId: string | null) => void;

  // UI State
  isPlanPanelOpen: boolean;
  setIsPlanPanelOpen: (isOpen: boolean) => void;
  isFilePanelOpen: boolean;
  setIsFilePanelOpen: (isOpen: boolean) => void;

  // Actions
  createProject: (
    name: string,
    description: string,
    projectType: ProjectType
  ) => void;
  updateFile: (fileId: string, content: string) => void;
  markFileModified: (fileId: string, isModified: boolean) => void;
  reset: () => void;
}

export interface BuilderMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  metadata?: {
    projectType?: ProjectType;
    planId?: string;
    fileChanges?: string[];
  };
}
