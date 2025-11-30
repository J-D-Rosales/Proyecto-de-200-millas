#!/bin/bash
set -Eeuo pipefail

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# -------- Utilidades --------
die() { echo -e "${RED}❌ $*${NC}"; exit 1; }
log() { echo -e "$*"; }

show_menu() {
  echo "============================================================"
  echo "🚀 MILLAS - SETUP BACKEND"
  echo "============================================================"
  echo ""
  echo "Selecciona una opción:"
  echo ""
  echo "  1) 🏗️  Desplegar todo (Infraestructura + Microservicios)"
  echo "  2) 🗑️  Eliminar todo (Microservicios + Infraestructura)"
  echo "  3) 📊 Solo crear infraestructura y poblar datos"
  echo "  4) 🚀 Solo desplegar microservicios"
  echo "  5) ❌ Salir"
  echo ""
}

check_env() {
  if [[ ! -f .env ]]; then
    echo -e "${YELLOW}⚠️  Archivo .env no encontrado${NC}"
    echo "Copia .env.example a .env y configura tus variables."
    exit 1
  fi
  # Carga segura de variables del .env
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a

  # Validaciones mínimas
  : "${AWS_ACCOUNT_ID:?Falta AWS_ACCOUNT_ID en .env}"
  : "${ORG_NAME:?Falta ORG_NAME en .env}"

  : "${TABLE_USUARIOS:?Falta TABLE_USUARIOS en .env}"
  : "${TABLE_EMPLEADOS:?Falta TABLE_EMPLEADOS en .env}"
  : "${TABLE_LOCALES:?Falta TABLE_LOCALES en .env}"
  : "${TABLE_PRODUCTOS:?Falta TABLE_PRODUCTOS en .env}"
  : "${TABLE_PEDIDOS:?Falta TABLE_PEDIDOS en .env}"
  : "${TABLE_HISTORIAL_ESTADOS:?Falta TABLE_HISTORIAL_ESTADOS en .env}"
  : "${TABLE_TOKENS_USUARIOS:?Falta TABLE_TOKENS_USUARIOS en .env}"
  : "${S3_BUCKET_NAME:?Falta S3_BUCKET_NAME en .env}"

  export AWS_REGION="${AWS_REGION:-us-east-1}"
}

check_prereqs() {
  command -v aws >/dev/null 2>&1 || die "AWS CLI no encontrado. Instálalo y ejecuta 'aws configure'."
  command -v python3 >/dev/null 2>&1 || die "python3 no encontrado."
  command -v pip3 >/dev/null 2>&1 || die "pip3 no encontrado."
  command -v sls >/dev/null 2>&1 || die "Serverless Framework (sls) no encontrado. Instala con: npm i -g serverless"
}

prepare_dependencies() {
  if [[ ! -f "Dependencias/requirements.txt" ]]; then
    echo -e "${YELLOW}ℹ️  No hay Dependencias/requirements.txt. Saltando Layer...${NC}"
    return 0
  fi

  echo -e "\n${BLUE}📦 Preparando Lambda Layer de dependencias...${NC}"
  mkdir -p Dependencias/python-dependencies
  pushd Dependencias/python-dependencies >/dev/null

  rm -rf python
  mkdir -p python

  echo -e "${YELLOW}📥 Instalando dependencias Python (Layer)...${NC}"
  pip3 install -r ../requirements.txt -t python/ --upgrade --quiet
  echo -e "${GREEN}✅ Dependencias instaladas en Dependencias/python-dependencies/python/${NC}"

  popd >/dev/null
}

