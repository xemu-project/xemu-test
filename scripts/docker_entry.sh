#!/bin/bash
exec 2>&1

XVFB_WHD=640x480x24
DISPLAY=:99

if [ $# -eq 0 ]; then
	echo "No launch command provided"
	exit 1
fi

set -e
echo "[*] Installing xemu package"
apt-get -qy install /work/inputs/xemu.deb

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
