// ============================================================
// Export Button - ZIP export with auto-generated README
// ============================================================

import { useState, useCallback } from 'react';
import JSZip from 'jszip';
import { useBuilderStore } from '../../../stores/builderStore';
import type { Project, ProjectPlan, PlanTask, ProjectType } from '../../../types/builder';
import {
  PRIMARY,
  PRIMARY_HOVER,
  PRIMARY_BG20,
  RADIUS,
  SPACE,
  TEXT_PRIMARY,
  TEXT_SECONDARY,
  TEXT_MUTED,
  BORDER_LIGHT,
  SUCCESS,
  ERROR,
} from '../../../theme';

// Get tech stack based on project type and files
const getTechStack = (project: Project): string[] => {
  const stack: string[] = [];
  const extensions = new Set(
    project.files.map((f) => f.path.split('.').pop()?.toLowerCase() || '')
  );

  // Frameworks/Libraries
  if (extensions.has('tsx') || extensions.has('ts')) {
    stack.push('TypeScript');
  }
  if (extensions.has('jsx') || extensions.has('tsx')) {
    stack.push('React');
  }
  if (extensions.has('vue')) {
    stack.push('Vue.js');
  }
  if (extensions.has('svelte')) {
    stack.push('Svelte');
  }

  // Languages
  if (extensions.has('js') || extensions.has('mjs')) {
    stack.push('JavaScript');
  }
  if (extensions.has('py')) {
    stack.push('Python');
  }
  if (extensions.has('ino')) {
    stack.push('Arduino');
  }
  if (extensions.has('java')) {
    stack.push('Java');
  }
  if (extensions.has('cpp') || extensions.has('c') || extensions.has('h')) {
    stack.push('C/C++');
  }
  if (extensions.has('go')) {
    stack.push('Go');
  }
  if (extensions.has('rs')) {
    stack.push('Rust');
  }

  // Styling
  if (extensions.has('css')) {
    stack.push('CSS');
  }
  if (extensions.has('scss') || extensions.has('sass')) {
    stack.push('SCSS');
  }
  if (extensions.has('less')) {
    stack.push('Less');
  }

  // Backend/Config
  if (extensions.has('json')) {
    stack.push('JSON');
  }
  if (extensions.has('yaml') || extensions.has('yml')) {
    stack.push('YAML');
  }
  if (extensions.has('dockerfile')) {
    stack.push('Docker');
  }
  if (extensions.has('sql')) {
    stack.push('SQL');
  }

  // HTML
  if (extensions.has('html') || extensions.has('htm')) {
    stack.push('HTML');
  }

  return stack.length > 0 ? stack : ['Vanilla JavaScript'];
};

