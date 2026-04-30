#!/bin/bash
# Google Wallet Setup Helper
# This script helps you set up Google Wallet pass generation

set -e

echo "======================================"
echo "Google Wallet Setup for HackVerify"
echo "======================================"
echo ""

DATA_DIR="${1:-./data/wallet}"
mkdir -p "$DATA_DIR"

echo "Step 1: Enable Google Wallet API"
echo "==============================="
echo "1. Go to https://console.cloud.google.com/"
echo "2. Create a new project (or select existing)"
echo "3. Navigate to 'APIs & Services' → 'Library'"
echo "4. Search for 'Google Wallet API'"
echo "5. Click 'Enable'"
echo ""

echo "Step 2: Create Service Account"
echo "==============================="
echo "1. Go to 'IAM & Admin' → 'Service Accounts'"
echo "2. Click 'Create Service Account'"
echo "3. Name: 'hackverify-wallet'"
echo "4. Description: 'HackVerify Wallet Integration'"
echo "5. Click 'Create and Continue'"
echo "6. For roles, select 'Owner' (or at minimum 'Service Account User')"
echo "7. Click 'Continue' then 'Done'"
echo ""

echo "Step 3: Create and Download Service Account Key"
echo "================================================="
echo "1. Click on your newly created service account"
echo "2. Go to the 'Keys' tab"
echo "3. Click 'Add Key' → 'Create New Key'"
echo "4. Select 'JSON' format"
echo "5. Click 'Create' - this downloads the key file"
echo ""

read -p "Enter path to downloaded JSON key file: " KEY_FILE

if [ ! -f "$KEY_FILE" ]; then
    echo "❌ Key file not found at: $KEY_FILE"
    exit 1
fi

# Copy and rename key file
GOOGLE_KEY_PATH="$DATA_DIR/google_wallet_service_account.json"
cp "$KEY_FILE" "$GOOGLE_KEY_PATH"
echo "✓ Copied key file to: $GOOGLE_KEY_PATH"

# Extract issuer ID
echo ""
echo "Step 4: Get Issuer ID"
echo "======================"
echo "The Issuer ID is your Google Cloud Project Number:"
echo "1. Go to https://console.cloud.google.com/"
echo "2. Look at the project selector dropdown - the number is there"
echo "3. Or go to 'IAM & Admin' → 'Settings' - Project Number is listed"
echo ""

read -p "Enter your Google Cloud Project Number (Issuer ID): " ISSUER_ID

echo ""
echo "Step 5: Share Class ID with Service Account"
echo "==========================================="
echo "This is required for Google Wallet to work:"
echo "1. The service account email is in the JSON key file"
echo "2. Go to https://pay.google.com/gp/m/issuer/"
echo "3. Sign in with the same Google account"
echo "4. Click your issuer"
echo "5. Go to 'Users' tab"
echo "6. Add the service account email with 'Developer' role"
echo ""

echo "Step 6: Update Configuration"
echo "============================="
echo "Add these to your .env file:"
echo ""
echo "# Google Wallet Configuration"
echo "HACKVERIFY_GOOGLE_WALLET_CREDENTIALS_PATH=$GOOGLE_KEY_PATH"
echo "HACKVERIFY_GOOGLE_WALLET_ISSUER_ID=$ISSUER_ID"
echo ""

# Save configuration
cat > "$DATA_DIR/google_wallet_config.txt" << EOF
Google Wallet Configuration
===========================
Issuer ID: $ISSUER_ID
Service Account Key: $GOOGLE_KEY_PATH

Add to your .env file:
HACKVERIFY_GOOGLE_WALLET_CREDENTIALS_PATH=$GOOGLE_KEY_PATH
HACKVERIFY_GOOGLE_WALLET_ISSUER_ID=$ISSUER_ID

Service Account Email (add to Google Pay Console):
EOF

# Extract service account email from JSON
if command -v python3 &> /dev/null; then
    SERVICE_ACCOUNT_EMAIL=$(python3 -c "import json; print(json.load(open('$GOOGLE_KEY_PATH'))['client_email'])")
    echo "Service Account Email: $SERVICE_ACCOUNT_EMAIL" >> "$DATA_DIR/google_wallet_config.txt"
    echo "$SERVICE_ACCOUNT_EMAIL" >> "$DATA_DIR/google_wallet_config.txt"
fi

echo "✓ Configuration saved to: $DATA_DIR/google_wallet_config.txt"
echo ""
echo "======================================"
echo "Google Wallet Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Update your .env file with the values above"
echo "2. Go to https://pay.google.com/gp/m/issuer/ and add the service account"
echo "3. Restart your HackVerify server"
echo "4. Test by registering for a hackathon"
echo ""
echo "Important:"
echo "- Keep the JSON key file secure"
echo "- The service account has access to your Google Wallet - protect it"
echo "- Never commit the JSON key file to version control"
