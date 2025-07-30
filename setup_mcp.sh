#!/bin/bash

echo "Setting up MCP (Model Context Protocol) for Onboarding Manager"
echo "=============================================================="

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed. Please install Node.js and npm first."
    exit 1
fi

# Install MCP SQLite server
echo "Installing MCP SQLite server..."
npm install

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create database directory if needed
mkdir -p ./data

echo ""
echo "Setup complete! To run the application with MCP:"
echo "1. The MCP SQLite server will be automatically started when needed"
echo "2. Run your Python application: python main.py <org_name> <project_slug>"
echo ""
echo "Note: The MCP server will be spawned as a subprocess by the client."