// Get setup instructions based on project type
const getSetupInstructions = (project: Project, techStack: string[]): string => {
  const { projectType } = project;
  const mainFile = project.files.find(
    (f) =>
      f.path.includes('index') ||
      f.path.includes('main') ||
      f.path.includes('app') ||
      f.path.includes('server')
  );

  let instructions = '';

  switch (projectType) {
    case 'web-app':
    case 'landing-page':
    case 'component':
      instructions = `## Setup Instructions

### Prerequisites
- Node.js (v18 or higher recommended)
- npm or yarn

### Installation
\`\`\`bash
# Install dependencies
npm install

# Or if no package.json exists, start a local server:
npx serve .
\`\`\`

### Development
\`\`\`bash
# Start development server
npm run dev
# or
npm start
\`\`\`

### Production Build
\`\`\`bash
# Build for production
npm run build
\`\`\`
`;
      break;

    case 'api':
      instructions = `## Setup Instructions

### Prerequisites
${techStack.includes('Python') ? '- Python 3.8+' : '- Node.js v18+ or appropriate runtime'}

### Installation
\`\`\`bash
${techStack.includes('Python') ? '# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt' : '# Install dependencies
npm install'}
\`\`\`

### Running the API
\`\`\`bash
${mainFile ? `# Start the server
python ${mainFile.path}
# or
node ${mainFile.path}` : '# Start the server (check main file)'}
\`\`\`
`;
      break;

    case 'script':
      if (techStack.includes('Python')) {
        instructions = `## Setup Instructions

### Prerequisites
- Python 3.8+

### Running the Script
\`\`\`bash
${mainFile ? `python ${mainFile.path}` : 'python main.py'}
\`\`\`

### Optional: Virtual Environment
\`\`\`bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate
pip install -r requirements.txt
\`\`\`
`;
      } else if (techStack.includes('JavaScript')) {
        instructions = `## Setup Instructions

### Prerequisites
- Node.js v18+

### Running the Script
\`\`\`bash
${mainFile ? `node ${mainFile.path}` : 'node script.js'}
\`\`\`
`;
      } else {
        instructions = `## Setup Instructions

1. Ensure you have the required runtime installed for this project
2. ${mainFile ? `Run the main file: \`${mainFile.path}\`` : 'Check the project files for the entry point'}
`;
      }
      break;

    case 'mobile-app':
      instructions = `## Setup Instructions

### Prerequisites
- Node.js v18+
- React Native CLI or Expo CLI (depending on project setup)
- Android Studio (for Android)
- Xcode (for iOS, macOS only)

### Installation
\`\`\`bash
npm install
\`\`\`

### Running on Device/Simulator
\`\`\`bash
# iOS
npx react-native run-ios

# Android
npx react-native run-android

# Or with Expo:
npx expo start
\`\`\`
`;
      break;

    default:
      instructions = `## Setup Instructions

1. Review the project files to understand the structure
2. Install any required dependencies based on the tech stack
3. Follow language-specific run instructions
`;
  }

  return instructions;
};

// Generate README content
const generateReadme = (project: Project): string => {
  const techStack = getTechStack(project);
  const setupInstructions = getSetupInstructions(project, techStack);

  // Build task checklist
  let taskChecklist = '';
  if (project.plan && project.plan.tasks.length > 0) {
    const tasks = project.plan.tasks;
    const completed = tasks.filter((t) => t.status === 'completed').length;
    const total = tasks.length;

    taskChecklist = `## Task Checklist

*Progress: ${completed}/${total} tasks completed*

| Status | Task | File |
|--------|------|------|
${tasks
  .map(
    (task: PlanTask) =>
      `| ${task.status === 'completed' ? '[x]' : '[ ]'} | ${task.description} | ${
        task.filePath || 'N/A'
      } |`
  )
  .join('\n')}

**Legend:**
- [x] Completed
- [ ] Pending
- [~] In Progress
- [!] Error
`;
  } else {
    taskChecklist = `## Task Checklist

No detailed plan available. Create a plan in the AI Assistant Builder to track progress.
`;
  }

  // File structure
  const fileStructure = project.files
    .map((f) => `- \`${f.path}\``)
    .join('\n');

  return `# ${project.name}

${project.description}

## Project Information

| Property | Value |
|----------|-------|
| **Type** | ${project.projectType} |
| **Created** | ${new Date(project.createdAt).toLocaleString()} |
| **Updated** | ${new Date(project.updatedAt).toLocaleString()} |
| **Files** | ${project.files.length} |

## Tech Stack

${techStack.map((tech) => `- ${tech}`).join('\n')}

${setupInstructions}

${taskChecklist}

## File Structure

${fileStructure}

## Notes

*This project was generated using the Hack the Valley AI Assistant Builder.*
`;
};

