# Monaco Editor Multi-Language Support

**Date:** 2026-05-05
**Components:** `StandaloneEditor.tsx` (AI Assistant), `CodeEditor.tsx` (Builder)

## Problem

The Monaco editor in the AI assistant *appears* to only support JavaScript, even though syntax highlighting already works for 20+ languages. Three issues cause this:

1. **Starter files are exclusively web languages** (`index.html`, `style.css`, `app.js`, `README.md`). A first-time user never sees non-JS highlighting in action.
2. **The "new file" dialog is a raw `prompt()`** with no hint about available languages.
3. **No `beforeMount` callback on the `<Editor>` component** means TypeScript's language service is unconfigured (no compiler options, no type-aware IntelliSense).

Monaco's CDN build (v0.55.1 via `@monaco-editor/react`) already ships syntax highlighting and basic keyword completions for 30+ languages — this is not broken. The fix is about **discoverability** and **TypeScript configuration**.

## Design

### 1. Starter Templates with Language Variety

Replace the static `STARTER_FILES` with a template picker. The picker is triggered by a **"New" dropdown button** in the Explorer header bar (replacing the current single "+" button). It does not show on every mount.

If a project already has files when "New Project" is clicked, a confirmation dialog asks: *"This will replace all current files. Continue?"*

**Templates with full file contents:**

**Web App** (default, unchanged):
```
README.md:
  # My Project\n\nBuilt with Hack the Valley AI Assistant.
src/index.html:
  <!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8">\n  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n  <title>My Project</title>\n  <link rel="stylesheet" href="css/style.css">\n</head>\n<body>\n  <h1>Hello World</h1>\n  <script src="js/app.js"></script>\n</body>\n</html>
src/css/style.css:
  body {\n  font-family: system-ui, sans-serif;\n  margin: 0;\n  padding: 2rem;\n  background: #0f172a;\n  color: #f1f5f9;\n}\n\nh1 {\n  font-size: 2rem;\n  font-weight: 700;\n}
src/js/app.js:
  document.addEventListener("DOMContentLoaded", () => {\n  console.log("App ready!");\n});
```

**Python Script** (flat structure):
```
README.md:
  # Python Project\n\nBuilt with Hack the Valley AI Assistant.
main.py:
  import argparse\n\n\ndef main():\n    parser = argparse.ArgumentParser(description="Your script")\n    parser.add_argument("--name", default="World", help="Who to greet")\n    args = parser.parse_args()\n    print(f"Hello, {args.name}!")\n\n\nif __name__ == "__main__":\n    main()
requirements.txt:
  # Add your dependencies here\n# e.g., requests>=2.31.0
```

**TypeScript App**:
```
README.md:
  # TypeScript Project\n\nBuilt with Hack the Valley AI Assistant.
src/index.ts:
  interface AppConfig {\n  title: string;\n  version: string;\n}\n\nconst config: AppConfig = {\n  title: "My App",\n  version: "1.0.0",\n};\n\ndocument.addEventListener("DOMContentLoaded", () => {\n  const root = document.getElementById("root");\n  if (root) {\n    root.textContent = `Welcome to ${config.title}`;\n  }\n  console.log("App ready!", config);\n});
tsconfig.json:
  {\n  "compilerOptions": {\n    "target": "ES2022",\n    "module": "ESNext",\n    "strict": true,\n    "jsx": "react",\n    "moduleResolution": "bundler",\n    "esModuleInterop": true,\n    "skipLibCheck": true\n  },\n  "include": ["src"]\n}
```

**Go App** (flat — no `src/`, as is idiomatic for Go):
```
README.md:
  # Go Project\n\nBuilt with Hack the Valley AI Assistant.
main.go:
  package main\n\nimport (\n\t"fmt"\n\t"log"\n\t"net/http"\n)\n\nfunc main() {\n\thttp.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {\n\t\tfmt.Fprintf(w, "Hello from Go!")\n\t})\n\tlog.Println("Server starting on :8080")\n\tlog.Fatal(http.ListenAndServe(":8080", nil))\n}
go.mod:
  module example.com/myapp\n\ngo 1.22
```

### 2. `beforeMount` for TypeScript Language Service

Add a `beforeMount(monaco)` prop to the `<Editor>` component that configures TypeScript's compiler options:

```typescript
monaco.languages.typescript.javascriptDefaults.setCompilerOptions({
  target: monaco.languages.typescript.ScriptTarget.ES2022,
  strict: true,
  moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
  esModuleInterop: true,
  allowNonTsExtensions: true,
})

monaco.languages.typescript.typescriptDefaults.setCompilerOptions({
  target: monaco.languages.typescript.ScriptTarget.ES2022,
  strict: true,
  jsx: monaco.languages.typescript.JsxEmit.React,
  moduleResolution: monaco.languages.typescript.ModuleResolutionKind.NodeJs,
  esModuleInterop: true,
})
```

This is the only language-specific configuration needed. Monaco's CDN build already handles syntax highlighting and basic completions for all other mapped languages (Python, Go, C++, YAML, SQL, etc.). No custom `CompletionItemProvider` or `register()` calls are needed.

### 3. New File Dialog

Replace `prompt()` with a small inline dialog (a floating panel, not a browser native dialog) containing:

- **File name input** — text field (free-form). Users can include folder paths (e.g., `src/utils/helper.py`). The parent path defaults to the project root (`''`), so flat-structured templates (Python, Go) don't force files into `src/`.
- **Language quick-pick bar** — buttons labeled with extensions (`.py`, `.ts`, `.go`, `.js`, `.html`, `.css`, `.jsx`, `.tsx`, `.sql`, `.sh`) that set the file name to `untitled<ext>`
- **Cancel / Create buttons**
- **Duplicate handling**: if a file with the same path already exists, show an inline error message

### 4. Shared Language Config

Create `frontend/src/utils/languageConfig.ts` exporting:

- `getLanguageFromPath(path: string): string` — unified mapping (the superset of both existing versions)
- `getExtBadge(name: string): { label: string; color: string }` — extension badge colors
- `getFileIcon(filename: string): string` — emoji icon for file types (extracted from `CodeEditor.tsx`)
- `LANGUAGE_MAP: Record<string, string>` — extension → language ID, for consumers to enumerate available extensions
- `EXT_BADGE_COLORS: Record<string, string>` — extension → color, for badge rendering
- `FILE_ICONS: Record<string, string>` — extension → emoji, for file tree icons

Both `StandaloneEditor.tsx` and `CodeEditor.tsx` import from this shared module, keeping their mappings in sync. Each component continues using its existing visual style: `StandaloneEditor` uses `getExtBadge` (colored monospace text labels like `.ts` in blue), `CodeEditor` uses `getFileIcon` (emoji icons like 📘 for `.ts`). No visual migration — only the data lives in the shared module.

### 5. `CodeEditor.tsx` Parity

Add the same `beforeMount` TypeScript config to `CodeEditor.tsx`. Update it to import from the shared `languageConfig.ts`, gaining the additional extension mappings it currently lacks (`svg`, `sh`, `bash`, `yaml`, `sql`, `env`, `gitignore`).

### 6. Explorer "New" dropdown

Replace the current "+" and "+F" buttons in the Explorer header with a single "New" button that opens a small dropdown with:

- **New File** — opens the New File dialog
- **New Folder** — prompts for folder name (same as current "+F")
- **New Project** — opens the template picker (with confirmation if files exist)

## Non-Goals

- Custom `CompletionItemProvider` for Python/Go — Monaco's built-in completions are sufficient
- `monaco.languages.register()` — languages are already registered by Monaco's CDN build
- Worker/fetch configuration — the default CDN loader works
- Full LSP integration — requires backend infrastructure beyond scope

## Implementation Order

1. Create `frontend/src/utils/languageConfig.ts` with shared helpers
2. Update `StandaloneEditor.tsx` to import from shared config, add `beforeMount` with TS config
3. Update `CodeEditor.tsx` to import from shared config, add `beforeMount` with TS config
4. Build New File dialog component
5. Build "New" dropdown in Explorer header with template picker
6. Verify: each template loads with correct syntax highlighting; opening a `.ts` file with `const x: number = 'hello'` shows a type error; creating a `.py` file via the dialog highlights Python keywords
7. Verify config parity: `getLanguageFromPath('file.ino') === 'cpp'` (migration of CodeEditor's special-case extension); `getLanguageFromPath('file.svg') === 'xml'` now works in CodeEditor too (previously only StandaloneEditor had this mapping); `getLanguageFromPath('file.sh') === 'shell'` works in both editors
