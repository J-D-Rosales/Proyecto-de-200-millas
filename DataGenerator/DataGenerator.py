import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import random
import os

# Configuración
OUTPUT_DIR = Path(__file__).parent / "example-data"
SCHEMAS_DIR = Path(__file__).parent / "schemas-validation"

# Tenant solo para tablas multi-tenant (p.ej. pedidos)
TENANT_ID = os.getenv("TENANT_ID", "millas")

NOMBRES = ["Juan","María","Carlos","Ana","Luis","Carmen","José","Laura","Miguel","Isabel","Pedro","Sofía","Diego","Valentina","Andrés","Camila"]
APELLIDOS = ["Pérez","García","López","Martínez","Rodríguez","Fernández","González","Sánchez","Torres","Ramírez","Flores","Castro","Morales","Ortiz","Silva","Rojas"]
CORREOS_DOMINIOS = ["gmail.com","outlook.com","hotmail.com"]

CATEGORIAS_PRODUCTO = [
    "Promos Fast","Express","Promociones","Sopas Power","Bowls Del Tigre","Leche de Tigre",
    "Ceviches","Fritazo","Mostrimar","Box Marino","Duos Marinos","Trios Marinos",
    "Dobles","Rondas Marinas","Mega Marino","Familiares"
]

ROLES_EMPLEADOS = ["Repartidor","Cocinero","Despachador"]
ROLES_USUARIOS = ["Cliente","Gerente","Admin"]
ESTADOS_PEDIDO = ["procesando","cocinando","empacando","enviando","recibido"]

USUARIOS_TOTAL   = int(os.getenv("USUARIOS_TOTAL", "30"))
EMPLEADOS_TOTAL  = int(os.getenv("EMPLEADOS_TOTAL", "40"))
LOCALES_TOTAL    = int(os.getenv("LOCALES_TOTAL", "3"))
PRODUCTOS_TOTAL  = int(os.getenv("PRODUCTOS_TOTAL", "60"))
PEDIDOS_TOTAL    = int(os.getenv("PEDIDOS_TOTAL", "40"))

def base_url_imagenes_desde_env() -> str:
    bucket = os.getenv("S3_BUCKET_NAME")
    region = os.getenv("AWS_REGION", "us-east-1")
    if not bucket:
        return os.getenv("BASE_URL_IMAGENES_PRODUCTOS", "https://example.com/productos")
    if "." not in bucket:
        return f"https://{bucket}.s3.amazonaws.com/productos"
    return f"https://{bucket}.s3.{region}.amazonaws.com/productos"

def generar_correo(nombre, apellido):
    base = (f"{nombre}.{apellido}".lower()
            .replace("á","a").replace("é","e").replace("í","i")
            .replace("ó","o").replace("ú","u"))
    dominio = random.choice(CORREOS_DOMINIOS)
    return f"{base}@{dominio}"

def generar_telefono():
    return f"+51 9{random.randint(10000000, 99999999)}"

