#!/bin/bash

# Script para probar el flujo completo de un pedido
# Uso: bash test_flujo_completo.sh <order_id>

set -e

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Verificar que se proporcionó el order_id
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Debes proporcionar el order_id${NC}"
    echo ""
    echo "Uso: bash test_flujo_completo.sh <order_id>"
    echo ""
    echo "Ejemplo:"
    echo "  bash test_flujo_completo.sh 927b448d-9400-4355-afe6-9631962f8d35"
    exit 1
fi

ORDER_ID="$1"
EMPLEADO_COCINA="EMP-COCINA-001"
EMPLEADO_EMPAQUE="EMP-EMPAQUE-001"
EMPLEADO_DELIVERY="DEL-001"

# Obtener la URL del API Gateway
echo -e "${BLUE}🔍 Obteniendo URL del API Gateway...${NC}"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name servicio-empleados-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`HttpApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -z "$API_URL" ]; then
    echo -e "${YELLOW}⚠️  No se pudo obtener la URL automáticamente${NC}"
    echo -e "${YELLOW}Por favor, ingresa la URL del API Gateway de servicio-empleados:${NC}"
    read -p "URL: " API_URL
fi

# Remover trailing slash si existe
API_URL="${API_URL%/}"

echo -e "${GREEN}✅ URL del API: ${API_URL}${NC}"
echo ""

# Función para hacer requests
make_request() {
    local endpoint=$1
    local body=$2
    local description=$3
    
    echo -e "${BLUE}📤 ${description}${NC}"
    echo "   Endpoint: ${endpoint}"
    echo "   Body: ${body}"
    
    response=$(curl -s -X POST "${API_URL}${endpoint}" \
        -H "Content-Type: application/json" \
        -d "${body}")
    
    echo "   Respuesta: ${response}"
    
    # Verificar si hay error
    if echo "$response" | grep -q '"error"'; then
        echo -e "${RED}   ❌ Error en la respuesta${NC}"
        return 1
    else
        echo -e "${GREEN}   ✅ Éxito${NC}"
        return 0
    fi
}

echo "=========================================="
echo "🚀 Iniciando Flujo Completo de Pedido"
echo "=========================================="
echo ""
echo "Order ID: ${ORDER_ID}"
echo ""

# Paso 1: Iniciar Cocina
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PASO 1: Iniciar Preparación en Cocina${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
make_request "/empleados/cocina/iniciar" \
    "{\"order_id\": \"${ORDER_ID}\", \"empleado_id\": \"${EMPLEADO_COCINA}\"}" \
    "Iniciando preparación en cocina"
echo ""
sleep 3

# Paso 2: Completar Cocina
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PASO 2: Completar Cocina${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
make_request "/empleados/cocina/completar" \
    "{\"order_id\": \"${ORDER_ID}\", \"empleado_id\": \"${EMPLEADO_COCINA}\"}" \
    "Completando cocina"
echo ""
sleep 3

# Paso 3: Completar Empaquetado
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PASO 3: Completar Empaquetado${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
make_request "/empleados/empaque/completar" \
    "{\"order_id\": \"${ORDER_ID}\", \"empleado_id\": \"${EMPLEADO_EMPAQUE}\"}" \
    "Completando empaquetado"
echo ""
sleep 3

# Paso 4: Iniciar Delivery
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PASO 4: Iniciar Delivery${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
make_request "/empleados/delivery/iniciar" \
    "{\"order_id\": \"${ORDER_ID}\", \"empleado_id\": \"${EMPLEADO_DELIVERY}\"}" \
    "Iniciando delivery"
echo ""
sleep 3

# Paso 5: Entregar Pedido
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PASO 5: Entregar Pedido${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
make_request "/empleados/delivery/entregar" \
    "{\"order_id\": \"${ORDER_ID}\", \"empleado_id\": \"${EMPLEADO_DELIVERY}\"}" \
    "Entregando pedido"
echo ""
sleep 3

# Paso 6: Cliente Confirma Recepción
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}PASO 6: Cliente Confirma Recepción${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Obtener URL del API de clientes
echo -e "${BLUE}🔍 Obteniendo URL del API de clientes...${NC}"
API_URL_CLIENTES=$(aws cloudformation describe-stacks \
    --stack-name service-clientes-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`HttpApiUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -z "$API_URL_CLIENTES" ]; then
    echo -e "${YELLOW}⚠️  No se pudo obtener la URL del API de clientes automáticamente${NC}"
    echo -e "${YELLOW}Saltando paso de confirmación de cliente${NC}"
else
    API_URL_CLIENTES="${API_URL_CLIENTES%/}"
    echo -e "${GREEN}✅ URL del API de clientes: ${API_URL_CLIENTES}${NC}"
    
    echo -e "${BLUE}📤 Cliente confirmando recepción${NC}"
    echo "   Endpoint: /pedido/confirmar"
    echo "   Body: {\"order_id\": \"${ORDER_ID}\", \"empleado_id\": \"CLIENTE\"}"
    
    response=$(curl -s -X POST "${API_URL_CLIENTES}/pedido/confirmar" \
        -H "Content-Type: application/json" \
        -d "{\"order_id\": \"${ORDER_ID}\", \"empleado_id\": \"CLIENTE\"}")
    
    echo "   Respuesta: ${response}"
    
    if echo "$response" | grep -q '"error"'; then
        echo -e "${RED}   ❌ Error en la respuesta${NC}"
    else
        echo -e "${GREEN}   ✅ Éxito${NC}"
    fi
fi
echo ""

echo "=========================================="
echo -e "${GREEN}✅ Flujo Completo Ejecutado${NC}"
echo "=========================================="
echo ""
echo "🔍 Verifica el estado en:"
echo "   1. AWS Step Functions Console"
echo "   2. DynamoDB tabla Historial Estados"
echo ""
echo "💡 Para ver el historial completo:"
echo "   aws dynamodb query \\"
echo "     --table-name Millas-Historial-Estados \\"
echo "     --key-condition-expression \"pedido_id = :pid\" \\"
echo "     --expression-attribute-values '{\":pid\":{\"S\":\"${ORDER_ID}\"}}'"
echo ""
