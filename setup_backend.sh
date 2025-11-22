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

  : "${IMAGES_BUCKET:?Falta IMAGES_BUCKET en .env}"

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
  local bucket="${IMAGES_BUCKET}"
  local region="${AWS_REGION:-us-east-1}"
  [[ -z "$bucket" ]] && die "IMAGES_BUCKET no definido."

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

  # 1) Crear tablas + 2) Generar datos + 3) Poblar
  # Asumo dos scripts Python en tu repo:
  # - scripts/create_tables.py  -> crea tablas con nombres del .env
  # - scripts/populate_dynamo.py -> lee example-data/*.json y puebla
  # - scripts/generate_data.py  -> genera example-data/*.json con los schemas nuevos
  #
  # Si tus rutas son otras, ajusta abajo.

  if [[ -f "scripts/create_tables.py" ]]; then
    echo -e "${BLUE}📚 Creando tablas DynamoDB...${NC}"
    python3 scripts/create_tables.py
  else
    echo -e "${YELLOW}ℹ️  scripts/create_tables.py no existe. Se asume que las tablas ya están creadas.${NC}"
  fi

  if [[ -f "scripts/generate_data.py" ]]; then
    echo -e "${BLUE}🧪 Generando datos de ejemplo...${NC}"
    python3 scripts/generate_data.py
  elif [[ -f "DataGenerator/generate_data.py" ]]; then
    echo -e "${BLUE}🧪 Generando datos de ejemplo (DataGenerator)...${NC}"
    pushd DataGenerator >/dev/null
    python3 generate_data.py
    popd >/dev/null
  else
    echo -e "${YELLOW}ℹ️  No se encontró generate_data.py. Saltando generación de datos.${NC}"
  fi

  if [[ -f "scripts/populate_dynamo.py" ]]; then
    echo -e "${BLUE}📤 Poblando DynamoDB con example-data/...${NC}"
    python3 scripts/populate_dynamo.py
  elif [[ -f "DataGenerator/populate_dynamo.py" ]]; then
    echo -e "${BLUE}📤 Poblando DynamoDB (DataGenerator)...${NC}"
    pushd DataGenerator >/dev/null
    python3 populate_dynamo.py
    popd >/dev/null
  else
    echo -e "${YELLOW}ℹ️  No se encontró populate_dynamo.py. Saltando poblar datos.${NC}"
  fi

  echo -e "${GREEN}✅ Infraestructura lista${NC}"
}

deploy_services() {
  echo -e "\n${BLUE}🚀 Desplegando microservicios con Serverless...${NC}"
  prepare_dependencies
  # upload_airflow_dag   # ← activa si usas Airflow
  sls deploy
  echo -e "${GREEN}✅ Microservicios desplegados${NC}"
}

remove_services() {
  echo -e "\n${RED}🗑️  Eliminando microservicios...${NC}"
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

  # Espera corta opcional (algunas regiones tardan en soltar recursos)
  sleep 3

  if [[ -n "${IMAGES_BUCKET:-}" ]]; then
    echo -e "${YELLOW}Eliminando bucket de imágenes...${NC}"
    aws s3 rm "s3://${IMAGES_BUCKET}" --recursive 2>/dev/null || echo "Bucket ${IMAGES_BUCKET} vacío/no existe"
    aws s3 rb "s3://${IMAGES_BUCKET}" 2>/dev/null || echo "Bucket ${IMAGES_BUCKET} no existe"
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
