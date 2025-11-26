#!/bin/bash

echo "=========================================="
echo "🔧 Configurando Athena"
echo "=========================================="

# Cargar variables de entorno
if [ -f ../.env ]; then
    export $(cat ../.env | grep -v '^#' | xargs)
    echo "✅ Variables de entorno cargadas"
else
    echo "❌ Archivo .env no encontrado"
    exit 1
fi

ATHENA_BUCKET="athena-results-${AWS_ACCOUNT_ID}"

echo ""
echo "📦 Verificando bucket de Athena: ${ATHENA_BUCKET}"

# Verificar si el bucket existe
if aws s3 ls "s3://${ATHENA_BUCKET}" 2>/dev/null; then
    echo "✅ Bucket existe"
else
    echo "🔨 Creando bucket..."
    aws s3 mb "s3://${ATHENA_BUCKET}" --region us-east-1
    echo "✅ Bucket creado"
fi

echo ""
echo "⚙️  Configurando workgroup de Athena..."

# Actualizar workgroup para usar el bucket
aws athena update-work-group \
    --work-group millas-analytics-workgroup \
    --configuration-updates "ResultConfigurationUpdates={OutputLocation=s3://${ATHENA_BUCKET}/results/},EnforceWorkGroupConfiguration=true" \
    --region us-east-1 2>/dev/null

if [ $? -eq 0 ]; then
    echo "✅ Workgroup configurado"
else
    echo "⚠️  Workgroup no existe o ya está configurado"
fi

echo ""
echo "⚙️  Configurando workgroup 'primary' (por defecto)..."

# También configurar el workgroup primary para que funcione desde la consola
aws athena update-work-group \
    --work-group primary \
    --configuration-updates "ResultConfigurationUpdates={OutputLocation=s3://${ATHENA_BUCKET}/results/}" \
    --region us-east-1

if [ $? -eq 0 ]; then
    echo "✅ Workgroup 'primary' configurado"
else
    echo "⚠️  Error al configurar workgroup 'primary'"
fi

echo ""
echo "=========================================="
echo "✅ Configuración completada"
echo "=========================================="
echo ""
echo "Ahora puedes ejecutar queries en Athena usando:"
echo "  - Workgroup: millas-analytics-workgroup"
echo "  - Database: millas_analytics_db"
echo "  - Output: s3://${ATHENA_BUCKET}/results/"
echo ""
