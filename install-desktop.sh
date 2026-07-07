#!/bin/bash
# One-time setup: creates a desktop launcher for Kal Quarry Billing
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cat > "$HOME/Desktop/Kal Quarry Billing.desktop" << EOF
[Desktop Entry]
Name=Kal Quarry Billing
Comment=Stone Quarry Billing Software
Exec=$SCRIPT_DIR/run.sh
Path=$SCRIPT_DIR
Terminal=false
Type=Application
Categories=Office;Finance;
EOF
chmod +x "$HOME/Desktop/Kal Quarry Billing.desktop"
echo "✅ Done! Double-click 'Kal Quarry Billing' on your Desktop to launch."
