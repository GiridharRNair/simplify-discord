# Script to bulk add GitHub secrets from a .env file. 

while IFS='=' read -r key value || [ -n "$key" ]; do
  # Skip comments and empty lines
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  # Strip quotes if present
  value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//')

  echo "Setting secret: $key"
  gh secret set "$key" --body "$value" --repo "GiridharRNair/simplify-discord"
done < .env
