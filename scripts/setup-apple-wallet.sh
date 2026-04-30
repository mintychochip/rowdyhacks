#!/bin/bash
# Apple Wallet Setup Helper
# This script helps you set up Apple Wallet pass generation

set -e

echo "======================================"
echo "Apple Wallet Setup for HackVerify"
echo "======================================"
echo ""

# Check if running on macOS (required for some steps)
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "⚠️  Warning: Some Apple Developer tools work best on macOS"
    echo "You can still run this on Linux, but certificate export may differ"
    echo ""
fi

DATA_DIR="${1:-./data/wallet}"
mkdir -p "$DATA_DIR"

echo "Step 1: Apple Developer Account Setup"
echo "====================================="
echo "1. Go to https://developer.apple.com/account/"
echo "2. Sign in with your Apple ID"
echo "3. Navigate to 'Certificates, Identifiers & Profiles'"
echo ""
echo "Step 2: Create Pass Type ID"
echo "==========================="
echo "1. Go to 'Identifiers' → 'Pass Type IDs'"
echo "2. Click '+' to add new"
echo "3. Enter Description: 'HackVerify Check-in Pass'"
echo "4. Enter Identifier: pass.com.yourdomain.hackverify"
echo "   (replace 'yourdomain' with your actual domain)"
echo "5. Click 'Continue' then 'Register'"
echo ""
read -p "Enter your Pass Type ID (e.g., pass.com.yourdomain.hackverify): " PASS_TYPE_ID
read -p "Enter your Apple Team ID (found in Apple Developer Account → Membership): " TEAM_ID

echo ""
echo "Step 3: Generate Certificate Signing Request (CSR)"
echo "======================================================"
echo "This creates the private key and CSR needed for Apple"
echo ""

KEY_PATH="$DATA_DIR/apple_pass.key"
CSR_PATH="$DATA_DIR/apple_pass.csr"
CERT_P12_PATH="$DATA_DIR/apple_pass.p12"

# Generate private key
openssl genrsa -out "$KEY_PATH" 2048
echo "✓ Generated private key: $KEY_PATH"

# Generate CSR
openssl req -new -key "$KEY_PATH" -out "$CSR_PATH" \
    -subj "/CN=HackVerify Pass/C=US"
echo "✓ Generated CSR: $CSR_PATH"

echo ""
echo "Step 4: Upload CSR to Apple Developer Portal"
echo "============================================"
echo "1. Go back to https://developer.apple.com/account/"
echo "2. Navigate to 'Certificates' → 'All'"
echo "3. Click '+' to add new certificate"
echo "4. Select 'Pass Type ID Certificate' under 'Services'"
echo "5. Select your Pass Type ID from the dropdown"
echo "6. Upload the CSR file: $CSR_PATH"
echo "7. Download the generated certificate (.cer file)"
echo ""

read -p "Enter path to downloaded Apple certificate (.cer): " APPLE_CERT_PATH

if [ ! -f "$APPLE_CERT_PATH" ]; then
    echo "❌ Certificate not found at: $APPLE_CERT_PATH"
    exit 1
fi

echo ""
echo "Step 5: Convert Certificate to P12"
echo "===================================="

# Convert .cer to .pem
CERT_PEM_PATH="$DATA_DIR/apple_cert.pem"
openssl x509 -inform der -in "$APPLE_CERT_PATH" -out "$CERT_PEM_PATH"
echo "✓ Converted certificate to PEM"

# Create P12 file
read -s -p "Enter password for P12 file (remember this!): " P12_PASSWORD
echo ""

openssl pkcs12 -export \
    -in "$CERT_PEM_PATH" \
    -inkey "$KEY_PATH" \
    -out "$CERT_P12_PATH" \
    -name "HackVerify Pass" \
    -passout "pass:$P12_PASSWORD"

echo "✓ Created P12 certificate: $CERT_P12_PATH"

echo ""
echo "Step 6: Update Configuration"
echo "==========================="
echo "Add these to your .env file:"
echo ""
echo "# Apple Wallet Configuration"
echo "HACKVERIFY_APPLE_PASS_CERT_PATH=$CERT_P12_PATH"
echo "HACKVERIFY_APPLE_PASS_CERT_PASSWORD=$P12_PASSWORD"
echo "HACKVERIFY_APPLE_PASS_TYPE_IDENTIFIER=$PASS_TYPE_ID"
echo "HACKVERIFY_APPLE_TEAM_IDENTIFIER=$TEAM_ID"
echo ""

# Save configuration
cat > "$DATA_DIR/apple_wallet_config.txt" << EOF
Apple Wallet Configuration
==========================
Pass Type ID: $PASS_TYPE_ID
Team ID: $TEAM_ID
Certificate Path: $CERT_P12_PATH
Certificate Password: [hidden]

Add to your .env file:
HACKVERIFY_APPLE_PASS_CERT_PATH=$CERT_P12_PATH
HACKVERIFY_APPLE_PASS_CERT_PASSWORD=$P12_PASSWORD
HACKVERIFY_APPLE_PASS_TYPE_IDENTIFIER=$PASS_TYPE_ID
HACKVERIFY_APPLE_TEAM_IDENTIFIER=$TEAM_ID
EOF

echo "✓ Configuration saved to: $DATA_DIR/apple_wallet_config.txt"
echo ""
echo "======================================"
echo "Apple Wallet Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Update your .env file with the values above"
echo "2. Restart your HackVerify server"
echo "3. Test by registering for a hackathon and downloading a pass"
echo ""
echo "Important:"
echo "- Keep the .p12 file and password secure"
echo "- The certificate expires yearly (Apple requires renewal)"
echo "- In production, use a more secure password storage method"