ensure_images_bucket() {
  local bucket="${S3_BUCKET_NAME}"
  local region="${AWS_REGION:-us-east-1}"
  [[ -z "$bucket" ]] && die "S3_BUCKET_NAME no definido."

  if aws s3api head-bucket --bucket "${bucket}" 2>/dev/null; then
    echo -e "${GREEN}✅ Bucket de imágenes '${bucket}' disponible${NC}"
  else
    echo -e "${YELLOW}🔨 Creando bucket de imágenes '${bucket}'...${NC}"
    if [[ "${region}" == "us-east-1" ]]; then
      aws s3api create-bucket --bucket "${bucket}" >/dev/null
    else
      aws s3api create-bucket --bucket "${bucket}" --create-bucket-configuration LocationConstraint="${region}" >/dev/null
    fi
    aws s3api put-bucket-versioning --bucket "${bucket}" --versioning-configuration Status=Enabled >/dev/null
    aws s3api put-public-access-block --bucket "${bucket}" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true >/dev/null
    echo -e "${GREEN}✅ Bucket de imágenes creado${NC}"
  fi

  # Exporta la BASE_URL para que el generador use este bucket
  export BASE_URL_IMAGENES_PRODUCTOS="https://${bucket}.s3.amazonaws.com/productos"
  echo -e "${BLUE}ℹ️  BASE_URL_IMAGENES_PRODUCTOS=${BASE_URL_IMAGENES_PRODUCTOS}${NC}"
}

# (Opcional) Subida de DAG si tuvieras Airflow — desactivado por defecto
upload_airflow_dag() {
  return 0
  # Ejemplo:
  # local source_file="Analitica/etl_dynamodb.py"
  # local target_uri="s3://${ANALITICA_S3_BUCKET}/dags/etl_dynamodb.py"
  # [[ -f "$source_file" ]] || die "No se encuentra ${source_file}"
  # echo -e "${BLUE}📤 Subiendo DAG a ${target_uri}...${NC}"
  # aws s3 cp "${source_file}" "${target_uri}" >/dev/null
  # echo -e "${GREEN}✅ DAG actualizado${NC}"
}

create_dynamodb_tables() {
  echo -e "${BLUE}📚 Creando tablas DynamoDB...${NC}"
  
  # Tabla Usuarios
  aws dynamodb create-table \
    --table-name "${TABLE_USUARIOS}" \
    --attribute-definitions AttributeName=correo,AttributeType=S \
    --key-schema AttributeName=correo,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_USUARIOS} ya existe"
  
  # Tabla Empleados
  aws dynamodb create-table \
    --table-name "${TABLE_EMPLEADOS}" \
    --attribute-definitions AttributeName=local_id,AttributeType=S AttributeName=dni,AttributeType=S \
    --key-schema AttributeName=local_id,KeyType=HASH AttributeName=dni,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_EMPLEADOS} ya existe"
  
  # Tabla Locales
  aws dynamodb create-table \
    --table-name "${TABLE_LOCALES}" \
    --attribute-definitions AttributeName=local_id,AttributeType=S \
    --key-schema AttributeName=local_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_LOCALES} ya existe"
  
  # Tabla Productos
  aws dynamodb create-table \
    --table-name "${TABLE_PRODUCTOS}" \
    --attribute-definitions AttributeName=local_id,AttributeType=S AttributeName=producto_id,AttributeType=S \
    --key-schema AttributeName=local_id,KeyType=HASH AttributeName=producto_id,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_PRODUCTOS} ya existe"
  
  # Tabla Pedidos
  aws dynamodb create-table \
    --table-name "${TABLE_PEDIDOS}" \
    --attribute-definitions AttributeName=local_id,AttributeType=S AttributeName=pedido_id,AttributeType=S \
    --key-schema AttributeName=local_id,KeyType=HASH AttributeName=pedido_id,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_PEDIDOS} ya existe"
  
  # Tabla Historial Estados
  aws dynamodb create-table \
    --table-name "${TABLE_HISTORIAL_ESTADOS}" \
    --attribute-definitions AttributeName=pedido_id,AttributeType=S AttributeName=timestamp,AttributeType=S \
    --key-schema AttributeName=pedido_id,KeyType=HASH AttributeName=timestamp,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_HISTORIAL_ESTADOS} ya existe"
  
  # Tabla Tokens Usuarios
  aws dynamodb create-table \
    --table-name "${TABLE_TOKENS_USUARIOS}" \
    --attribute-definitions AttributeName=token,AttributeType=S \
    --key-schema AttributeName=token,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_TOKENS_USUARIOS} ya existe"
  
  echo -e "${GREEN}✅ Tablas DynamoDB creadas${NC}"
  
  # Esperar a que las tablas estén activas
  echo -e "${YELLOW}⏳ Esperando a que las tablas estén activas...${NC}"
  sleep 5
}

