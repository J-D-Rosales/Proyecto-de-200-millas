import os
import json
import boto3
from datetime import datetime
from decimal import Decimal

# Variables de entorno
TABLE_PEDIDOS = os.environ.get('TABLE_PEDIDOS')
TABLE_HISTORIAL_ESTADOS = os.environ.get('TABLE_HISTORIAL_ESTADOS')
ANALYTICS_BUCKET = os.environ.get('ANALYTICS_BUCKET')

dynamodb = boto3.resource('dynamodb')
s3_client = boto3.client('s3')
glue_client = boto3.client('glue')

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "POST,OPTIONS,GET",
    "Content-Type": "application/json"
}

def decimal_default(obj):
    """Convierte Decimal a float para JSON"""
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def export_table_to_s3(table_name, s3_prefix):
    """Exporta una tabla de DynamoDB a S3 en formato JSON"""
    print(f"📤 Exportando tabla {table_name}...")
    
    table = dynamodb.Table(table_name)
    
    # Escanear toda la tabla
    items = []
    response = table.scan()
    items.extend(response.get('Items', []))
    
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))
    
    print(f"   ✅ Total de items: {len(items)}")
    
    if len(items) == 0:
        print(f"   ⚠️  No hay datos para exportar en {table_name}")
        return None, 0
    
    # Generar timestamp para el archivo
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Guardar en S3 como JSON Lines (un objeto por línea)
    s3_key = f"{s3_prefix}/data_{timestamp}.json"
    
    # Convertir a JSON Lines (JSONL) - un objeto por línea
    json_lines = '\n'.join([json.dumps(item, default=decimal_default, ensure_ascii=False) for item in items])
    
    # Subir a S3
    s3_client.put_object(
        Bucket=ANALYTICS_BUCKET,
        Key=s3_key,
        Body=json_lines,
        ContentType='application/json'
    )
    
    print(f"   ✅ Exportado a s3://{ANALYTICS_BUCKET}/{s3_key}")
    return s3_key, len(items)

def trigger_crawler(crawler_name):
    """Inicia un Glue Crawler"""
    try:
        print(f"🕷️  Iniciando crawler: {crawler_name}")
        glue_client.start_crawler(Name=crawler_name)
        print(f"   ✅ Crawler {crawler_name} iniciado")
        return True
    except glue_client.exceptions.CrawlerRunningException:
        print(f"   ⚠️  Crawler {crawler_name} ya está ejecutándose")
        return True
    except Exception as e:
        print(f"   ❌ Error al iniciar crawler {crawler_name}: {str(e)}")
        return False

def lambda_handler(event, context):
    """Handler principal para exportar datos"""
    
    # Manejar CORS preflight
    if event.get('requestContext', {}).get('http', {}).get('method') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({'message': 'OK'})
        }
    
    try:
        print("=" * 60)
        print("🚀 Iniciando exportación de datos de DynamoDB a S3")
        print("=" * 60)
        
        start_time = datetime.now()
        
        # Exportar tabla de pedidos
        print("\n1️⃣  Exportando tabla de pedidos...")
        pedidos_key, pedidos_count = export_table_to_s3(TABLE_PEDIDOS, 'pedidos')
        
        # Exportar tabla de historial de estados
        print("\n2️⃣  Exportando tabla de historial de estados...")
        historial_key, historial_count = export_table_to_s3(TABLE_HISTORIAL_ESTADOS, 'historial_estados')
        
        # Iniciar crawlers automáticamente
        print("\n3️⃣  Iniciando Glue Crawlers...")
        crawler_pedidos = trigger_crawler('millas-pedidos-crawler')
        crawler_historial = trigger_crawler('millas-historial-crawler')
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("✅ Exportación completada exitosamente")
        print("=" * 60)
        
        result = {
            'message': 'Exportación completada exitosamente',
            'timestamp': datetime.now().isoformat(),
            'duration_seconds': round(duration, 2),
            'exports': {
                'pedidos': {
                    's3_key': pedidos_key,
                    'total_items': pedidos_count,
                    'crawler_started': crawler_pedidos
                },
                'historial_estados': {
                    's3_key': historial_key,
                    'total_items': historial_count,
                    'crawler_started': crawler_historial
                }
            },
            'next_steps': [
                'Los crawlers están procesando los datos (1-2 minutos)',
                'Las tablas estarán disponibles en Glue Database: millas_analytics_db',
                'Puedes consultar los endpoints de analytics después'
            ]
        }
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps(result, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'error': str(e),
                'message': 'Error durante la exportación'
            })
        }
