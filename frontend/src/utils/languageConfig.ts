// ── Extension → Monaco language ID ─────────────────────────
export const LANGUAGE_MAP: Record<string, string> = {
  js: 'javascript', ts: 'typescript', jsx: 'javascript', tsx: 'typescript',
  html: 'html', htm: 'html', css: 'css', scss: 'scss', less: 'less',
  py: 'python', ino: 'cpp', cpp: 'cpp', c: 'c', go: 'go', json: 'json',
  md: 'markdown', yaml: 'yaml', yml: 'yaml', xml: 'xml',
  svg: 'xml', sql: 'sql', sh: 'shell', bash: 'shell',
  gitignore: 'plaintext', env: 'plaintext',
};

export const getLanguageFromPath = (path: string): string => {
  const ext = path.split('.').pop()?.toLowerCase() || '';
  return LANGUAGE_MAP[ext] || 'plaintext';
};

// ── Extension badge colors (for StandaloneEditor) ──────────
export const EXT_BADGE_COLORS: Record<string, string> = {
  ts: '#3178c6', tsx: '#61dafb', js: '#f7df1e', jsx: '#61dafb',
  html: '#e34f26', css: '#1572b6', scss: '#cc6699', py: '#3776ab',
  json: '#292929', md: '#42a5f5', yaml: '#cb171e', yml: '#cb171e',
  svg: '#ffb13b', sql: '#e38c00', sh: '#4eaa25',
  gitignore: '#f05032', env: '#ecd53f',
};

export const getExtBadge = (name: string): { label: string; color: string } => {
  const ext = name.split('.').pop()?.toLowerCase() || '';
  return { label: `.${ext}`, color: EXT_BADGE_COLORS[ext] || '#64748b' };
};

// ── File icons (for CodeEditor) ────────────────────────────
export const FILE_ICONS: Record<string, string> = {
  js: '', ts: '', jsx: '', tsx: '', html: '', css: '',
  py: '', ino: '', json: '', md: '',
};

export const getFileIcon = (filename: string): string => {
  const ext = filename.split('.').pop()?.toLowerCase() || '';
  return FILE_ICONS[ext] || '';
};

// ── Starter Templates ──────────────────────────────────────
export interface FileEntry {
  id: string;
  path: string;
  content: string;
  language: string;
}

export interface TemplateDef {
  name: string;
  description: string;
  files: FileEntry[];
}

let fileCounter = 0;
const fileId = () => `f-${Date.now()}-${++fileCounter}`;

const WEB_APP: TemplateDef = {
  name: 'Web App',
  description: 'HTML + CSS + JavaScript',
  files: [
    { id: fileId(), path: 'README.md', content: '# My Project\n\nBuilt with AI Assistant.\n', language: 'markdown' },
    { id: fileId(), path: 'src/index.html', content: '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>My Project</title>\n  <link rel="stylesheet" href="css/style.css">\n</head>\n<body>\n  <h1>Hello World</h1>\n  <script src="js/app.js"></script>\n</body>\n</html>\n', language: 'html' },
    { id: fileId(), path: 'src/css/style.css', content: 'body {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n  padding: 2rem;\n  background: #0f172a;\n  color: #f1f5f9;\n}\n\nh1 {\n  font-size: 2rem;\n  font-weight: 700;\n}\n', language: 'css' },
    { id: fileId(), path: 'src/js/app.js', content: 'document.addEventListener("DOMContentLoaded", () => {\n  console.log("App ready!");\n});\n', language: 'javascript' },
  ],
};

const PYTHON: TemplateDef = {
  name: 'Python Script',
  description: 'Python with argparse',
  files: [
    { id: fileId(), path: 'README.md', content: '# Python Project\n\nBuilt with AI Assistant.\n', language: 'markdown' },
    { id: fileId(), path: 'main.py', content: 'import argparse\n\n\ndef main():\n    parser = argparse.ArgumentParser(description="Your script")\n    parser.add_argument("--name", default="World", help="Who to greet")\n    args = parser.parse_args()\n    print(f"Hello, {args.name}!")\n\n\nif __name__ == "__main__":\n    main()\n', language: 'python' },
    { id: fileId(), path: 'requirements.txt', content: '# Add your dependencies here\n# e.g., requests>=2.31.0\n', language: 'plaintext' },
  ],
};

const TYPESCRIPT: TemplateDef = {
  name: 'TypeScript App',
  description: 'TypeScript with strict mode',
  files: [
    { id: fileId(), path: 'README.md', content: '# TypeScript Project\n\nBuilt with AI Assistant.\n', language: 'markdown' },
    { id: fileId(), path: 'src/index.ts', content: 'interface AppConfig {\n  title: string;\n  version: string;\n}\n\nconst config: AppConfig = {\n  title: "My App",\n  version: "1.0.0",\n};\n\ndocument.addEventListener("DOMContentLoaded", () => {\n  const root = document.getElementById("root");\n  if (root) {\n    root.textContent = `Welcome to ${config.title}`;\n  }\n  console.log("App ready!", config);\n});\n', language: 'typescript' },
    { id: fileId(), path: 'tsconfig.json', content: '{\n  "compilerOptions": {\n    "target": "ES2022",\n    "module": "ESNext",\n    "strict": true,\n    "jsx": "react",\n    "moduleResolution": "bundler",\n    "esModuleInterop": true,\n    "skipLibCheck": true\n  },\n  "include": ["src"]\n}\n', language: 'json' },
  ],
};

const GO: TemplateDef = {
  name: 'Go App',
  description: 'Go HTTP server',
  files: [
    { id: fileId(), path: 'README.md', content: '# Go Project\n\nBuilt with AI Assistant.\n', language: 'markdown' },
    { id: fileId(), path: 'main.go', content: 'package main\n\nimport (\n\t"fmt"\n\t"log"\n\t"net/http"\n)\n\nfunc main() {\n\thttp.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {\n\t\tfmt.Fprintf(w, "Hello from Go!")\n\t})\n\tlog.Println("Server starting on :8080")\n\tlog.Fatal(http.ListenAndServe(":8080", nil))\n}\n', language: 'go' },
    { id: fileId(), path: 'go.mod', content: 'module example.com/myapp\n\ngo 1.22\n', language: 'plaintext' },
  ],
};

export const TEMPLATES: TemplateDef[] = [WEB_APP, PYTHON, TYPESCRIPT, GO];