deploy_infrastructure() {
  echo -e "\n${BLUE}🏗️  Creando recursos de infraestructura (DynamoDB + S3)${NC}"
  
  # 1) Crear bucket de imágenes
  ensure_images_bucket
  
  # 2) Crear tablas DynamoDB
  create_dynamodb_tables
  
  # 3) Instalar dependencias Python para generador
  echo -e "${YELLOW}📦 Instalando dependencias Python...${NC}"
  pip3 install -q boto3 python-dotenv 2>/dev/null || pip3 install boto3 python-dotenv

  # 4) Generar datos de prueba
  if [[ -f "DataGenerator/DataGenerator.py" ]]; then
    echo -e "${BLUE}🧪 Generando datos de prueba...${NC}"
    python3 DataGenerator/DataGenerator.py
  else
    echo -e "${YELLOW}ℹ️  No se encontró DataGenerator.py. Saltando generación de datos.${NC}"
  fi

  # 5) Poblar DynamoDB
  if [[ -f "DataGenerator/DataPoblator.py" ]]; then
    echo -e "${BLUE}📤 Poblando tablas DynamoDB...${NC}"
    python3 DataGenerator/DataPoblator.py
  else
    echo -e "${YELLOW}ℹ️  No se encontró DataPoblator.py. Saltando población de datos.${NC}"
  fi

  echo -e "${GREEN}✅ Infraestructura lista${NC}"
}


fix_eventbridge_rules() {
  echo -e "${BLUE}🔧 Configurando EventBridge para Step Functions...${NC}"
  
  local LAMBDA_NAME="service-orders-200-millas-dev-cambiarEstado"
  local RULE_NAME="service-orders-cambiarEstado-manual"
  local REGION="us-east-1"
  
  # Verificar que el Lambda existe
  if ! aws lambda get-function --function-name "${LAMBDA_NAME}" --region "${REGION}" >/dev/null 2>&1; then
    echo -e "${YELLOW}   ⚠️  Lambda ${LAMBDA_NAME} no encontrado, saltando configuración de EventBridge${NC}"
    return 0
  fi
  
  local LAMBDA_ARN=$(aws lambda get-function \
    --function-name "${LAMBDA_NAME}" \
    --region "${REGION}" \
    --query 'Configuration.FunctionArn' \
    --output text)
  
  echo "   Lambda ARN: ${LAMBDA_ARN}"
  
  # Eliminar regla anterior si existe
  if aws events describe-rule --name "${RULE_NAME}" --region "${REGION}" >/dev/null 2>&1; then
    aws events remove-targets --rule "${RULE_NAME}" --ids "1" --region "${REGION}" 2>/dev/null || true
    aws events delete-rule --name "${RULE_NAME}" --region "${REGION}" 2>/dev/null || true
  fi
  
  # Crear nueva regla
  local EVENT_PATTERN='{
    "source": ["200millas.cocina", "200millas.delivery", "200millas.cliente"],
    "detail-type": ["EnPreparacion", "CocinaCompleta", "Empaquetado", "PedidoEnCamino", "EntregaDelivery", "ConfirmarPedidoCliente"]
  }'
  
  aws events put-rule \
    --name "${RULE_NAME}" \
    --event-pattern "${EVENT_PATTERN}" \
    --state ENABLED \
    --description "Rule to trigger cambiarEstado Lambda for order state changes" \
    --region "${REGION}" >/dev/null
  
  # Conectar Lambda a la regla
  aws events put-targets \
    --rule "${RULE_NAME}" \
    --targets "Id"="1","Arn"="${LAMBDA_ARN}" \
    --region "${REGION}" >/dev/null
  
  # Dar permisos al Lambda
  aws lambda remove-permission \
    --function-name "${LAMBDA_NAME}" \
    --statement-id AllowEventBridgeInvokeManual \
    --region "${REGION}" 2>/dev/null || true
  
  local RULE_ARN="arn:aws:events:${REGION}:${AWS_ACCOUNT_ID}:rule/${RULE_NAME}"
  
  aws lambda add-permission \
    --function-name "${LAMBDA_NAME}" \
    --statement-id AllowEventBridgeInvokeManual \
    --action lambda:InvokeFunction \
    --principal events.amazonaws.com \
    --source-arn "${RULE_ARN}" \
    --region "${REGION}" >/dev/null 2>&1 || true
  
  echo -e "${GREEN}   ✅ EventBridge configurado correctamente${NC}"
}

