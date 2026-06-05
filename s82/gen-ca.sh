#!/bin/bash
# gen-ca.sh — Genera CA + certificados para MITM
set -e
DIR=/home/vuos/code/p3/s82/certs
mkdir -p "$DIR"

# 1. CA
if [ ! -f "$DIR/ca.key" ]; then
    echo "=== Generando CA ==="
    openssl genrsa -out "$DIR/ca.key" 2048
    openssl req -x509 -new -nodes -key "$DIR/ca.key" -sha256 -days 3650 \
        -out "$DIR/ca.crt" -subj "/CN=SniffMITM CA/O=Sniff/OU=Monitoring"
fi

# 2. Server key (compartido para todos los certs dinámicos)
if [ ! -f "$DIR/server.key" ]; then
    echo "=== Generando server key ==="
    openssl genrsa -out "$DIR/server.key" 2048
fi

# 3. Certificado inicial (para sni_callback)
if [ ! -f "$DIR/initial.crt" ]; then
    echo "=== Generando initial cert ==="
    openssl req -new -key "$DIR/server.key" -out /tmp/initial.csr \
        -subj "/CN=mitm-initial" 2>/dev/null
    openssl x509 -req -in /tmp/initial.csr \
        -CA "$DIR/ca.crt" -CAkey "$DIR/ca.key" \
        -CAcreateserial -out "$DIR/initial.crt" \
        -days 365 -sha256 2>/dev/null
    rm -f /tmp/initial.csr
fi

echo ""
echo "=== Certificados listos ==="
ls -la "$DIR/" | grep -v cache
echo ""
echo "Instalar CA:  sudo python3 mitm.py --install-ca"
echo "Iptables:     sudo python3 mitm.py --iptables-add"
echo "Iniciar:      python3 mitm.py"
