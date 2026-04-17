# music-cleanup

Local-first workspace for beets-driven music canonicalization, import cleanup, and custom plugin development.

This repo exists outside the k3s GitOps workflow on purpose. The goal is to iterate quickly on beets config, library cleanup routines, and custom plugins before deciding what should graduate back into `homelab-infra`.

## Scope

- Keep raw upload staging and managed library content on NFS.
- Keep beets SQLite state local to avoid NFS locking issues.
- Develop custom beets plugins in-repo.
- Reuse the same baseline plugin set already assumed by `music-ingest`:
  - `fetchart`
  - `chroma`
  - `lastgenre`
  - `scrub`
  - `discogs`

## Layout

- `src/music_cleanup/beetsplug/`
  Python package code and helpers for this repo.
- `beetsplug/`
  Repo-local beets plugin modules loaded via `pluginpath`.
- `config/config.example.yaml`
  Local config template for this workspace.
- `scripts/setup-venv.sh`
  Creates a local virtualenv and installs beets plus plugin dependencies.
- `scripts/beet.sh`
  Runs `beet` with repo-local config and cache directories pinned into this repo and loads `.env` if present.
- `scripts/mount-nfs.sh`
  Mounts the current library and uploads NFS shares into this repo.
- `scripts/cleanup_bad_genres.py`
  Library cleanup helper adapted from the existing `music-ingest` workflow.
- `state/`
  Local beets state, including SQLite database and caches.
- `mnt/`
  Local mount targets for NFS shares.

## Current Assumptions

These come from the existing `music-ingest` deployment in `homelab-infra`:

- NFS server: `192.168.1.231`
- Upload staging export: `/mnt/user/uploads/music-ingest`
- Library export: `/mnt/user/music`
- Local managed library path inside that export: `managed`

If those change, update `scripts/mount-nfs.sh` and your local beets config together.

## Local Setup

1. Create the virtualenv and install Python dependencies:

```bash
./scripts/setup-venv.sh
```

2. Optionally create a local `.env` from the example if you want API-backed metadata plugins later:

```bash
cp .env.example .env
```

3. Mount the NFS shares into the repo:

```bash
sudo ./scripts/mount-nfs.sh
```

4. Activate the environment and verify beets:

```bash
./scripts/beet.sh version
./scripts/beet.sh help auditfields
./.venv/bin/pytest
```

## Plugin Development

The config uses `pluginpath` to load modules from this repo:

- `audit`

The starter plugin adds an `auditfields` command that reports albums and items missing key metadata. It is meant to be a safe first plugin: read-only, no hidden mutations, and directly useful for cleanup triage.

## Current Status

- Local virtualenv and beets toolchain are installed.
- Repo-local config, cache, and SQLite state are working.
- The starter `auditfields` plugin is wired into beets and tested.
- NFS mounts are intentionally left for host-side setup.

## Notes

- Do not put the beets library database on NFS.
- Expect NFS mounts to require root privileges.
- This repo is intentionally local-first and should remain easy to run without containers or Kubernetes.
