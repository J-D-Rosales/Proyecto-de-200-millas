"""
Helper functions for Athena queries
"""
import os
import time
import boto3

GLUE_DATABASE = os.environ.get('GLUE_DATABASE', 'millas_analytics_db')
ATHENA_OUTPUT_BUCKET = os.environ.get('ATHENA_OUTPUT_BUCKET')

athena_client = boto3.client('athena')

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "POST,OPTIONS,GET",
    "Content-Type": "application/json"
}

def execute_athena_query(query, workgroup='primary'):
    """
    Ejecuta una query en Athena y espera los resultados
    
    Args:
        query: SQL query string
        workgroup: Athena workgroup name (default: 'primary')
    
    Returns:
        Query results from Athena
    """
    
    # Configuración de la query
    query_config = {
        'QueryString': query,
        'QueryExecutionContext': {
            'Database': GLUE_DATABASE
        },
        'ResultConfiguration': {
            'OutputLocation': f's3://{ATHENA_OUTPUT_BUCKET}/results/'
        }
    }
    
    # Intentar con el workgroup especificado
    try:
        response = athena_client.start_query_execution(
            **query_config,
            WorkGroup=workgroup
        )
    except athena_client.exceptions.InvalidRequestException as e:
        # Si el workgroup no existe, intentar con 'primary'
        if 'WorkGroup is not found' in str(e) and workgroup != 'primary':
            print(f"Workgroup '{workgroup}' no encontrado, usando 'primary'")
            response = athena_client.start_query_execution(**query_config)
        else:
            raise
    
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
    """
    Parsea los resultados de Athena a formato JSON
    
    Args:
        results: Raw results from Athena
    
    Returns:
        List of dictionaries with parsed data
    """
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
                if value is not None:
                    if '.' in str(value):
                        value = float(value)
                    else:
                        value = int(value)
            except (ValueError, TypeError):
                pass
            row_data[headers[i]] = value
        data.append(row_data)
    
    return data