// Generate package.json if needed
const generatePackageJson = (project: Project): string | null => {
  const hasJS = project.files.some(
    (f) => f.path.endsWith('.js') || f.path.endsWith('.jsx') || f.path.endsWith('.ts') || f.path.endsWith('.tsx')
  );

  if (!hasJS) return null;

  const hasReact = project.files.some(
    (f) => f.path.endsWith('.jsx') || f.path.endsWith('.tsx')
  );

  const packageJson = {
    name: project.name.toLowerCase().replace(/\s+/g, '-'),
    version: '1.0.0',
    description: project.description,
    main: 'index.js',
    scripts: {
      start: hasReact ? 'react-scripts start' : 'node index.js',
      build: hasReact ? 'react-scripts build' : undefined,
      test: hasReact ? 'react-scripts test' : undefined,
      dev: 'nodemon index.js',
    },
    dependencies: hasReact
      ? {
          react: '^18.2.0',
          'react-dom': '^18.2.0',
          'react-scripts': '5.0.1',
        }
      : {},
    devDependencies: {
      nodemon: '^3.0.1',
    },
    browserslist: hasReact
      ? {
          production: ['>0.2%', 'not dead', 'not op_mini all'],
          development: ['last 1 chrome version', 'last 1 firefox version', 'last 1 safari version'],
        }
      : undefined,
  };

  return JSON.stringify(packageJson, null, 2);
};

// Generate requirements.txt if Python project
const generateRequirementsTxt = (project: Project): string | null => {
  const hasPython = project.files.some((f) => f.path.endsWith('.py'));

  if (!hasPython) return null;

  // Common packages based on imports
  const packages = new Set<string>();

  project.files.forEach((file) => {
    const content = file.content;
    if (content.includes('import flask') || content.includes('from flask')) {
      packages.add('flask>=2.0.0');
    }
    if (content.includes('import fastapi') || content.includes('from fastapi')) {
      packages.add('fastapi>=0.100.0');
      packages.add('uvicorn>=0.23.0');
    }
    if (content.includes('import django') || content.includes('from django')) {
      packages.add('django>=4.0');
    }
    if (content.includes('import requests')) {
      packages.add('requests>=2.28.0');
    }
    if (content.includes('import numpy')) {
      packages.add('numpy>=1.24.0');
    }
    if (content.includes('import pandas')) {
      packages.add('pandas>=2.0.0');
    }
    if (content.includes('import matplotlib')) {
      packages.add('matplotlib>=3.7.0');
    }
  });

  if (packages.size === 0) {
    return '# Add your Python dependencies here\n# flask>=2.0.0\n# requests>=2.28.0\n';
  }

  return Array.from(packages).join('\n') + '\n';
};

// Generate .gitignore
const generateGitignore = (project: Project): string => {
  const techStack = getTechStack(project);

  let gitignore = `# Generated by Hack the Valley AI Assistant Builder

# Environment
.env
.env.local
.env.*.local

# Dependencies
node_modules/
vendor/
__pycache__/
*.py[cod]
*$py.class
.Python

# Build outputs
dist/
build/
*.egg-info/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*
`;

  if (techStack.includes('Python')) {
    gitignore += `
# Python
venv/
env/
.venv/
*.pyc
.pytest_cache/
.mypy_cache/
`;
  }

  if (techStack.includes('React') || techStack.includes('JavaScript')) {
    gitignore += `
# React/JavaScript
.next/
coverage/
.eslintcache
`;
  }

  return gitignore;
};

interface ExportButtonProps {
  variant?: 'primary' | 'secondary';
  size?: 'small' | 'medium';
}

