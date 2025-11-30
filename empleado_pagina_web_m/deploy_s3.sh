#!/bin/bash

# Script de despliegue a AWS S3
# Uso: ./deploy_s3.sh [nombre-bucket]

BUCKET_NAME=${1:-"200-millas-panel-empleado"}
REGION=${AWS_REGION:-"us-east-1"}

echo "=========================================="
echo "🚀 Despliegue Panel de Empleado - S3"
echo "=========================================="
echo ""
echo "📦 Bucket: $BUCKET_NAME"
echo "🌍 Región: $REGION"
echo ""

# Validar que AWS CLI esté configurado
echo "🔍 Verificando AWS CLI..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Error: AWS CLI no está configurado correctamente"
    echo "   Ejecuta: aws configure"
    exit 1
fi
echo "✅ AWS CLI configurado"
echo ""

# Verificar si el bucket existe, si no, crearlo
echo "🔍 Verificando si el bucket existe..."
if ! aws s3 ls "s3://$BUCKET_NAME" 2>&1 | grep -q 'NoSuchBucket'; then
    echo "✅ Bucket existe"
else
    echo "📦 Creando bucket $BUCKET_NAME..."
    aws s3 mb s3://$BUCKET_NAME --region $REGION
    
    echo "🌐 Configurando website hosting..."
    aws s3 website s3://$BUCKET_NAME \
        --index-document index.html \
        --error-document index.html
    
    echo "🔓 Configurando política pública..."
    cat > /tmp/bucket-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    }
  ]
}
EOF
    
    aws s3api put-bucket-policy \
        --bucket $BUCKET_NAME \
        --policy file:///tmp/bucket-policy.json
    
    rm /tmp/bucket-policy.json
    echo "✅ Bucket creado y configurado"
fi
echo ""

# Sincronizar archivos
echo "📤 Subiendo archivos..."
aws s3 sync . s3://$BUCKET_NAME \
    --exclude "*.md" \
    --exclude "*.sh" \
    --exclude ".git/*" \
    --exclude "README.md" \
    --exclude "DEPLOY.md" \
    --delete \
    --cache-control "public, max-age=3600" \
    --acl public-read

echo ""
echo "🔄 Configurando content-type para archivos..."

# HTML sin cache
aws s3 cp index.html s3://$BUCKET_NAME/index.html \
    --content-type "text/html" \
    --cache-control "no-cache, no-store, must-revalidate" \
    --acl public-read

# CSS
aws s3 cp styles.css s3://$BUCKET_NAME/styles.css \
    --content-type "text/css" \
    --cache-control "public, max-age=86400" \
    --acl public-read

# JavaScript
aws s3 cp app.js s3://$BUCKET_NAME/app.js \
    --content-type "application/javascript" \
    --cache-control "public, max-age=86400" \
    --acl public-read

aws s3 cp config.js s3://$BUCKET_NAME/config.js \
    --content-type "application/javascript" \
    --cache-control "no-cache, no-store, must-revalidate" \
    --acl public-read

echo ""
echo "=========================================="
echo "✅ Despliegue completado exitosamente!"
echo "=========================================="
echo ""
echo "🌐 Tu sitio está disponible en:"
echo "   http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Configura los endpoints en config.js"
echo "   2. Asegúrate de que CORS esté configurado en tu API"
echo "   3. Prueba el login y la funcionalidad"
echo ""
