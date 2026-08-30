# Bulk-adds GitHub Actions secrets from a .env file, one `gh secret set` call per line.
#
# Requirements:
#   - GitHub CLI installed and authenticated: `gh auth login`
#   - Run this from inside your cloned fork, so `gh` targets the repo your
#     `origin` remote points to (no --repo flag, so it can't accidentally
#     target someone else's repo).
#
# Usage:
#   cp example.env .env   # then fill in your webhook URLs
#   ./github-secrets-bulk-add.sh

while IFS='=' read -r key value || [ -n "$key" ]; do
  # Skip comments and empty lines
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  # Strip quotes if present
  value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//')

  echo "Setting secret: $key"
  gh secret set "$key" --body "$value"
done < .env
