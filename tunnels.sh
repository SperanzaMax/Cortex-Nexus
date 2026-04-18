#!/bin/bash
# tunnels.sh — Levanta túneles públicos para todos los dashboards de Cortex-Nexus
# Uso: bash tunnels.sh

echo "========================================"
echo " Cortex-Nexus — Túneles Públicos"
echo "========================================"

# Matar túneles anteriores
pkill -f "localtunnel --port" 2>/dev/null && echo "→ Túneles anteriores cerrados." && sleep 1

# Levantar túneles en background
nohup npx localtunnel --port 8510 > /tmp/tunnel_8510.log 2>&1 &
PID1=$!
nohup npx localtunnel --port 8511 > /tmp/tunnel_8511.log 2>&1 &
PID2=$!

echo "→ Iniciando túneles (PIDs: $PID1, $PID2)..."
sleep 5

URL_8510=$(grep -o 'https://[^ ]*' /tmp/tunnel_8510.log | tail -1)
URL_8511=$(grep -o 'https://[^ ]*' /tmp/tunnel_8511.log | tail -1)

echo ""
echo "=========================================="
echo " 🧊 3D Monitor:          $URL_8510"
echo " 🔬 Validación Monitor:  $URL_8511"
echo "=========================================="
echo ""
echo "⚠️  Al entrar desde el celular, si pide una"
echo "   contraseña/IP, obtenela con:"
echo "   curl https://ipv4.icanhazip.com"
echo ""
echo "PIDs activos:"
echo "  Túnel 8510: $PID1"
echo "  Túnel 8511: $PID2"
echo ""
echo "Para cerrar: pkill -f 'localtunnel --port'"