def generar_slug(texto: str) -> str:
    s = texto.lower()
    for k,v in {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"}.items():
        s = s.replace(k, v)
    s = s.replace(" ", "-")
    return "".join(c for c in s if c.isalnum() or c in "-_")

def generar_locales(cantidad=None):
    cantidad = cantidad or LOCALES_TOTAL
    locales = []
    for i in range(1, cantidad + 1):
        local_id = f"LOCAL-{i:03d}"
        hora_apertura = f"{random.randint(9, 11):02d}:00"
        hora_finalizacion = f"{random.randint(20, 23):02d}:00"
        nombre_gerente = f"{random.choice(NOMBRES)} {random.choice(APELLIDOS)}"
        correo_gerente = generar_correo(*nombre_gerente.split())
        gerente = {"nombre": nombre_gerente, "correo": correo_gerente, "contrasena": f"ger_{uuid.uuid4().hex[:8]}"}
        locales.append({
            "local_id": local_id,
            "direccion": f"Av. Ejemplo {i*100}, Ciudad {i}",
            "telefono": generar_telefono(),
            "hora_apertura": hora_apertura,
            "hora_finalizacion": hora_finalizacion,
            "gerente": gerente
        })
    return locales

def generar_usuarios(locales, cantidad=None):
    """Cumple exactamente el schema de Usuarios (additionalProperties=false)."""
    cantidad = max(1, cantidad or USUARIOS_TOTAL)
    usuarios = []
    correos_usados = set()

    # Admin
    admin = {"nombre": "Administrador General", "correo": "admin@200millas.com", "contrasena": "admin123", "role": "Admin"}
    usuarios.append(admin); correos_usados.add(admin["correo"])

    # Gerentes (uno por local)
    for local in locales:
        g = local["gerente"]
        if g["correo"] in correos_usados:
            continue
        usuarios.append({
            "nombre": g["nombre"],
            "correo": g["correo"],
            "contrasena": g["contrasena"],
            "role": "Gerente"
        })
        correos_usados.add(g["correo"])

    # Clientes (sin props extra)
    while len(usuarios) < cantidad:
        nombre = random.choice(NOMBRES); apellido = random.choice(APELLIDOS)
        correo = generar_correo(nombre, apellido)
        if correo in correos_usados: 
            continue
        usuario = {
            "nombre": f"{nombre} {apellido}",
            "correo": correo,
            "contrasena": f"cli_{uuid.uuid4().hex[:10]}",
            "role": "Cliente"
        }
        usuarios.append(usuario)
        correos_usados.add(correo)

    return usuarios

def generar_empleados(locales, cantidad=None):
    cantidad = max(1, cantidad or EMPLEADOS_TOTAL)
    empleados = []
    for _ in range(cantidad):
        local = random.choice(locales)
        nombre = random.choice(NOMBRES); apellido = random.choice(APELLIDOS)
        empleados.append({
            "local_id": local["local_id"],
            "dni": f"{random.randint(10_000_000, 99_999_999)}",
            "nombre": nombre,
            "apellido": apellido,
            "role": random.choice(ROLES_EMPLEADOS)
        })
    return empleados

def generar_productos(locales, cantidad=None):
    cantidad = max(1, cantidad or PRODUCTOS_TOTAL)
    productos = []
    BASE_URL_IMAGENES = base_url_imagenes_desde_env()
    for i in range(cantidad):
        local = random.choice(locales)
        categoria = random.choice(CATEGORIAS_PRODUCTO)
        nombre = f"{categoria} {i+1}"
        producto_id = str(uuid.uuid4())  # UUID único
        slug = generar_slug(nombre)
        imagen_url = f"{BASE_URL_IMAGENES}/{local['local_id'].lower()}/{slug}.jpg"
        productos.append({
            "local_id": local["local_id"],
            "producto_id": producto_id,  # UUID
            "nombre": nombre,
            "precio": round(random.uniform(15, 80), 2),
            "descripcion": f"Delicioso plato de la categoría {categoria}",
            "categoria": categoria,
            "stock": random.randint(0, 50),
            "imagen_url": imagen_url
        })
    return productos

def generar_pedidos_y_historial(locales, usuarios, productos, cantidad=None):
    """
    Pedidos con nueva estructura:
    - PK: local_id (cambió de tenant_id)
    - SK: pedido_id
    - tenant_id_usuario: para GSI by_usuario_v2
    - created_at: timestamp de creación
    - productos[].producto_id: en lugar de nombre
    """
    cantidad = max(1, cantidad or PEDIDOS_TOTAL)
    pedidos, historial_estados = [], []

    clientes = [u for u in usuarios if u["role"] == "Cliente"]
    productos_por_local = {
        local["local_id"]: [p for p in productos if p["local_id"] == local["local_id"]]
        for local in locales
    }

    for _ in range(cantidad):
        local = random.choice(locales)
        local_id = local["local_id"]
        cliente = random.choice(clientes)
        productos_local = productos_por_local.get(local_id, [])
        if not productos_local:
            continue

        num_items = random.randint(1, 4)
        items = random.sample(productos_local, k=min(num_items, len(productos_local)))
        productos_pedido, costo = [], 0.0
        for prod in items:
            cant = random.randint(1, 3)
            # Usar producto_id (combinación de local_id#nombre)
            producto_id = f"{prod['local_id']}#{prod['nombre']}"
            productos_pedido.append({"producto_id": producto_id, "cantidad": cant})
            costo += prod["precio"] * cant

        ahora = datetime.now()
        inicio = ahora - timedelta(minutes=random.randint(5, 90))
        created_at = inicio.isoformat()

        estados_posibles = ESTADOS_PEDIDO.copy()
        ultimo_estado = random.choice(estados_posibles)
        idx_final = estados_posibles.index(ultimo_estado)
        secuencia = estados_posibles[: idx_final + 1]

        pedido_id = str(uuid.uuid4())
        t_actual = inicio
        for estado in secuencia:
            dur = random.randint(2, 15)
            t_fin = t_actual + timedelta(minutes=dur)
            historial_estados.append({
                "estado_id": str(uuid.uuid4()),
                "pedido_id": pedido_id,
                "estado": estado,
                "hora_inicio": t_actual.isoformat(),
                "hora_fin": t_fin.isoformat()
            })
            t_actual = t_fin

        # Nuevo formato de pedido
        pedido = {
            "local_id": local_id,                                    # PK (cambió de tenant_id)
            "pedido_id": pedido_id,                                  # SK
            "correo": cliente['correo'],                             # GSI by_usuario_v2 (solo correo)
            "productos": productos_pedido,                           # Ahora usa producto_id
            "costo": round(costo, 2),
            "direccion": f"Calle {random.randint(1,200)} #{random.randint(100,999)}",
            "estado": ultimo_estado,
            "created_at": created_at                                 # Nuevo campo requerido
        }

        pedidos.append(pedido)

    return pedidos, historial_estados

def validar_con_esquema(datos, nombre_esquema):
    try:
        with open(SCHEMAS_DIR / f"{nombre_esquema}.json", "r", encoding="utf-8") as f:
            esquema = json.load(f)
        required = esquema.get("required", [])
        for item in datos:
            for campo in required:
                if campo not in item:
                    print(f"⚠️ Falta campo requerido '{campo}' en {nombre_esquema}")
                    return False
        print(f"✅ Datos de {nombre_esquema} pasan validación básica (required)")
        return True
    except Exception as e:
        print(f"❌ Error al validar {nombre_esquema}: {e}")
        return False

def guardar_json(datos, nombre_archivo):
    OUTPUT_DIR.mkdir(exist_ok=True)
    ruta = OUTPUT_DIR / nombre_archivo
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=2, ensure_ascii=False)
    print(f"📝 Generado: {ruta} ({len(datos)} registros)")

