#!/usr/bin/env bash
#
# change-passphrase.sh - Change Pulumi stack passphrase
#

set -e

cd "$(dirname "$0")/../infrastructure"

OLD_PASS="${1:-}"
NEW_PASS="${2:-123}"

echo "Changing Pulumi passphrase..."
echo "This will update both dev and main stacks"
echo ""

for stack in dev main; do
    echo "Processing $stack stack..."
    
    # Use expect to handle interactive prompts
    expect << EOF
set timeout -1
spawn env PULUMI_CONFIG_PASSPHRASE="$OLD_PASS" pulumi stack change-secrets-provider "passphrase" --stack $stack
expect "Enter your new passphrase to protect config/secrets:"
send "$NEW_PASS\r"
expect "Re-enter your new passphrase to confirm:"
send "$NEW_PASS\r"
expect eof
EOF
    
    echo "✅ $stack stack passphrase changed"
done

echo ""
echo "✅ All stacks updated!"
echo "Don't forget to update PULUMI_CONFIG_PASSPHRASE=123 in your .env file"