deploy_services() {
  echo -e "\n${BLUE}🚀 Desplegando microservicios con Serverless...${NC}"
  
  # 1) Preparar dependencias (Lambda Layer)
  prepare_dependencies
  
  # 2) Desplegar servicios principales usando serverless-compose
  echo -e "${YELLOW}📦 Desplegando servicios principales (users, products, clientes)...${NC}"
  sls deploy
  echo -e "${GREEN}✅ Servicios principales desplegados${NC}"
  
  # 3) Desplegar Step Functions
  if [[ -d "stepFunction" ]]; then
    echo -e "${YELLOW}⚙️  Desplegando Step Functions...${NC}"
    pushd stepFunction > /dev/null
    sls deploy
    popd > /dev/null
    echo -e "${GREEN}✅ Step Functions desplegado${NC}"
    
    # Configurar EventBridge para Step Functions
    fix_eventbridge_rules
  else
    echo -e "${YELLOW}ℹ️  No se encontró directorio stepFunction, saltando...${NC}"
  fi
  
  # 4) Desplegar servicio de empleados
  if [[ -d "servicio-empleados" ]]; then
    echo -e "${YELLOW}👥 Desplegando servicio de empleados...${NC}"
    pushd servicio-empleados > /dev/null
    sls deploy
    popd > /dev/null
    echo -e "${GREEN}✅ Servicio de empleados desplegado${NC}"
  else
    echo -e "${YELLOW}ℹ️  No se encontró directorio servicio-empleados, saltando...${NC}"
  fi
  
  # 5) Desplegar servicio de analytics
  if [[ -d "analytics" ]]; then
    echo -e "${YELLOW}📊 Desplegando servicio de analytics...${NC}"
    pushd analytics > /dev/null
    
    # Verificar si existe setup_analytics.sh
    if [[ -f "setup_analytics.sh" ]]; then
      bash setup_analytics.sh
    else
      # Si no existe el script, desplegar directamente
      sls deploy
    fi
    
    popd > /dev/null
    echo -e "${GREEN}✅ Servicio de analytics desplegado${NC}"
  else
    echo -e "${YELLOW}ℹ️  No se encontró directorio analytics, saltando...${NC}"
  fi
  
  echo -e "\n${GREEN}============================================================${NC}"
  echo -e "${GREEN}✅ Todos los microservicios desplegados exitosamente${NC}"
  echo -e "${GREEN}============================================================${NC}"
  
  # Mostrar URLs de API Gateway
  echo -e "\n${BLUE}📡 URLs de API Gateway:${NC}"
  echo -e "${YELLOW}Ejecuta estos comandos para obtener las URLs:${NC}"
  echo ""
  echo "  aws apigatewayv2 get-apis --query 'Items[?contains(Name, \`service-users\`)].ApiEndpoint' --output text"
  echo "  aws apigatewayv2 get-apis --query 'Items[?contains(Name, \`service-products\`)].ApiEndpoint' --output text"
  echo "  aws apigatewayv2 get-apis --query 'Items[?contains(Name, \`service-clientes\`)].ApiEndpoint' --output text"
  echo "  aws apigatewayv2 get-apis --query 'Items[?contains(Name, \`servicio-empleados\`)].ApiEndpoint' --output text"
  echo "  aws apigatewayv2 get-apis --query 'Items[?contains(Name, \`service-analytics\`)].ApiEndpoint' --output text"
  echo ""
}

