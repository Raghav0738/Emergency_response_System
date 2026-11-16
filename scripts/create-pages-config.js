const fs = require('node:fs');
const path = require('node:path');

function createProductionConfig(source, apiUrl) {
  if (typeof apiUrl !== 'string' || !apiUrl || apiUrl.trim() !== apiUrl) {
    throw new Error('API URL is required');
  }

  let parsed;
  try {
    parsed = new URL(apiUrl);
  } catch {
    throw new Error('API URL must be a valid HTTPS URL');
  }
  if (parsed.protocol !== 'https:' || parsed.username || parsed.password || parsed.search || parsed.hash) {
    throw new Error('API URL must be HTTPS and cannot include credentials, a query, or a fragment');
  }

  const marker = "API_BASE_URL: '',";
  if (!source.includes(marker)) {
    throw new Error('Could not locate API_BASE_URL in frontend/config.js');
  }
  return source.replace(
    marker,
    `API_BASE_URL: ${JSON.stringify(apiUrl.replace(/\/+$/, ''))},`
  );
}

if (require.main === module) {
  const root = path.resolve(__dirname, '..');
  const source = fs.readFileSync(path.join(root, 'frontend', 'config.js'), 'utf8');
  const output = createProductionConfig(source, process.env.API_BASE_URL);
  fs.writeFileSync(path.join(root, 'frontend', 'config.production.js'), output);
}

module.exports = { createProductionConfig };
