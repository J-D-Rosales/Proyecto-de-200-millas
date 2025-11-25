import json
import boto3
import os
from dotenv import load_dotenv
from botocore.exceptions import ClientError
import time
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import random as random_module

# Cargar variables de entorno
load_dotenv()

# ------------------------------------------------------------
# Configuración AWS
# ------------------------------------------------------------
AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID')

dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
dynamodb_client = boto3.client('dynamodb', region_name=AWS_REGION)
s3_client = boto3.client('s3', region_name=AWS_REGION)

# ------------------------------------------------------------
# Nombres de tablas desde .env (algunas pueden no estar definidas)
# ------------------------------------------------------------
TABLE_USUARIOS = os.getenv('TABLE_USUARIOS')
TABLE_EMPLEADOS = os.getenv('TABLE_EMPLEADOS')
TABLE_LOCALES = os.getenv('TABLE_LOCALES')
TABLE_PRODUCTOS = os.getenv('TABLE_PRODUCTOS')
TABLE_PEDIDOS = os.getenv('TABLE_PEDIDOS')
TABLE_HISTORIAL_ESTADOS = os.getenv('TABLE_HISTORIAL_ESTADOS')
TABLE_TOKENS_USUARIOS   = os.getenv('TABLE_TOKENS_USUARIOS')

# Bucket S3 (para verificación; la carga de imágenes no se hace aquí)
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

# Carpeta con los datos JSON
DATA_DIR = os.path.join(os.path.dirname(__file__), "example-data")

# ------------------------------------------------------------
# Mapeo de archivos JSON -> tablas/keys (dinámico: solo si hay nombre)
# ------------------------------------------------------------
TABLE_MAPPING = {}

if TABLE_USUARIOS:
    TABLE_MAPPING["usuarios.json"] = {
        "table_name": TABLE_USUARIOS,
        "pk": "correo",
        "sk": None
    }

if TABLE_EMPLEADOS:
    TABLE_MAPPING["empleados.json"] = {
        "table_name": TABLE_EMPLEADOS,
        "pk": "local_id",
        "sk": "dni"
    }

if TABLE_LOCALES:
    TABLE_MAPPING["locales.json"] = {
        "table_name": TABLE_LOCALES,
        "pk": "local_id",
        "sk": None
    }

if TABLE_PRODUCTOS:
    TABLE_MAPPING["productos.json"] = {
        "table_name": TABLE_PRODUCTOS,
        "pk": "local_id",
        "sk": "producto_id"  # Cambió de nombre a producto_id
    }

# Pedidos (PK=local_id, SK=pedido_id)
if TABLE_PEDIDOS:
    TABLE_MAPPING["pedidos.json"] = {
        "table_name": TABLE_PEDIDOS,
        "pk": "local_id",
        "sk": "pedido_id"
    }

if TABLE_HISTORIAL_ESTADOS:
    TABLE_MAPPING["historial_estados.json"] = {
        "table_name": TABLE_HISTORIAL_ESTADOS,
        "pk": "pedido_id",
        "sk": "estado_id"
    }

# Opcionales: tablas de tokens (solo si existen en .env)
if TABLE_TOKENS_USUARIOS:
    TABLE_MAPPING["tokens_usuarios.json"] = {
        "table_name": TABLE_TOKENS_USUARIOS,
        "pk": "token",
        "sk": None
    }

