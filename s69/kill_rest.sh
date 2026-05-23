#!/bin/bash
# Mata procesos no esenciales que requieren sudo
# Ejecutar: sudo bash kill_rest.sh

echo "=== Matando procesos no esenciales ==="

# Matar todo el árbol de Docker rootless primero
echo "Docker rootless..."
for pid in $(pgrep -f dockerd-rootless 2>/dev/null); do
  /bin/kill -9 "$pid" 2>/dev/null
done
for pid in $(pgrep -f rootlesskit 2>/dev/null); do
  /bin/kill -9 "$pid" 2>/dev/null
done
for pid in $(pgrep -x dockerd 2>/dev/null); do
  /bin/kill -9 "$pid" 2>/dev/null
done
for pid in $(pgrep -f "containerd.*config.*user" 2>/dev/null); do
  /bin/kill -9 "$pid" 2>/dev/null
done
# Matar threads si quedan vivos
for pid in $(pgrep -f dockerd 2>/dev/null); do
  for tid in $(ls /proc/$pid/task/ 2>/dev/null); do
    /bin/kill -9 "$tid" 2>/dev/null
  done
done
sleep 1

# MySQLs y Redis
/bin/kill -9 50503 63722 50831 2>/dev/null

# Cube
for pid in $(pgrep -f cube-network-agent 2>/dev/null); do
  /bin/kill -9 "$pid" 2>/dev/null
done

# Docker del sistema (root)
for pid in $(pgrep -x dockerd 2>/dev/null; pgrep -f "dockerd -H" 2>/dev/null); do
  /bin/kill -9 "$pid" 2>/dev/null
done

# Deshabilitar servicios systemd
echo "Deshabilitando servicios..."
for svc in mysql docker redis; do
  systemctl is-active --quiet "$svc" 2>/dev/null && systemctl stop "$svc" 2>/dev/null
  systemctl is-enabled --quiet "$svc" 2>/dev/null && systemctl disable "$svc" 2>/dev/null
done

# También deshabilitar el servicio de usuario docker
if [ -f /home/vuos/.config/systemd/user/docker.service ]; then
  mv /home/vuos/.config/systemd/user/docker.service /home/vuos/.config/systemd/user/docker.service.bak
  echo "  docker user service masked"
fi

sleep 2

echo ""
echo "=== Remanentes ==="
for name in dockerd mysqld redis-server cube-network-agent; do
  pids=$(pgrep -x "$name" 2>/dev/null || pgrep -f "$name" 2>/dev/null || true)
  if [ -n "$pids" ]; then
    echo "  VIVE: $name -> PIDs $pids"
  else
    echo "  MUERTO: $name"
  fi
done
echo "=== Listo ==="