remove_services() {
  echo -e "\n${RED}🗑️  Eliminando microservicios...${NC}"
  
  # 1) Eliminar servicio de analytics
  if [[ -d "analytics" ]]; then
    echo -e "${YELLOW}Eliminando servicio de analytics...${NC}"
    pushd analytics > /dev/null
    sls remove || true
    popd > /dev/null
  fi
  
  # 2) Eliminar servicio de empleados
  if [[ -d "servicio-empleados" ]]; then
    echo -e "${YELLOW}Eliminando servicio de empleados...${NC}"
    pushd servicio-empleados > /dev/null
    sls remove || true
    popd > /dev/null
  fi
  
  # 3) Eliminar Step Functions y reglas de EventBridge
  if [[ -d "stepFunction" ]]; then
    echo -e "${YELLOW}Eliminando Step Functions...${NC}"
    
    # Eliminar reglas de EventBridge primero
    local RULE_NAME="service-orders-cambiarEstado-manual"
    if aws events describe-rule --name "${RULE_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1; then
      echo -e "${YELLOW}   Eliminando reglas de EventBridge...${NC}"
      aws events remove-targets --rule "${RULE_NAME}" --ids "1" --region "${AWS_REGION}" 2>/dev/null || true
      aws events delete-rule --name "${RULE_NAME}" --region "${AWS_REGION}" 2>/dev/null || true
    fi
    
    pushd stepFunction > /dev/null
    sls remove || true
    popd > /dev/null
  fi
  
  # 4) Eliminar servicios principales (usando serverless-compose)
  echo -e "${YELLOW}Eliminando servicios principales (users, products, clientes)...${NC}"
  sls remove || true
  
  echo -e "${GREEN}✅ Microservicios eliminados${NC}"
}

remove_infrastructure() {
  echo -e "\n${RED}🗑️  Eliminando recursos de infraestructura...${NC}"

  # 1) Eliminar tablas DynamoDB
  echo -e "${YELLOW}Eliminando tablas DynamoDB...${NC}"
  aws dynamodb delete-table --table-name "${TABLE_USUARIOS}" --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_USUARIOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_EMPLEADOS}" --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_EMPLEADOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_LOCALES}" --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_LOCALES} no existe"
  aws dynamodb delete-table --table-name "${TABLE_PRODUCTOS}" --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_PRODUCTOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_PEDIDOS}" --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_PEDIDOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_HISTORIAL_ESTADOS}" --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_HISTORIAL_ESTADOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_TOKENS_USUARIOS}" --region "${AWS_REGION}" 2>/dev/null || echo "   Tabla ${TABLE_TOKENS_USUARIOS} no existe"
  
  # 2) Eliminar bucket de imágenes
  if [[ -n "${S3_BUCKET_NAME:-}" ]]; then
    echo -e "${YELLOW}Eliminando bucket de imágenes (${S3_BUCKET_NAME})...${NC}"
    aws s3 rm "s3://${S3_BUCKET_NAME}" --recursive 2>/dev/null || echo "   Bucket ${S3_BUCKET_NAME} vacío/no existe"
    aws s3 rb "s3://${S3_BUCKET_NAME}" --region "${AWS_REGION}" 2>/dev/null || echo "   Bucket ${S3_BUCKET_NAME} no existe"
  fi
  
  # 3) Eliminar buckets de analytics (si existen)
  local ANALYTICS_BUCKET="bucket-analytic-${AWS_ACCOUNT_ID}"
  local ATHENA_BUCKET="athena-results-${AWS_ACCOUNT_ID}"
  
  echo -e "${YELLOW}Eliminando buckets de analytics...${NC}"
  aws s3 rm "s3://${ANALYTICS_BUCKET}" --recursive 2>/dev/null || echo "   Bucket ${ANALYTICS_BUCKET} vacío/no existe"
  aws s3 rb "s3://${ANALYTICS_BUCKET}" --region "${AWS_REGION}" 2>/dev/null || echo "   Bucket ${ANALYTICS_BUCKET} no existe"
  
  aws s3 rm "s3://${ATHENA_BUCKET}" --recursive 2>/dev/null || echo "   Bucket ${ATHENA_BUCKET} vacío/no existe"
  aws s3 rb "s3://${ATHENA_BUCKET}" --region "${AWS_REGION}" 2>/dev/null || echo "   Bucket ${ATHENA_BUCKET} no existe"

  echo -e "${GREEN}✅ Infraestructura eliminada${NC}"
}

