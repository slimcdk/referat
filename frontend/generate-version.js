const fs = require('fs');
const { execSync } = require('child_process');

try {
  console.log('Generating dynamic public/version.json from Git history...');
  
  // Try to get git info
  let commit = 'unknown';
  try {
    commit = execSync('git rev-parse --short HEAD').toString().trim();
  } catch (err) {
    console.warn('Could not read git commit hash.');
  }

  let version = 'v2026.07.22'; // Default fallback
  try {
    version = execSync('git describe --tags --always').toString().trim();
  } catch (e) {
    if (commit !== 'unknown') {
      version = commit;
    }
  }
  
  const versionInfo = {
    version: version,
    commit: commit,
    githubUrl: 'https://github.com/christian/referat' // Default fallback url
  };

  try {
    const remoteUrl = execSync('git config --get remote.origin.url').toString().trim();
    if (remoteUrl) {
      // Convert standard SSH or HTTPS git url to a clean HTTP landing page URL
      let cleanUrl = remoteUrl
        .replace('git@github.com:', 'https://github.com/')
        .replace('https://github.com/', 'https://github.com/')
        .replace('.git', '');
      versionInfo.githubUrl = cleanUrl;
    }
  } catch (remoteErr) {
    console.warn('Could not read git remote url, using default.');
  }

  // Write to public/version.json
  fs.writeFileSync('public/version.json', JSON.stringify(versionInfo, null, 2));
  console.log('Successfully generated public/version.json:', versionInfo);
} catch (err) {
  console.error('Failed to generate version.json, creating fallback.', err);
  fs.writeFileSync('public/version.json', JSON.stringify({
    version: 'v2026.07.22',
    commit: 'unknown',
    githubUrl: 'https://github.com/christian/referat'
  }, null, 2));
}
