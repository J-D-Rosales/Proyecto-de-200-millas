import json
from athena_helper import execute_athena_query, parse_results, CORS_HEADERS

def lambda_handler(event, context):
    """
    Query: Ganancias totales por local
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
                COUNT(*) as total_pedidos,
                SUM(costo) as ganancias_totales,
                AVG(costo) as ganancia_promedio
            FROM pedidos
            WHERE local_id = '{local_id}'
            GROUP BY local_id
            """
            print(f"Ejecutando query: Ganancias para local {local_id}")
        else:
            query = """
            SELECT 
                local_id,
                COUNT(*) as total_pedidos,
                SUM(costo) as ganancias_totales,
                AVG(costo) as ganancia_promedio
            FROM pedidos
            GROUP BY local_id
            ORDER BY ganancias_totales DESC
            """
            print("Ejecutando query: Ganancias totales por local (todos)")
        
        results = execute_athena_query(query, workgroup='millas-analytics-workgroup')
        data = parse_results(results)
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'query': 'Ganancias totales por local',
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
