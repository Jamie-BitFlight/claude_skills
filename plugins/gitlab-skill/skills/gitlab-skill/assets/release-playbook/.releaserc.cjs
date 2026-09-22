const defaultBranch = process.env.CI_DEFAULT_BRANCH;
const tagPrefix = process.env.RELEASE_TAG_PREFIX;

if (!defaultBranch) {
  throw new Error('CI_DEFAULT_BRANCH is required');
}
if (!tagPrefix) {
  throw new Error('RELEASE_TAG_PREFIX is required from the resolved base tag contract');
}

module.exports = {
  branches: [defaultBranch],
  tagFormat: `${tagPrefix}\${version}`,
  plugins: ['@semantic-release/commit-analyzer'],
};
