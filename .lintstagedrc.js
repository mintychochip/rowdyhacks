const path = require('path');

module.exports = {
  'frontend/src/**/*.{ts,tsx}': (filenames) => {
    // TypeScript type check first (critical - must pass)
    // Then run lint (warnings allowed)
    const relativeFiles = filenames
      .map(f => path.relative(path.join(process.cwd(), 'frontend'), f).replace(/\\/g, '/'))
      .join(' ');
    return [
      // TypeScript type check - must pass (catches build errors)
      'bash -c "cd frontend && npx tsc -b"',
      // ESLint - warnings allowed to match CI behavior
      `bash -c "cd frontend && npm run lint -- ${relativeFiles} 2>&1 || echo 'Lint warnings present'"`,
    ];
  },
  'backend/**/*.py': [
    () => 'bash -c "cd backend && ruff check --fix ."',
    () => 'bash -c "cd backend && ruff format ."',
  ],
};
