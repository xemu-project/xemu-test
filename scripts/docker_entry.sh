#!/bin/bash
exec 2>&1

XVFB_WHD=640x480x24
DISPLAY=:99

if [ $# -eq 0 ]; then
	echo "No launch command provided"
	exit 1
fi

set -e
if [[ -e /work/inputs/xemu.deb ]]; then
  echo "[*] Installing xemu package"
  apt-get -qy install /work/inputs/xemu.deb
else
    appimage_file="$(find /work/inputs -name "*.AppImage" -print0 \
        | sort -zV \
        | tail -zn 1 \
        | tr -d '\0')"
    readonly appimage_file

    if [[ "${appimage_file:+x}" != "x" ]]; then
      echo "No .deb or .AppImage found in /work/inputs."
      exit 1
    fi

    echo "[*] Using xemu from ${appimage_file}"

    chmod +x "${appimage_file}"
    "${appimage_file}" --appimage-extract > /dev/null 2>&1
    export PATH="$PWD/squashfs-root/usr/bin:${PATH}"
fi

echo "exec i3" >> ~/.xinitrc
chmod +x ~/.xinitrc

mkdir -p ~/.config/i3
cat <<EOF >>~/.config/i3/config
border none
bar {
}
EOF

echo "[*] Starting Xvfb"
xinit -- /usr/bin/Xvfb $DISPLAY -ac -screen 0 "$XVFB_WHD" -nolisten tcp +extension GLX +render -noreset 1>/dev/null 2>&1 &
Xvfb_pid="$!"
echo "[~] Waiting for Xvfb (PID: $Xvfb_pid) to be ready..."
set +e
while ! xdpyinfo -display "${DISPLAY}" 1>/dev/null 2>&1; do
		sleep 0.1
done
set -e
export DISPLAY

echo "[*] Starting VNC server"
x11vnc -forever 1>/dev/null 2>&1 &

echo "[*] Running target command"
exec "$@"
