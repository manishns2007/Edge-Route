#!/bin/bash
# ==============================================================================
# EdgeRoute — 1-Click Raspberry Pi (Pi 4 / Pi 5) Deployment Script
# Supports: Raspberry Pi OS 64-bit (Debian Bookworm/Bullseye)
# ==============================================================================
set -e

echo "========================================================="
echo "  ⚡ EdgeRoute — Raspberry Pi Edge AI Deployment Setup"
echo "========================================================="

# 1. Update system and install prerequisites
echo "\n[1/5] Updating system packages..."
sudo apt-get update && sudo apt-get install -y python3-pip python3-venv python3-full curl git

# 2. Install Ollama for ARM64
echo "\n[2/5] Installing Ollama ARM64..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
else
    echo "Ollama is already installed."
fi

# Ensure Ollama service is active
sudo systemctl enable --now ollama

# 3. Pull Edge-optimized models
echo "\n[3/5] Pulling Edge-optimized SLMs for Raspberry Pi..."
echo "Pulling Qwen2.5-0.5B (Fastest routing on Pi CPU)..."
ollama pull qwen2.5:0.5b

echo "Pulling Llama 3.2 1B (High-quality edge generation)..."
ollama pull llama3.2:1b

# 4. Set up Python environment
echo "\n[4/5] Setting up Python virtual environment..."
cd "$(dirname "$0")"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Create .env for Raspberry Pi
if [ ! -f .env ]; then
    cat <<EOT >> .env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:0.5b
OLLAMA_TIMEOUT=30
MOCK_CLOUD=false
CLOUD_API_KEY=
API_HOST=0.0.0.0
API_PORT=8000
EOT
    echo ".env created with Pi defaults."
fi

# 5. Create Systemd Service for Auto-start on Boot
echo "\n[5/5] Creating systemd service for boot startup..."
USER_NAME=$(whoami)
WORK_DIR=$(pwd)

sudo tee /etc/systemd/system/edgeroute.service > /dev/null <<EOT
[Unit]
Description=EdgeRoute AI Inference Router
After=network.target ollama.service
Wants=ollama.service

[Service]
Type=simple
User=${USER_NAME}
WorkingDirectory=${WORK_DIR}
ExecStart=${WORK_DIR}/venv/bin/python -m streamlit run app/ui.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOT

sudo systemctl daemon-reload
sudo systemctl enable edgeroute.service
sudo systemctl start edgeroute.service

echo "\n========================================================="
echo "  ✅ EdgeRoute is now LIVE on your Raspberry Pi!"
echo "  Web UI running at: http://$(hostname -I | awk '{print $1}'):8501"
echo "  API running at:    http://$(hostname -I | awk '{print $1}'):8000"
echo "  Service control:   sudo systemctl status edgeroute"
echo "========================================================="
