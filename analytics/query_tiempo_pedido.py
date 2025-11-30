import json
from athena_helper import execute_athena_query, parse_results, CORS_HEADERS

def lambda_handler(event, context):
    """
    Query: Tiempo total de pedido desde procesado hasta recibido, agrupado por local con paginación
    Query params:
        - local_id (opcional): Filtrar por local específico
        - page (opcional): Número de página (default: 1)
        - page_size (opcional): Tamaño de página (default: 10, max: 100)
    """
    try:
        # Parsear query parameters
        params = event.get('queryStringParameters', {}) or {}
        local_id = params.get('local_id')
        page = int(params.get('page', 1))
        page_size = min(int(params.get('page_size', 10)), 100)  # Max 100 items per page
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Query SQL que calcula el tiempo entre el primer estado (procesado) y el último (recibido)
        if local_id:
            query = f"""
            WITH estados_ordenados AS (
                SELECT 
                    h.pedido_id,
                    h.estado,
                    h.hora_inicio,
                    h.hora_fin,
                    ROW_NUMBER() OVER (PARTITION BY h.pedido_id ORDER BY h.hora_inicio ASC) as rn_first,
                    ROW_NUMBER() OVER (PARTITION BY h.pedido_id ORDER BY h.hora_fin DESC) as rn_last
                FROM historial_estados h
                INNER JOIN pedidos ped ON h.pedido_id = ped.pedido_id
                WHERE ped.local_id = '{local_id}'
            ),
            primer_estado AS (
                SELECT pedido_id, hora_inicio as inicio
                FROM estados_ordenados
                WHERE rn_first = 1 AND estado = 'procesando'
            ),
            ultimo_estado AS (
                SELECT pedido_id, hora_fin as fin
                FROM estados_ordenados
                WHERE rn_last = 1 AND estado = 'recibido'
            )
            SELECT 
                '{local_id}' as local_id,
                p.pedido_id,
                p.inicio,
                u.fin,
                date_diff('minute', 
                    from_iso8601_timestamp(p.inicio), 
                    from_iso8601_timestamp(u.fin)
                ) as tiempo_total_minutos,
                date_diff('hour', 
                    from_iso8601_timestamp(p.inicio), 
                    from_iso8601_timestamp(u.fin)
                ) as tiempo_total_horas
            FROM primer_estado p
            INNER JOIN ultimo_estado u ON p.pedido_id = u.pedido_id
            ORDER BY tiempo_total_minutos DESC
            """
            print(f"Ejecutando query: Tiempo total de pedido para local {local_id}")
        else:
            query = """
            WITH estados_ordenados AS (
                SELECT 
                    h.pedido_id,
                    h.estado,
                    h.hora_inicio,
                    h.hora_fin,
                    ped.local_id,
                    ROW_NUMBER() OVER (PARTITION BY h.pedido_id ORDER BY h.hora_inicio ASC) as rn_first,
                    ROW_NUMBER() OVER (PARTITION BY h.pedido_id ORDER BY h.hora_fin DESC) as rn_last
                FROM historial_estados h
                INNER JOIN pedidos ped ON h.pedido_id = ped.pedido_id
            ),
            primer_estado AS (
                SELECT pedido_id, local_id, hora_inicio as inicio
                FROM estados_ordenados
                WHERE rn_first = 1 AND estado = 'procesando'
            ),
            ultimo_estado AS (
                SELECT pedido_id, hora_fin as fin
                FROM estados_ordenados
                WHERE rn_last = 1 AND estado = 'recibido'
            )
            SELECT 
                p.local_id,
                COUNT(DISTINCT p.pedido_id) as total_pedidos,
                AVG(date_diff('minute', 
                    from_iso8601_timestamp(p.inicio), 
                    from_iso8601_timestamp(u.fin)
                )) as tiempo_promedio_minutos,
                MIN(date_diff('minute', 
                    from_iso8601_timestamp(p.inicio), 
                    from_iso8601_timestamp(u.fin)
                )) as tiempo_minimo_minutos,
                MAX(date_diff('minute', 
                    from_iso8601_timestamp(p.inicio), 
                    from_iso8601_timestamp(u.fin)
                )) as tiempo_maximo_minutos
            FROM primer_estado p
            INNER JOIN ultimo_estado u ON p.pedido_id = u.pedido_id
            GROUP BY p.local_id
            ORDER BY tiempo_promedio_minutos DESC
            """
            print("Ejecutando query: Tiempo total de pedido por local (todos)")
        
        results = execute_athena_query(query, workgroup='millas-analytics-workgroup')
        
        # Parsear resultados
        all_data = parse_results(results)
        
        # Apply pagination in Python (Athena doesn't support OFFSET well)
        total_items = len(all_data)
        total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 1
        
        # Get the page slice
        start_idx = offset
        end_idx = offset + page_size
        data = all_data[start_idx:end_idx]
        
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': json.dumps({
                'query': 'Tiempo total de pedido (procesado -> recibido) por local',
                'local_id': local_id if local_id else 'todos',
                'pagination': {
                    'page': page,
                    'page_size': page_size,
                    'total_items': total_items,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                },
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
