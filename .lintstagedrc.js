const path = require('path');

module.exports = {
  'frontend/src/**/*.{ts,tsx}': (filenames) => {
    // Pass files to frontend's lint command using bash
    const relativeFiles = filenames
      .map(f => path.relative(path.join(process.cwd(), 'frontend'), f).replace(/\\/g, '/'))
      .join(' ');
    return `bash -c "cd frontend && npm run lint -- ${relativeFiles}"`;
  },
  'backend/**/*.py': [
    () => 'bash -c "cd backend && ruff check --fix ."',
    () => 'bash -c "cd backend && ruff format ."',
  ],
};