# ------------------------------------------------------------
# Utilidades
# ------------------------------------------------------------
def convert_float_to_decimal(obj):
    """Convierte float a Decimal recursivamente (requerido por DynamoDB)."""
    if isinstance(obj, list):
        return [convert_float_to_decimal(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: convert_float_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


def table_exists(table_name):
    """Verifica si una tabla existe."""
    try:
        dynamodb_client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            return False
        else:
            raise


def load_json_file(filename):
    """Carga un archivo JSON desde DATA_DIR."""
    filepath = os.path.join(DATA_DIR, filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return convert_float_to_decimal(data)
    except FileNotFoundError:
        print(f"⚠️  Archivo no encontrado: {filepath}")
        return None
    except json.JSONDecodeError as e:
        print(f"⚠️  Error al decodificar JSON en {filename}: {e}")
        return None


def delete_all_items_from_table(table_name, pk_name, sk_name=None):
    """Elimina todos los items de una tabla DynamoDB."""
    try:
        table = dynamodb.Table(table_name)
        
        print(f"   🗑️  Escaneando items en '{table_name}'...")
        response = table.scan()
        items = response.get('Items', [])
        
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response.get('Items', []))
        
        if not items:
            print(f"   ℹ️  La tabla '{table_name}' ya está vacía")
            return True
        
        print(f"   🗑️  Eliminando {len(items)} items de '{table_name}'...")
        
        with table.batch_writer() as batch:
            for item in items:
                key = {pk_name: item[pk_name]}
                if sk_name:
                    key[sk_name] = item[sk_name]
                batch.delete_item(Key=key)
        
        print(f"   ✅ {len(items)} items eliminados")
        return True
        
    except Exception as e:
        print(f"   ❌ Error al limpiar tabla: {str(e)}")
        return False


def batch_write_items(table, items, table_name):
    """Escribe items en lotes con reintentos y multithreading."""
    success_count = 0
    error_count = 0
    total_items = len(items)
    batch_size = 25
    count_lock = Lock()
    error_details = []
    
    batches = [items[i:i + batch_size] for i in range(0, total_items, batch_size)]
    
    def process_batch_with_retry(batch, max_retries=5):
        local_success = 0
        local_errors = 0
        local_error_details = []
        
        for attempt in range(max_retries):
            try:
                with table.batch_writer() as batch_writer:
                    for item in batch:
                        try:
                            batch_writer.put_item(Item=item)
                            local_success += 1
                        except ClientError as e:
                            if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                                # reintentar lote completo
                                raise
                            else:
                                local_errors += 1
                                local_error_details.append({
                                    'item': str(item)[:100],
                                    'error': str(e)
                                })
                return local_success, local_errors, local_error_details
                
            except ClientError as e:
                if e.response['Error']['Code'] == 'ProvisionedThroughputExceededException':
                    if attempt < max_retries - 1:
                        wait_time = (2 ** attempt) + random_module.uniform(0, 1)
                        time.sleep(wait_time)
                        local_success = 0
                        local_errors = 0
                        local_error_details = []
                        continue
                else:
                    local_errors += len(batch)
                    local_error_details.append({
                        'batch_size': len(batch),
                        'error': str(e)
                    })
                    return 0, local_errors, local_error_details
        
        return local_success, local_errors, local_error_details
    
    try:
        num_threads = min(10, len(batches)) if batches else 1
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {executor.submit(process_batch_with_retry, batch): batch for batch in batches}
            
            for future in as_completed(futures):
                try:
                    local_success, local_errors, local_error_details = future.result()
                    with count_lock:
                        success_count += local_success
                        error_count += local_errors
                        error_details.extend(local_error_details)
                        
                        if (success_count % 100 == 0) or (success_count + error_count >= total_items):
                            porcentaje = ((success_count + error_count) / total_items) * 100
                            print(f"      📊 Progreso: {success_count}/{total_items} ({porcentaje:.1f}%)")
                
                except Exception as e:
                    with count_lock:
                        error_count += len(futures[future])
                        error_details.append({
                            'batch': 'unknown',
                            'error': str(e)
                        })
    
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return success_count, total_items - success_count, error_details
    
    if error_details and len(error_details) <= 5:
        print(f"\n   ⚠️  Detalles de errores:")
        for i, err in enumerate(error_details[:5], 1):
            print(f"      {i}. {err.get('error', 'Error desconocido')[:200]}")
    
    return success_count, error_count, error_details


def populate_table(filename, table_config):
    """Puebla una tabla DynamoDB usando un archivo JSON."""
    table_name = table_config["table_name"]
    pk_name = table_config["pk"]
    sk_name = table_config["sk"]
    
    print(f"\n📤 Poblando tabla: {table_name}")
    print(f"   Archivo: {filename}")
    
    if not table_name:
        print(f"   ⚠️  No hay nombre de tabla configurado para {filename} (revisa tus variables de entorno)")
        return False
    
    if not table_exists(table_name):
        print(f"   ⚠️  Tabla '{table_name}' no existe. Debe crearse primero.")
        return False
    
    print(f"   ✅ Tabla '{table_name}' existe")
    
    # Limpiar datos existentes
    print(f"   🗑️  Limpiando datos existentes...")
    if not delete_all_items_from_table(table_name, pk_name, sk_name):
        print(f"   ❌ Error al limpiar la tabla")
        return False
    
    # Cargar datos
    items = load_json_file(filename)
    
    if items is None or not isinstance(items, list) or len(items) == 0:
        print(f"   ⚠️  No hay datos para insertar en {filename}")
        return True
    
    print(f"   📊 Total de items: {len(items)}")
    
    # Validar claves requeridas
    if items:
        first_item = items[0]
        if pk_name not in first_item:
            print(f"   ❌ Error: Los items no tienen la clave primaria '{pk_name}'")
            print(f"   Ejemplo de item: {first_item}")
            return False
        if sk_name and sk_name not in first_item:
            print(f"   ❌ Error: Los items no tienen la clave de ordenamiento '{sk_name}'")
            print(f"   Ejemplo de item: {first_item}")
            return False
    
    try:
        table = dynamodb.Table(table_name)
        success_count, error_count, error_details = batch_write_items(table, items, table_name)
        
        print(f"   ✅ Insertados: {success_count} items")
        if error_count > 0:
            print(f"   ⚠️  Errores: {error_count} items")
        
        return error_count == 0
        
    except Exception as e:
        print(f"   ❌ Error al insertar en tabla '{table_name}': {str(e)}")
        return False


def verify_credentials():
    """Verifica credenciales AWS."""
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        if credentials is None:
            print("❌ No se encontraron credenciales de AWS (perfil, variables de entorno o ~/.aws/credentials)")
            return False
        return True
    except Exception as e:
        print(f"❌ Error al verificar credenciales: {e}")
        return False


def create_s3_bucket():
    """Crea el bucket S3 con acceso público si no existe."""
    try:
        print(f"\n📦 Verificando bucket S3: {S3_BUCKET_NAME}")
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        print(f"   ✅ El bucket '{S3_BUCKET_NAME}' ya existe")
        
        # Verificar y actualizar configuración de acceso público si es necesario
        try:
            print(f"   🔓 Configurando acceso público...")
            
            # Desactivar el bloqueo de acceso público
            s3_client.delete_public_access_block(Bucket=S3_BUCKET_NAME)
            
            # Habilitar ACLs
            s3_client.put_bucket_ownership_controls(
                Bucket=S3_BUCKET_NAME,
                OwnershipControls={
                    'Rules': [
                        {
                            'ObjectOwnership': 'ObjectWriter'  # Permite ACLs
                        }
                    ]
                }
            )
            
            # Aplicar política de bucket para acceso público de lectura
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{S3_BUCKET_NAME}/*"
                    }
                ]
            }
            
            s3_client.put_bucket_policy(
                Bucket=S3_BUCKET_NAME,
                Policy=json.dumps(bucket_policy)
            )
            
            print(f"   ✅ Acceso público configurado correctamente")
            
        except Exception as config_error:
            print(f"   ⚠️  Advertencia al configurar acceso público: {str(config_error)}")
        
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code in ('404', 'NoSuchBucket'):
            try:
                print(f"   🔨 Creando bucket '{S3_BUCKET_NAME}' con acceso público...")
                
                # Crear bucket
                if AWS_REGION == 'us-east-1':
                    s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
                else:
                    s3_client.create_bucket(
                        Bucket=S3_BUCKET_NAME,
                        CreateBucketConfiguration={'LocationConstraint': AWS_REGION}
                    )
                
                print(f"   ✅ Bucket creado")
                
                # Habilitar versionado
                s3_client.put_bucket_versioning(
                    Bucket=S3_BUCKET_NAME,
                    VersioningConfiguration={'Status': 'Enabled'}
                )
                print(f"   ✅ Versionado habilitado")
                
                # Desactivar el bloqueo de acceso público
                s3_client.delete_public_access_block(Bucket=S3_BUCKET_NAME)
                print(f"   ✅ Bloqueo de acceso público desactivado")
                
                # Habilitar ACLs (ObjectWriter permite que los objetos tengan ACLs)
                s3_client.put_bucket_ownership_controls(
                    Bucket=S3_BUCKET_NAME,
                    OwnershipControls={
                        'Rules': [
                            {
                                'ObjectOwnership': 'ObjectWriter'
                            }
                        ]
                    }
                )
                print(f"   ✅ ACLs habilitadas")
                
                # Aplicar política de bucket para acceso público de lectura
                bucket_policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "PublicReadGetObject",
                            "Effect": "Allow",
                            "Principal": "*",
                            "Action": "s3:GetObject",
                            "Resource": f"arn:aws:s3:::{S3_BUCKET_NAME}/*"
                        }
                    ]
                }
                
                s3_client.put_bucket_policy(
                    Bucket=S3_BUCKET_NAME,
                    Policy=json.dumps(bucket_policy)
                )
                print(f"   ✅ Política de acceso público aplicada")
                
                print(f"\n   ⚠️  ADVERTENCIA: El bucket '{S3_BUCKET_NAME}' ahora es público")
                print(f"   ⚠️  Todos los objetos en este bucket serán accesibles públicamente")
                print(f"   ✅ Bucket '{S3_BUCKET_NAME}' creado exitosamente con acceso público")
                
                return True
                
            except Exception as create_error:
                print(f"   ❌ Error al crear bucket: {str(create_error)}")
                return False
        else:
            print(f"   ❌ Error al verificar bucket: {str(e)}")
            return False


def create_dynamodb_table(table_name, key_schema, attribute_definitions, 
                          global_secondary_indexes=None, stream_enabled=False, ttl_attribute=None):
    """Crea una tabla DynamoDB si no existe."""
    if not table_name:
        print("   ⚠️  Nombre de tabla no definido. Saltando creación.")
        return True  # lo tratamos como opcional

    try:
        print(f"\n📊 Verificando tabla: {table_name}")
        dynamodb_client.describe_table(TableName=table_name)
        print(f"   ✅ La tabla '{table_name}' ya existe")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            try:
                print(f"   🔨 Creando tabla '{table_name}'...")
                
                table_config = {
                    'TableName': table_name,
                    'KeySchema': key_schema,
                    'AttributeDefinitions': attribute_definitions,
                    'BillingMode': 'PAY_PER_REQUEST',
                    'Tags': [
                        {'Key': 'Project', 'Value': 'delivery-app'},
                        {'Key': 'Environment', 'Value': 'dev'}
                    ]
                }
                
                if global_secondary_indexes:
                    table_config['GlobalSecondaryIndexes'] = global_secondary_indexes
                
                if stream_enabled:
                    table_config['StreamSpecification'] = {
                        'StreamEnabled': True,
                        'StreamViewType': 'NEW_AND_OLD_IMAGES'
                    }
                
                dynamodb_client.create_table(**table_config)
                
                waiter = dynamodb_client.get_waiter('table_exists')
                waiter.wait(TableName=table_name)
                
                if ttl_attribute:
                    dynamodb_client.update_time_to_live(
                        TableName=table_name,
                        TimeToLiveSpecification={
                            'Enabled': True,
                            'AttributeName': ttl_attribute
                        }
                    )
                
                print(f"   ✅ Tabla '{table_name}' creada exitosamente")
                return True
            except Exception as create_error:
                print(f"   ❌ Error al crear tabla: {str(create_error)}")
                return False
        else:
            print(f"   ❌ Error al verificar tabla: {str(e)}")
            return False


def create_all_resources():
    """Crea tablas DynamoDB necesarias y verifica bucket S3."""
    print("\n" + "=" * 60)
    print("🏗️  CREANDO RECURSOS AWS (Delivery)")
    print("=" * 60)
    
    # Bucket S3 (opcional, pero lo verificamos/creamos si está definido)
    if S3_BUCKET_NAME:
        if not create_s3_bucket():
            return False
    
    # Usuarios: PK = correo
    if not create_dynamodb_table(
        table_name=TABLE_USUARIOS,
        key_schema=[{'AttributeName': 'correo', 'KeyType': 'HASH'}],
        attribute_definitions=[{'AttributeName': 'correo', 'AttributeType': 'S'}]
    ):
        return False
    
    # Empleados: PK = local_id, SK = dni
    if not create_dynamodb_table(
        table_name=TABLE_EMPLEADOS,
        key_schema=[
            {'AttributeName': 'local_id', 'KeyType': 'HASH'},
            {'AttributeName': 'dni', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'local_id', 'AttributeType': 'S'},
            {'AttributeName': 'dni', 'AttributeType': 'S'}
        ]
    ):
        return False
    
    # Locales: PK = local_id
    if not create_dynamodb_table(
        table_name=TABLE_LOCALES,
        key_schema=[{'AttributeName': 'local_id', 'KeyType': 'HASH'}],
        attribute_definitions=[{'AttributeName': 'local_id', 'AttributeType': 'S'}]
    ):
        return False
    
    # Productos: PK = local_id, SK = producto_id
    if not create_dynamodb_table(
        table_name=TABLE_PRODUCTOS,
        key_schema=[
            {'AttributeName': 'local_id', 'KeyType': 'HASH'},
            {'AttributeName': 'producto_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'local_id', 'AttributeType': 'S'},
            {'AttributeName': 'producto_id', 'AttributeType': 'S'}
        ]
    ):
        return False
    
    # Pedidos: PK = local_id, SK = pedido_id
    # GSI:
    #   - by_usuario_v2 (tenant_id_usuario, created_at)
    if not create_dynamodb_table(
        table_name=TABLE_PEDIDOS,
        key_schema=[
            {'AttributeName': 'local_id', 'KeyType': 'HASH'},
            {'AttributeName': 'pedido_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'local_id', 'AttributeType': 'S'},
            {'AttributeName': 'pedido_id', 'AttributeType': 'S'},
            {'AttributeName': 'tenant_id_usuario', 'AttributeType': 'S'},
            {'AttributeName': 'created_at', 'AttributeType': 'S'}
        ],
        global_secondary_indexes=[
            {
                'IndexName': 'by_usuario_v2',
                'KeySchema': [
                    {'AttributeName': 'tenant_id_usuario', 'KeyType': 'HASH'},
                    {'AttributeName': 'created_at', 'KeyType': 'RANGE'}
                ],
                'Projection': {'ProjectionType': 'ALL'}
            }
        ]
    ):
        return False
    
    # HistorialEstados: PK = pedido_id, SK = estado_id
    if not create_dynamodb_table(
        table_name=TABLE_HISTORIAL_ESTADOS,
        key_schema=[
            {'AttributeName': 'pedido_id', 'KeyType': 'HASH'},
            {'AttributeName': 'estado_id', 'KeyType': 'RANGE'}
        ],
        attribute_definitions=[
            {'AttributeName': 'pedido_id', 'AttributeType': 'S'},
            {'AttributeName': 'estado_id', 'AttributeType': 'S'}
        ]
    ):
        return False
    
    # Tokens Usuarios (opcional)
    if TABLE_TOKENS_USUARIOS:
        if not create_dynamodb_table(
            table_name=TABLE_TOKENS_USUARIOS,
            key_schema=[{'AttributeName': 'token', 'KeyType': 'HASH'}],
            attribute_definitions=[{'AttributeName': 'token', 'AttributeType': 'S'}]
        ):
            return False
    
    print("\n✅ Todos los recursos creados exitosamente")
    return True


def main():
    if not verify_credentials():
        return

    # Crear recursos
    if not create_all_resources():
        print("\n❌ Error al crear recursos. Abortando...")
        return

    if not os.path.exists(DATA_DIR):
        print(f"\n❌ La carpeta '{DATA_DIR}/' no existe (debería tener usuarios.json, empleados.json, etc.)")
        return

    print(f"\n🔌 Conectando a DynamoDB ({AWS_REGION})")
    print("✅ Conexión establecida")

    print("\n" + "=" * 60)
    print("📊 POBLANDO TABLAS")
    print("=" * 60)

    results = {}
    for filename, config in TABLE_MAPPING.items():
        success = populate_table(filename, config)
        results[filename] = success
        time.sleep(1)

    print("\n" + "=" * 60)
    print("📋 RESUMEN")
    print("=" * 60)

    successful = sum(1 for success in results.values() if success)
    failed = len(results) - successful

    print(f"\n✅ Tablas pobladas correctamente: {successful}")
    if failed > 0:
        print(f"❌ Tablas con errores: {failed}")
        for fname, ok in results.items():
            if not ok:
                print(f"   - {fname}")

    print("\n" + "=" * 60)
    print("🎉 COMPLETADO")
    print("=" * 60)


if __name__ == "__main__":
    main()