def main():
    print("=" * 60)
    print("🚀 GENERADOR DE DATOS - DELIVERY")
    print("=" * 60)
    print()

    print("📊 Generando locales...")
    locales = generar_locales()
    validar_con_esquema(locales, "locales")
    guardar_json(locales, "locales.json"); print()

    print("📊 Generando usuarios...")
    usuarios = generar_usuarios(locales)
    validar_con_esquema(usuarios, "usuarios")
    guardar_json(usuarios, "usuarios.json"); print()

    print("📊 Generando empleados...")
    empleados = generar_empleados(locales)
    validar_con_esquema(empleados, "empleados")
    guardar_json(empleados, "empleados.json"); print()

    print("📊 Generando productos...")
    productos = generar_productos(locales)
    validar_con_esquema(productos, "productos")
    guardar_json(productos, "productos.json"); print()

    print("📊 Generando pedidos e historial de estados...")
    pedidos, historial_estados = generar_pedidos_y_historial(locales, usuarios, productos)
    validar_con_esquema(pedidos, "pedidos")
    guardar_json(pedidos, "pedidos.json"); print()

    validar_con_esquema(historial_estados, "historial_estados")
    guardar_json(historial_estados, "historial_estados.json"); print()

    print("=" * 60)
    print("✨ Generación completada exitosamente")
    print(f"📂 Archivos guardados en: {OUTPUT_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
