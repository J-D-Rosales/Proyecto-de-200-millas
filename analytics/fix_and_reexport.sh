#!/bin/bash

echo "=========================================="
echo "🔧 Arreglando y Re-exportando Datos"
echo "=========================================="

# Cargar variables de entorno
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✅ Variables de entorno cargadas desde .env"
elif [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
    echo "✅ Variables de entorno cargadas desde ../.env"
else
    echo "❌ Archivo .env no encontrado"
    echo "   Asegúrate de tener un archivo .env en el directorio raíz"
    exit 1
fi

# Verificar que AWS_ACCOUNT_ID esté definido
if [ -z "${AWS_ACCOUNT_ID}" ]; then
    echo "❌ AWS_ACCOUNT_ID no está definido en .env"
    exit 1
fi

ANALYTICS_BUCKET="bucket-analytic-${AWS_ACCOUNT_ID}"

echo ""
echo "🗑️  Limpiando datos antiguos en S3..."
aws s3 rm "s3://${ANALYTICS_BUCKET}/pedidos/" --recursive 2>/dev/null || echo "   (No hay datos previos en pedidos)"
aws s3 rm "s3://${ANALYTICS_BUCKET}/historial_estados/" --recursive 2>/dev/null || echo "   (No hay datos previos en historial_estados)"
echo "✅ Limpieza completada"

echo ""
echo "🔨 Recreando tablas de Glue con schema correcto..."
python3 create_glue_tables.py

if [ $? -ne 0 ]; then
    echo "❌ Error al crear tablas de Glue"
    exit 1
fi

echo ""
echo "📤 Exportando datos con formato correcto (JSON Lines)..."
aws lambda invoke \
    --function-name service-analytics-dev-ExportDynamoDBToS3 \
    --region us-east-1 \
    /tmp/export-response.json

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Exportación completada"
    echo ""
    echo "📋 Respuesta:"
    cat /tmp/export-response.json | python3 -m json.tool 2>/dev/null || cat /tmp/export-response.json
    echo ""
else
    echo "❌ Error en la exportación"
    exit 1
fi

echo ""
echo "⏳ Esperando 15 segundos para que los crawlers procesen los datos..."
sleep 15

echo ""
echo "🔍 Verificando datos en S3..."
echo ""
echo "📊 Archivos en pedidos:"
aws s3 ls "s3://${ANALYTICS_BUCKET}/pedidos/" --recursive --human-readable

echo ""
echo "📊 Archivos en historial_estados:"
aws s3 ls "s3://${ANALYTICS_BUCKET}/historial_estados/" --recursive --human-readable

echo ""
echo "=========================================="
echo "✅ Proceso completado exitosamente"
echo "=========================================="
echo ""
echo "💡 Próximos pasos:"
echo ""
echo "   1. Ve a la consola de Athena (https://console.aws.amazon.com/athena)"
echo "   2. Selecciona el workgroup 'primary' o 'millas-analytics-workgroup'"
echo "   3. Selecciona la database 'millas_analytics_db'"
echo "   4. Ejecuta: SELECT * FROM pedidos LIMIT 10"
echo "   5. Deberías ver 10 filas individuales con columnas: local_id, pedido_id, costo, etc."
echo ""
echo "💡 Para probar los endpoints de analytics:"
echo "   - Obtén tu API Gateway URL desde la consola o el output de serverless deploy"
echo "   - Prueba: curl https://YOUR-API-ID.execute-api.us-east-1.amazonaws.com/analytics/pedidos-por-local"
echo ""
