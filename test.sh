#!/bin/bash
set -e
set -o pipefail

SUPPORT_DIR=private
SUPPORT_ARCHIVE=${SUPPORT_DIR}.zip
SUPPORT_ARCHIVE_ENC=${SUPPORT_ARCHIVE}.enc
SUPPORT_URL=${SUPPORT_URL:-http://localhost:8080/${SUPPORT_ARCHIVE_ENC}}

if [[ ! -d ${SUPPORT_DIR} ]]; then
    if [[ ! -e ${SUPPORT_ARCHIVE} ]]; then
        if [[ ! -e ${SUPPORT_ARCHIVE_ENC} ]]; then
            echo "[*] Downloading ${SUPPORT_ARCHIVE_ENC}"
            wget -O ${SUPPORT_ARCHIVE_ENC} ${SUPPORT_URL} 1>/dev/null 2>&1
        fi
        echo "[*] Decrypting ${SUPPORT_ARCHIVE}"
        gpg --quiet --batch --yes --decrypt --passphrase="$SUPPORT_PASSPHRASE" \
            --output ./${SUPPORT_ARCHIVE} ${SUPPORT_ARCHIVE_ENC}
    fi

    unzip ${SUPPORT_ARCHIVE}
fi

echo "[*] Building test executable"
docker run --rm -v $PWD/test-xbe:/work -w /work ghcr.io/xboxdev/nxdk make

echo "[*] Pulling test container"
docker pull ghcr.io/mborgerson/xemu-test:master

echo "[*] Running tests"
rm -rf results
mkdir results
docker run --rm -p 5900:5900 -v $PWD:/work -w /work \
           ghcr.io/mborgerson/xemu-test:master \
           python3 test_main.py 2>&1 | tee results/log.txt
