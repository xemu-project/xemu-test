#!/bin/bash
set -ex

if [[ ! -d xemutest ]]; then
    echo "Error: Run from repository root directory" >&2
    exit 1
fi

DATA_DIR="xemutest/data"
mkdir -p "$DATA_DIR/TestXBE"

# Build test-xbe if changed or missing
SRC_HASH=$(find test-xbe -type f -exec sha256sum {} + 2>/dev/null | sort | sha256sum | cut -d' ' -f1)
HASH_FILE="$DATA_DIR/TestXBE/.source_hash"
ISO_FILE="$DATA_DIR/TestXBE/tester.iso"

if [[ -f "$ISO_FILE" && -f "$HASH_FILE" && "$(<"$HASH_FILE")" == "$SRC_HASH" ]]; then
    echo "[Up-to-date] $ISO_FILE"
else
    echo "[Build] test-xbe tester.iso..."
    target=test-xbe-data
    image=xemu-test-data-tmp-img
    docker build --target "$target" -t "$image" .
    container=$(docker create "$image" "")
    docker cp "$container:/data/TestXBE/tester.iso" "$DATA_DIR/TestXBE/tester.iso"
    docker rm "$container"
    docker rmi -f "$image" > /dev/null 2>&1 || true
    echo "$SRC_HASH" > "$HASH_FILE"
fi


# Fetch external test requirements
python3 scripts/fetch_test_requirements.py "$DATA_DIR"
