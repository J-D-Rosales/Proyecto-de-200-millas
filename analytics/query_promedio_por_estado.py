import json
from athena_helper import execute_athena_query, parse_results, CORS_HEADERS

def lambda_handler(event, context):
    """
    Query: Promedio de tiempo que los pedidos pasan en cada estado
    Body: { "local_id": "LOCAL-001" } (opcional)
    """
    try:
        # Parsear body
        body = {}
        if event.get('body'):
            body = json.loads(event['body']) if isinstance(event['body'], str) else event['body']
        
        local_id = body.get('local_id')
        
        # Query SQL que calcula el tiempo promedio en cada estado
        if local_id:
            query = f"""
            WITH duraciones AS (
                SELECT 
                    h.estado,
                    h.pedido_id,
                    date_diff('minute', 
                        from_iso8601_timestamp(h.hora_inicio), 
                        from_iso8601_timestamp(h.hora_fin)
                    ) as duracion_minutos
                FROM historial_estados h
                INNER JOIN pedidos p ON h.pedido_id = p.pedido_id
                WHERE h.hora_inicio IS NOT NULL 
                  AND h.hora_fin IS NOT NULL
                  AND p.local_id = '{local_id}'
            )
            SELECT 
                estado,
                COUNT(DISTINCT pedido_id) as total_pedidos,
                AVG(duracion_minutos) as tiempo_promedio_minutos,
                MIN(duracion_minutos) as tiempo_minimo_minutos,
                MAX(duracion_minutos) as tiempo_maximo_minutos,
                STDDEV(duracion_minutos) as desviacion_estandar
            FROM duraciones
            GROUP BY estado
            ORDER BY tiempo_promedio_minutos DESC
            """
            print(f"Ejecutando query: Promedio por estado para local {local_id}")
        else:
            query = """
            WITH duraciones AS (
                SELECT 
                    estado,
                    pedido_id,
                    date_diff('minute', 
                        from_iso8601_timestamp(hora_inicio), 
                        from_iso8601_timestamp(hora_fin)
                    ) as duracion_minutos
                FROM historial_estados
                WHERE hora_inicio IS NOT NULL AND hora_fin IS NOT NULL
            )
            SELECT 
                estado,
                COUNT(DISTINCT pedido_id) as total_pedidos,
                AVG(duracion_minutos) as tiempo_promedio_minutos,
                MIN(duracion_minutos) as tiempo_minimo_minutos,
                MAX(duracion_minutos) as tiempo_maximo_minutos,
                STDDEV(duracion_minutos) as desviacion_estandar
            FROM duraciones
            GROUP BY estado
            ORDER BY tiempo_promedio_minutos DESC
            """
            print("Ejecutando query: Promedio de pedidos por estado (todos)")
        
        results = execute_athena_query(query, workgroup='millas-analytics-workgroup')
        data = parse_results(results)
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'query': 'Promedio de tiempo por estado',
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
