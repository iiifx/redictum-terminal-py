#!/bin/bash
# Generate SHA-256 checksum for the redictum script.
# Run this before publishing a GitHub Release and attach redictum.sha256 as an asset.
set -euo pipefail

SCRIPT="redictum"

if [[ ! -f "$SCRIPT" ]]; then
    echo "Error: $SCRIPT not found in $(pwd)" >&2
    exit 1
fi

sha256sum "$SCRIPT" > "${SCRIPT}.sha256"
echo "Generated ${SCRIPT}.sha256:"
cat "${SCRIPT}.sha256"