export default function ExportButton({ variant = 'primary', size = 'medium' }: ExportButtonProps) {
  const { project } = useBuilderStore();
  const [isExporting, setIsExporting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExport = useCallback(async () => {
    if (!project) {
      setError('No project to export');
      return;
    }

    if (project.files.length === 0) {
      setError('No files to export');
      return;
    }

    setIsExporting(true);
    setError(null);
    setShowSuccess(false);

    try {
      const zip = new JSZip();

      // Add all project files
      project.files.forEach((file) => {
        // Handle paths with directories
        const pathParts = file.path.split('/');
        if (pathParts.length > 1) {
          // File is in a subdirectory
          const folder = zip.folder(pathParts.slice(0, -1).join('/'));
          folder?.file(pathParts[pathParts.length - 1], file.content);
        } else {
          // File at root
          zip.file(file.path, file.content);
        }
      });

      // Generate README.md
      const readmeContent = generateReadme(project);
      zip.file('README.md', readmeContent);

      // Generate package.json if JS/TS project
      const packageJson = generatePackageJson(project);
      if (packageJson && !project.files.some((f) => f.path === 'package.json')) {
        zip.file('package.json', packageJson);
      }

      // Generate requirements.txt if Python project
      const requirementsTxt = generateRequirementsTxt(project);
      if (requirementsTxt && !project.files.some((f) => f.path === 'requirements.txt')) {
        zip.file('requirements.txt', requirementsTxt);
      }

      // Generate .gitignore
      if (!project.files.some((f) => f.path === '.gitignore')) {
        zip.file('.gitignore', generateGitignore(project));
      }

      // Generate ZIP
      const content = await zip.generateAsync({
        type: 'blob',
        compression: 'DEFLATE',
        compressionOptions: {
          level: 6,
        },
      });

      // Trigger download
      const url = URL.createObjectURL(content);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${project.name.toLowerCase().replace(/\s+/g, '_')}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setShowSuccess(true);
      setTimeout(() => setShowSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Export failed');
    } finally {
      setIsExporting(false);
    }
  }, [project]);

  if (!project) {
    return null;
  }

  const buttonStyles = {
    primary: {
      background: isExporting ? PRIMARY_BG20 : showSuccess ? SUCCESS : PRIMARY,
      color: '#fff',
      border: 'none',
      cursor: isExporting ? 'not-allowed' : 'pointer',
    },
    secondary: {
      background: 'transparent',
      color: PRIMARY,
      border: `1px solid ${PRIMARY}`,
      cursor: isExporting ? 'not-allowed' : 'pointer',
    },
  };

  const sizeStyles = {
    small: {
      padding: `${SPACE.xs}px ${SPACE.sm}px`,
      fontSize: 12,
    },
    medium: {
      padding: `${SPACE.sm}px ${SPACE.md}px`,
      fontSize: 14,
    },
  };

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={handleExport}
        disabled={isExporting || project.files.length === 0}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: SPACE.sm,
          borderRadius: RADIUS.md,
          fontWeight: 500,
          transition: 'all 0.15s ease',
          opacity: isExporting ? 0.7 : project.files.length === 0 ? 0.5 : 1,
          ...buttonStyles[variant],
          ...sizeStyles[size],
        }}
        onMouseEnter={(e) => {
          if (!isExporting && variant === 'secondary') {
            e.currentTarget.style.background = PRIMARY_BG20;
          } else if (!isExporting && !showSuccess && variant === 'primary') {
            e.currentTarget.style.background = PRIMARY_HOVER;
          }
        }}
        onMouseLeave={(e) => {
          if (variant === 'secondary') {
            e.currentTarget.style.background = 'transparent';
          } else if (!showSuccess) {
            e.currentTarget.style.background = isExporting ? PRIMARY_BG20 : PRIMARY;
          }
        }}
        title="Export project as ZIP"
      >
        {isExporting ? (
          <>
            <span
              style={{
                width: size === 'small' ? 12 : 16,
                height: size === 'small' ? 12 : 16,
                border: `2px solid ${variant === 'secondary' ? PRIMARY : '#fff'}40`,
                borderTopColor: variant === 'secondary' ? PRIMARY : '#fff',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite',
                display: 'inline-block',
              }}
            />
            <span>Exporting...</span>
          </>
        ) : showSuccess ? (
          <>
            <span>✓</span>
            <span>Exported!</span>
          </>
        ) : (
          <>
            <span>📦</span>
            <span>Export ZIP</span>
          </>
        )}
      </button>

      {error && (
        <div
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: SPACE.xs,
            padding: `${SPACE.xs}px ${SPACE.sm}px`,
            background: ERROR,
            color: '#fff',
            borderRadius: RADIUS.sm,
            fontSize: 12,
            whiteSpace: 'nowrap',
            zIndex: 10,
          }}
        >
          {error}
        </div>
      )}

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