show_deployment_summary() {
  echo ""
  echo -e "${BLUE}============================================================${NC}"
  echo -e "${BLUE}📋 RESUMEN DEL DESPLIEGUE${NC}"
  echo -e "${BLUE}============================================================${NC}"
  echo ""
  echo -e "${GREEN}✅ Infraestructura:${NC}"
  echo "   • 7 tablas DynamoDB creadas"
  echo "   • Bucket S3 de imágenes: ${S3_BUCKET_NAME}"
  echo "   • Buckets de analytics creados"
  echo ""
  echo -e "${GREEN}✅ Microservicios desplegados:${NC}"
  echo "   • service-users (Usuarios y autenticación)"
  echo "   • service-products (Gestión de productos)"
  echo "   • service-clientes (Pedidos de clientes)"
  echo "   • servicio-empleados (Workflow de empleados)"
  echo "   • stepFunction (Orquestación de pedidos)"
  echo "   • service-analytics (Reportes y consultas)"
  echo ""
  echo -e "${YELLOW}📡 Próximos pasos:${NC}"
  echo ""
  echo "1. Obtener URLs de API Gateway:"
  echo "   aws apigatewayv2 get-apis --query 'Items[].{Name:Name,Endpoint:ApiEndpoint}' --output table"
  echo ""
  echo "2. Probar el sistema:"
  echo "   • Importar la colección Postman: 200 Millas - API Collection COMPLETA.postman_collection.json"
  echo "   • Crear un usuario: POST /users/register"
  echo "   • Iniciar sesión: POST /users/login"
  echo "   • Crear un pedido: POST /pedido/create"
  echo ""
  echo "3. Ver logs de una función:"
  echo "   aws logs tail /aws/lambda/NOMBRE_FUNCION --follow"
  echo ""
  echo "4. Consultar analytics:"
  echo "   • Exportar datos: POST /analytics/export"
  echo "   • Ver reportes: POST /analytics/pedidos-por-local"
  echo ""
  echo -e "${BLUE}============================================================${NC}"
}

main() {
  check_env
  check_prereqs

  while true; do
    show_menu
    read -rp "Opción: " option

    case "$option" in
      1)
        echo ""
        echo "============================================================"
        echo "🏗️  DESPLIEGUE COMPLETO"
        echo "============================================================"
        deploy_infrastructure
        deploy_services
        show_deployment_summary
        echo ""
        echo -e "${GREEN}============================================================${NC}"
        echo -e "${GREEN}🎉 DESPLIEGUE COMPLETADO EXITOSAMENTE${NC}"
        echo -e "${GREEN}============================================================${NC}"
        break
        ;;
      2)
        echo ""
        echo "============================================================"
        echo "🗑️  ELIMINACIÓN COMPLETA"
        echo "============================================================"
        echo -e "${RED}⚠️  ADVERTENCIA: Esto eliminará TODOS los recursos${NC}"
        read -rp "¿Estás seguro? (escribe 'SI' para confirmar): " confirm
        if [[ "$confirm" == "SI" ]]; then
          remove_services
          remove_infrastructure
          echo ""
          echo -e "${GREEN}============================================================${NC}"
          echo -e "${GREEN}✅ ELIMINACIÓN COMPLETADA${NC}"
          echo -e "${GREEN}============================================================${NC}"
        else
          echo -e "${YELLOW}Operación cancelada${NC}"
        fi
        break
        ;;
      3)
        echo ""
        echo "============================================================"
        echo "📊 SOLO INFRAESTRUCTURA"
        echo "============================================================"
        deploy_infrastructure
        echo ""
        echo -e "${GREEN}✅ Infraestructura creada${NC}"
        break
        ;;
      4)
        echo ""
        echo "============================================================"
        echo "🚀 SOLO MICROSERVICIOS"
        echo "============================================================"
        deploy_services
        echo ""
        echo -e "${GREEN}✅ Microservicios desplegados${NC}"
        break
        ;;
      5)
        echo -e "${YELLOW}Saliendo...${NC}"
        exit 0
        ;;
      *)
        echo -e "${RED}Opción inválida${NC}"
        ;;
    esac
  done
}

main
