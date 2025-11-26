import os
import boto3
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv('../.env')

AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID')
ANALYTICS_BUCKET = f"bucket-analytic-{AWS_ACCOUNT_ID}"
GLUE_DATABASE = "millas_analytics_db"

glue_client = boto3.client('glue', region_name='us-east-1')

def create_database():
    """Crea la base de datos de Glue si no existe"""
    try:
        glue_client.get_database(Name=GLUE_DATABASE)
        print(f"✅ Database '{GLUE_DATABASE}' ya existe")
    except glue_client.exceptions.EntityNotFoundException:
        print(f"🔨 Creando database '{GLUE_DATABASE}'...")
        glue_client.create_database(
            DatabaseInput={
                'Name': GLUE_DATABASE,
                'Description': 'Database para analytics de 200 Millas'
            }
        )
        print(f"✅ Database '{GLUE_DATABASE}' creada")

def create_pedidos_table():
    """Crea la tabla de pedidos en Glue con el schema correcto"""
    table_name = 'pedidos'
    
    try:
        glue_client.get_table(DatabaseName=GLUE_DATABASE, Name=table_name)
        print(f"🗑️  Eliminando tabla existente '{table_name}'...")
        glue_client.delete_table(DatabaseName=GLUE_DATABASE, Name=table_name)
    except glue_client.exceptions.EntityNotFoundException:
        pass
    
    print(f"🔨 Creando tabla '{table_name}'...")
    
    glue_client.create_table(
        DatabaseName=GLUE_DATABASE,
        TableInput={
            'Name': table_name,
            'StorageDescriptor': {
                'Columns': [
                    {'Name': 'pedido_id', 'Type': 'string'},
                    {'Name': 'local_id', 'Type': 'string'},
                    {'Name': 'tenant_id_usuario', 'Type': 'string'},
                    {'Name': 'productos', 'Type': 'array<struct<producto_id:string,cantidad:int>>'},
                    {'Name': 'costo', 'Type': 'double'},
                    {'Name': 'direccion', 'Type': 'string'},
                    {'Name': 'estado', 'Type': 'string'},
                    {'Name': 'created_at', 'Type': 'string'},
                    {'Name': 'tenant_id_local', 'Type': 'string'},
                    {'Name': 'tenant_id_estado', 'Type': 'string'},
                    {'Name': 'fecha_entrega_aproximada', 'Type': 'string'},
                    {'Name': 'usuario_correo', 'Type': 'string'},
                    {'Name': 'tenant_id', 'Type': 'string'}
                ],
                'Location': f's3://{ANALYTICS_BUCKET}/pedidos/',
                'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                'SerdeInfo': {
                    'SerializationLibrary': 'org.openx.data.jsonserde.JsonSerDe',
                    'Parameters': {
                        'serialization.format': '1'
                    }
                }
            },
            'TableType': 'EXTERNAL_TABLE',
            'Parameters': {
                'classification': 'json'
            }
        }
    )
    
    print(f"✅ Tabla '{table_name}' creada")

def create_historial_estados_table():
    """Crea la tabla de historial_estados en Glue con el schema correcto"""
    table_name = 'historial_estados'
    
    try:
        glue_client.get_table(DatabaseName=GLUE_DATABASE, Name=table_name)
        print(f"🗑️  Eliminando tabla existente '{table_name}'...")
        glue_client.delete_table(DatabaseName=GLUE_DATABASE, Name=table_name)
    except glue_client.exceptions.EntityNotFoundException:
        pass
    
    print(f"🔨 Creando tabla '{table_name}'...")
    
    glue_client.create_table(
        DatabaseName=GLUE_DATABASE,
        TableInput={
            'Name': table_name,
            'StorageDescriptor': {
                'Columns': [
                    {'Name': 'estado_id', 'Type': 'string'},
                    {'Name': 'pedido_id', 'Type': 'string'},
                    {'Name': 'estado', 'Type': 'string'},
                    {'Name': 'hora_inicio', 'Type': 'string'},
                    {'Name': 'hora_fin', 'Type': 'string'},
                    {'Name': 'empleado', 'Type': 'string'}
                ],
                'Location': f's3://{ANALYTICS_BUCKET}/historial_estados/',
                'InputFormat': 'org.apache.hadoop.mapred.TextInputFormat',
                'OutputFormat': 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat',
                'SerdeInfo': {
                    'SerializationLibrary': 'org.openx.data.jsonserde.JsonSerDe',
                    'Parameters': {
                        'serialization.format': '1'
                    }
                }
            },
            'TableType': 'EXTERNAL_TABLE',
            'Parameters': {
                'classification': 'json'
            }
        }
    )
    
    print(f"✅ Tabla '{table_name}' creada")

def main():
    print("=" * 60)
    print("🔧 Creando Tablas de Glue con Schema Correcto")
    print("=" * 60)
    print()
    
    # Crear database
    create_database()
    print()
    
    # Crear tablas
    create_pedidos_table()
    print()
    create_historial_estados_table()
    
    print()
    print("=" * 60)
    print("✅ Tablas de Glue creadas exitosamente")
    print("=" * 60)
    print()
    print("📋 Tablas creadas:")
    print(f"  - {GLUE_DATABASE}.pedidos")
    print(f"  - {GLUE_DATABASE}.historial_estados")
    print()
    print("💡 Ahora puedes ejecutar queries en Athena")
    print()

if __name__ == "__main__":
    main()
