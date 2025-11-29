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

deploy_infrastructure() {
  echo -e "\n${BLUE}🏗️  Creando recursos de infraestructura (DynamoDB + S3 Imágenes)${NC}"
  ensure_images_bucket

  echo -e "${YELLOW}📦 Instalando dependencias para generador/poblador...${NC}"
  pip3 install -q boto3 python-dotenv

  # 1) Crear tablas
  if [[ -f "scripts/create_tables.py" ]]; then
    echo -e "${BLUE}📚 Creando tablas DynamoDB (scripts/create_tables.py)...${NC}"
    python3 scripts/create_tables.py
  elif [[ -f "DataGenerator/create_tables.py" ]]; then
    echo -e "${BLUE}📚 Creando tablas DynamoDB (DataGenerator/create_tables.py)...${NC}"
    python3 DataGenerator/create_tables.py
  else
    echo -e "${YELLOW}ℹ️  No se encontró create_tables.py. Se asume que las tablas ya están creadas.${NC}"
  fi

  # 2) Generar datos
  if [[ -f "scripts/generate_data.py" ]]; then
    echo -e "${BLUE}🧪 Generando datos (scripts/generate_data.py)...${NC}"
    python3 scripts/generate_data.py
  elif [[ -f "DataGenerator/generate_data.py" ]]; then
    echo -e "${BLUE}🧪 Generando datos (DataGenerator/generate_data.py)...${NC}"
    python3 DataGenerator/generate_data.py
  elif [[ -f "DataGenerator/DataGenerator.py" ]]; then
    echo -e "${BLUE}🧪 Generando datos (DataGenerator/DataGenerator.py)...${NC}"
    python3 DataGenerator/DataGenerator.py
  else
    echo -e "${YELLOW}ℹ️  No se encontró generate_data.py / DataGenerator.py. Saltando generación de datos.${NC}"
  fi

  # 3) Poblar DynamoDB
  if [[ -f "scripts/populate_dynamo.py" ]]; then
    echo -e "${BLUE}📤 Poblando DynamoDB (scripts/populate_dynamo.py)...${NC}"
    python3 scripts/populate_dynamo.py
  elif [[ -f "DataGenerator/populate_dynamo.py" ]]; then
    echo -e "${BLUE}📤 Poblando DynamoDB (DataGenerator/populate_dynamo.py)...${NC}"
    python3 DataGenerator/populate_dynamo.py
  elif [[ -f "DataGenerator/DataPoblator.py" ]]; then
    echo -e "${BLUE}📤 Poblando DynamoDB (DataGenerator/DataPoblator.py)...${NC}"
    python3 DataGenerator/DataPoblator.py
  else
    echo -e "${YELLOW}ℹ️  No se encontró populate_dynamo.py / DataPoblator.py. Saltando poblar datos.${NC}"
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
  prepare_dependencies
  # upload_airflow_dag   # ← activa si usas Airflow
  
  # Desplegar servicios principales
  echo -e "${YELLOW}📦 Desplegando servicios principales...${NC}"
  sls deploy
  
  # Desplegar Step Functions
  if [[ -d "stepFunction" ]]; then
    echo -e "${YELLOW}⚙️  Desplegando Step Functions...${NC}"
    pushd stepFunction > /dev/null
    sls deploy
    popd > /dev/null
    echo -e "${GREEN}✅ Step Functions desplegado${NC}"
    
    # Configurar EventBridge
    fix_eventbridge_rules
  else
    echo -e "${YELLOW}ℹ️  No se encontró directorio stepFunction, saltando...${NC}"
  fi
  
  # Desplegar servicio de empleados
  if [[ -d "servicio-empleados" ]]; then
    echo -e "${YELLOW}👥 Desplegando servicio de empleados...${NC}"
    pushd servicio-empleados > /dev/null
    sls deploy
    popd > /dev/null
    echo -e "${GREEN}✅ Servicio de empleados desplegado${NC}"
  else
    echo -e "${YELLOW}ℹ️  No se encontró directorio servicio-empleados, saltando...${NC}"
  fi
  
  # Desplegar servicio de clientes
  if [[ -d "clientes" ]]; then
    echo -e "${YELLOW}👤 Desplegando servicio de clientes...${NC}"
    pushd clientes > /dev/null
    sls deploy
    popd > /dev/null
    echo -e "${GREEN}✅ Servicio de clientes desplegado${NC}"
  else
    echo -e "${YELLOW}ℹ️  No se encontró directorio clientes, saltando...${NC}"
  fi
  
  # Desplegar servicio de analytics
  if [[ -d "analytics" ]]; then
    echo -e "${YELLOW}📊 Desplegando servicio de analytics...${NC}"
    pushd analytics > /dev/null
    bash setup_analytics.sh
    popd > /dev/null
    echo -e "${GREEN}✅ Servicio de analytics desplegado${NC}"
  else
    echo -e "${YELLOW}ℹ️  No se encontró directorio analytics, saltando...${NC}"
  fi
  
  echo -e "${GREEN}✅ Todos los microservicios desplegados${NC}"
}

