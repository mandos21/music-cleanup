#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
nfs_server="${NFS_SERVER:-192.168.1.231}"
uploads_export="${UPLOADS_EXPORT:-/mnt/user/uploads/music-ingest}"
library_export="${LIBRARY_EXPORT:-/mnt/user/music}"

uploads_mount="${repo_root}/mnt/uploads"
library_mount="${repo_root}/mnt/library"

mkdir -p "${uploads_mount}" "${library_mount}"

mountpoint -q "${uploads_mount}" || mount -t nfs -o nfsvers=4.2 "${nfs_server}:${uploads_export}" "${uploads_mount}"
mountpoint -q "${library_mount}" || mount -t nfs -o nfsvers=4.2 "${nfs_server}:${library_export}" "${library_mount}"

echo "Mounted uploads at ${uploads_mount}"
echo "Mounted library at ${library_mount}"
