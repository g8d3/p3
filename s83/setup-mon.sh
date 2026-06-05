#!/bin/bash
# setup-mon.sh — Genera certificados y prepara el monitor MITM
# Luego: inicia el proxy y relanza crush con las variables correctas

set -e
DIR=/home/vuos/code/p3/s82
CERTS=$DIR/certs
mkdir -p "$CERTS"

# 1. Generar CA (Autoridad Certificante)
if [ ! -f "$CERTS/ca.key" ]; then
    echo "=== Generando CA ==="
    openssl genrsa -out "$CERTS/ca.key" 2048
    openssl req -x509 -new -nodes -key "$CERTS/ca.key" \
        -sha256 -days 3650 \
        -out "$CERTS/ca.crt" \
        -subj "/CN=Crush MITM CA/O=Crush/OU=Monitoring"
fi

# 2. Generar certificado para 127.0.0.1
if [ ! -f "$CERTS/server.key" ]; then
    echo "=== Generando certificado del servidor ==="
    openssl genrsa -out "$CERTS/server.key" 2048
    
    # Config para SAN
    cat > "$CERTS/server.cnf" << EOF
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no
[req_distinguished_name]
CN = 127.0.0.1
[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
IP.1 = 127.0.0.1
DNS.1 = localhost
EOF
    
    openssl req -new -key "$CERTS/server.key" \
        -out "$CERTS/server.csr" \
        -config "$CERTS/server.cnf"
    
    openssl x509 -req -in "$CERTS/server.csr" \
        -CA "$CERTS/ca.crt" -CAkey "$CERTS/ca.key" \
        -CAcreateserial -out "$CERTS/server.crt" \
        -days 365 -sha256 \
        -extfile "$CERTS/server.cnf" -extensions v3_req
    
    rm -f "$CERTS/server.csr" "$CERTS/server.cnf"
fi

# 3. Crear bundle CA para SSL_CERT_FILE
cat "$CERTS/ca.crt" > "$CERTS/ca-bundle.crt"
# Incluir también el sistema para que funcione la conexión upstream
cat /etc/ssl/certs/ca-certificates.crt >> "$CERTS/ca-bundle.crt"

echo ""
echo "=== Certificados listos ==="
echo "  CA:  $CERTS/ca.crt"
echo "  Key: $CERTS/server.key"
echo ""
echo "Para iniciar el monitor:"
echo "1. Mata crush en ventana 1 (Ctrl+C)"
echo "2. En ventana 2 ejecuta el proxy:"
echo "   cd $DIR && python3 proxymon.py"
echo ""
echo "3. En ventana 1, relanza crush con:"
echo "   SSL_CERT_FILE=$CERTS/ca-bundle.crt \\"
echo "   OPENCODE_GO_BASE_URL=https://127.0.0.1:8443/zen/go/v1/ \\"
echo "   $(which crush) --yolo"
