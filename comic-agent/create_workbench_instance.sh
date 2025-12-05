#!/bin/bash

# Script to create a Vertex AI Workbench instance with JupyterLab
# Prerequisites: gcloud CLI installed and authenticated, project set

# Set variables (customize as needed)
PROJECT_ID="your-gcp-project-id"  # Replace with your GCP project ID
INSTANCE_NAME="comic-cataloger-workbench"
ZONE="us-central1-a"  # Choose appropriate zone
MACHINE_TYPE="n1-standard-4"  # 4 vCPUs, 15 GB RAM; adjust as needed
DISK_SIZE="100GB"  # Adjust disk size
IMAGE_FAMILY="common-cpu-notebooks"  # For CPU-based; use 'common-gpu-notebooks' for GPU
IMAGE_NAME="debian-10"  # Latest Debian-based image

# Create the Vertex AI Workbench instance
gcloud notebooks instances create $INSTANCE_NAME \
  --project=$PROJECT_ID \
  --location=$ZONE \
  --machine-type=$MACHINE_TYPE \
  --disk-size=$DISK_SIZE \
  --image-family=$IMAGE_FAMILY \
  --image-name=$IMAGE_NAME \
  --metadata=idle-timeout-seconds=3600 \
  --metadata=shutdown-script="sudo poweroff" \
  --no-public-ip  # For security; use --public-ip if needed

echo "Vertex AI Workbench instance '$INSTANCE_NAME' created successfully."
echo "Access it via: https://console.cloud.google.com/vertex-ai/workbench/instances?project=$PROJECT_ID"