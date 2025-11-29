import os
import json
import boto3
import time

GLUE_DATABASE = os.environ.get('GLUE_DATABASE')
ATHENA_OUTPUT_BUCKET = os.environ.get('ATHENA_OUTPUT_BUCKET')

athena_client = boto3.client('athena')

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "POST,OPTIONS"
}

def execute_athena_query(query):
    """Ejecuta una query en Athena y espera los resultados"""
    
    # Iniciar la query
    response = athena_client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': GLUE_DATABASE
        },
        ResultConfiguration={
            'OutputLocation': f's3://{ATHENA_OUTPUT_BUCKET}/results/'
        },
        WorkGroup='millas-analytics-workgroup'
    )
    
    query_execution_id = response['QueryExecutionId']
    print(f"Query ID: {query_execution_id}")
    
    # Esperar a que termine
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        query_status = athena_client.get_query_execution(
            QueryExecutionId=query_execution_id
        )
        
        status = query_status['QueryExecution']['Status']['State']
        
        if status == 'SUCCEEDED':
            break
        elif status in ['FAILED', 'CANCELLED']:
            reason = query_status['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
            raise Exception(f"Query failed: {reason}")
        
        time.sleep(2)
        attempt += 1
    
    if attempt >= max_attempts:
        raise Exception("Query timeout")
    
    # Obtener resultados
    results = athena_client.get_query_results(
        QueryExecutionId=query_execution_id
    )
    
    return results

def parse_results(results):
    """Parsea los resultados de Athena a formato JSON"""
    rows = results['ResultSet']['Rows']
    
    if len(rows) < 2:
        return []
    
    # Primera fila son los headers
    headers = [col['VarCharValue'] for col in rows[0]['Data']]
    
    # Resto son los datos
    data = []
    for row in rows[1:]:
        row_data = {}
        for i, col in enumerate(row['Data']):
            value = col.get('VarCharValue', None)
            # Intentar convertir a número si es posible
            try:
                value = int(value) if value and '.' not in value else float(value)
            except (ValueError, TypeError):
                pass
            row_data[headers[i]] = value
        data.append(row_data)
    
    return data

def lambda_handler(event, context):
    """
    Query: Total de pedidos por local
    Body: { "local_id": "LOCAL-001" } (opcional)
    """
    try:
        # Parsear body
        body = {}
        if event.get('body'):
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        local_id = body.get('local_id')
        
        # Query SQL con filtro opcional
        if local_id:
            query = f"""
            SELECT 
                local_id,
                COUNT(*) as total_pedidos
            FROM pedidos
            WHERE local_id = '{local_id}'
            GROUP BY local_id
            """
            print(f"Ejecutando query: Total de pedidos para local {local_id}")
        else:
            query = """
            SELECT 
                local_id,
                COUNT(*) as total_pedidos
            FROM pedidos
            GROUP BY local_id
            ORDER BY total_pedidos DESC
            """
            print("Ejecutando query: Total de pedidos por local (todos)")
        
        results = execute_athena_query(query)
        
        # Parsear resultados
        data = parse_results(results)
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'query': 'Total de pedidos por local',
                'local_id': local_id if local_id else 'todos',
                'data': data
            }, ensure_ascii=False)
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'error': str(e)
            })
        }
