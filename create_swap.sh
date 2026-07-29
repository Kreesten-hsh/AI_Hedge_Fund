#!/bin/bash
# Script to create an 8GB swap file to prevent OOM errors during PPO training.
# Run this script with: sudo bash create_swap.sh

echo "Creating 8GB swap file..."
fallocate -l 8G /swapfile

echo "Setting permissions..."
chmod 600 /swapfile

echo "Setting up swap area..."
mkswap /swapfile

echo "Enabling swap..."
swapon /swapfile

echo "Making swap permanent in /etc/fstab..."
if ! grep -q "/swapfile" /etc/fstab; then
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "Swap added to /etc/fstab."
else
    echo "Swap already in /etc/fstab."
fi

echo "Swap space created successfully!"
free -h
