#!/bin/bash

echo "=========================================="
echo "🔧 Setup Analytics - 200 Millas"
echo "=========================================="

# Cargar variables de entorno
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
    echo "✅ Variables de entorno cargadas"
else
    echo "❌ Archivo .env no encontrado"
    exit 1
fi

# Desplegar servicio de analytics
echo ""
echo "📦 Desplegando servicio de analytics..."
serverless deploy

if [ $? -ne 0 ]; then
    echo "❌ Error al desplegar analytics"
    exit 1
fi

echo "✅ Servicio de analytics desplegado"

# Configurar Athena
echo ""
echo "⚙️  Configurando Athena..."
bash configure_athena.sh

# Crear tablas de Glue con schema correcto
echo ""
echo "📊 Creando tablas de Glue con schema correcto..."
python3 create_glue_tables.py

if [ $? -ne 0 ]; then
    echo "⚠️  Error al crear tablas de Glue"
fi

# Ejecutar exportación inicial de datos
echo ""
echo "📤 Ejecutando exportación inicial de datos..."
aws lambda invoke \
    --function-name service-analytics-dev-ExportDynamoDBToS3 \
    --region us-east-1 \
    /tmp/export-response.json

if [ $? -eq 0 ]; then
    echo "✅ Exportación completada"
    cat /tmp/export-response.json
else
    echo "⚠️  Error en la exportación (puede ser normal si las tablas están vacías)"
fi

# Mostrar información de las tablas creadas
echo ""
echo "📋 Tablas en Glue Database:"
aws glue get-tables --database-name millas_analytics_db --region us-east-1 --query 'TableList[*].Name' --output table 2>/dev/null

echo ""
echo "=========================================="
echo "✅ Setup de Analytics completado"
echo "=========================================="
echo ""
echo "📍 Endpoints disponibles:"
echo ""
echo "  📤 Exportación de datos:"
echo "     POST /analytics/export"
echo ""
echo "  📊 Consultas de analytics:"
echo "     GET /analytics/pedidos-por-local"
echo "     GET /analytics/ganancias-por-local"
echo "     GET /analytics/tiempo-pedido"
echo "     GET /analytics/promedio-por-estado"
echo ""
echo "💡 Para exportar datos manualmente:"
echo "   Opción 1 (API): curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/export"
echo "   Opción 2 (CLI): aws lambda invoke --function-name service-analytics-dev-ExportDynamoDBToS3 /tmp/response.json"
echo ""
echo "💡 Para habilitar exportación automática (2 AM diaria):"
echo "   1. Editar analytics/serverless.yml"
echo "   2. Cambiar 'enabled: false' a 'enabled: true' en el schedule"
echo "   3. Redesplegar: cd analytics && serverless deploy"
echo ""
echo "💡 Para ejecutar los crawlers manualmente:"
echo "   aws glue start-crawler --name millas-pedidos-crawler"
echo "   aws glue start-crawler --name millas-historial-crawler"
echo ""
