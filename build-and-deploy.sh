#!/bin/bash

# Build and Deploy Script for Portainer
# This script builds the Docker image and prepares it for Portainer deployment

set -e

echo "🏗️  Building maintenance dashboard Docker image..."

# Build the Docker image
docker build -t maintenance-dashboard:latest .

echo "✅ Image built successfully!"

echo "📋 Next steps for Portainer deployment:"
echo ""
echo "Option A - Use Local Image (if Portainer is on same machine):"
echo "1. Copy the content of 'portainer-stack-with-image.yml'"
echo "2. Go to Portainer -> Stacks -> Add Stack"
echo "3. Paste the content and deploy"
echo ""
echo "Option B - Push to Docker Hub (for remote deployment):"
echo "1. Tag image: docker tag maintenance-dashboard:latest yourusername/maintenance-dashboard:latest"
echo "2. Push image: docker push yourusername/maintenance-dashboard:latest"
echo "3. Update 'portainer-stack-with-image.yml' to use yourusername/maintenance-dashboard:latest"
echo "4. Deploy in Portainer"
echo ""
echo "🚀 Your application will be available at http://localhost:8000 after deployment"