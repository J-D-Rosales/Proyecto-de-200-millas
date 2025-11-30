#!/bin/bash

# Script para iniciar servidor local de la página de empleado
# Uso: ./start_server.sh [puerto]

PORT=${1:-8000}
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Iniciando servidor web para Panel de Empleado..."
echo "📁 Directorio: $DIR"
echo "🌐 Puerto: $PORT"
echo ""
echo "✅ Servidor iniciado en: http://localhost:$PORT"
echo "🔗 También accesible desde: http://127.0.0.1:$PORT"
echo ""
echo "⚠️  Recuerda configurar los endpoints en config.js antes de usar"
echo "⏹️  Presiona Ctrl+C para detener el servidor"
echo ""

cd "$DIR" && python3 -m http.server $PORT