remove_services() {
  echo -e "\n${RED}🗑️  Eliminando microservicios...${NC}"
  
  # Eliminar servicio de empleados
  if [[ -d "servicio-empleados" ]]; then
    echo -e "${YELLOW}Eliminando servicio de empleados...${NC}"
    pushd servicio-empleados > /dev/null
    sls remove || true
    popd > /dev/null
  fi
  
  # Eliminar Step Functions y reglas de EventBridge
  if [[ -d "stepFunction" ]]; then
    echo -e "${YELLOW}Eliminando Step Functions...${NC}"
    
    # Eliminar reglas de EventBridge primero
    local RULE_NAME="service-orders-cambiarEstado-manual"
    if aws events describe-rule --name "${RULE_NAME}" --region us-east-1 >/dev/null 2>&1; then
      echo -e "${YELLOW}Eliminando reglas de EventBridge...${NC}"
      aws events remove-targets --rule "${RULE_NAME}" --ids "1" --region us-east-1 2>/dev/null || true
      aws events delete-rule --name "${RULE_NAME}" --region us-east-1 2>/dev/null || true
    fi
    
    pushd stepFunction > /dev/null
    sls remove || true
    popd > /dev/null
  fi
  
  # Eliminar servicios principales
  echo -e "${YELLOW}Eliminando servicios principales...${NC}"
  sls remove || true
  
  echo -e "${GREEN}✅ Microservicios eliminados${NC}"
}

remove_infrastructure() {
  echo -e "\n${RED}🗑️  Eliminando recursos de infraestructura...${NC}"

  echo -e "${YELLOW}Eliminando tablas DynamoDB...${NC}"
  aws dynamodb delete-table --table-name "${TABLE_USUARIOS}" 2>/dev/null || echo "Tabla ${TABLE_USUARIOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_EMPLEADOS}" 2>/dev/null || echo "Tabla ${TABLE_EMPLEADOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_LOCALES}" 2>/dev/null || echo "Tabla ${TABLE_LOCALES} no existe"
  aws dynamodb delete-table --table-name "${TABLE_PRODUCTOS}" 2>/dev/null || echo "Tabla ${TABLE_PRODUCTOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_PEDIDOS}" 2>/dev/null || echo "Tabla ${TABLE_PEDIDOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_HISTORIAL_ESTADOS}" 2>/dev/null || echo "Tabla ${TABLE_HISTORIAL_ESTADOS} no existe"
  aws dynamodb delete-table --table-name "${TABLE_TOKENS_USUARIOS}" 2>/dev/null || echo "Tabla ${TABLE_TOKENS_USUARIOS} no existe"
  # Espera corta opcional (algunas regiones tardan en soltar recursos)
  sleep 3

  if [[ -n "${S3_BUCKET_NAME:-}" ]]; then
    echo -e "${YELLOW}Eliminando bucket de imágenes...${NC}"
    aws s3 rm "s3://${S3_BUCKET_NAME}" --recursive 2>/dev/null || echo "Bucket ${S3_BUCKET_NAME} vacío/no existe"
    aws s3 rb "s3://${S3_BUCKET_NAME}" 2>/dev/null || echo "Bucket ${S3_BUCKET_NAME} no existe"
  fi

  echo -e "${GREEN}✅ Infraestructura eliminada${NC}"
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
        echo -e "${GREEN}✅ Listo${NC}"
        break
        ;;
      4)
        echo ""
        echo "============================================================"
        echo "🚀 SOLO MICROSERVICIOS"
        echo "============================================================"
        deploy_services
        echo ""
        echo -e "${GREEN}✅ Listo${NC}"
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
