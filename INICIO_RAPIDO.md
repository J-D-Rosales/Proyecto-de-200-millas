# 🚀 Inicio Rápido - 200 Millas

Guía rápida para desplegar el sistema en menos de 10 minutos.

## Requisitos Previos

```bash
# 1. Verificar AWS CLI
aws --version

# 2. Verificar Serverless Framework
sls --version

# 3. Verificar Python
python3 --version
```

Si falta alguno:
- **AWS CLI**: https://aws.amazon.com/cli/
- **Serverless**: `npm install -g serverless`
- **Python 3**: https://www.python.org/downloads/

## Configuración (2 minutos)

### 1. Configurar AWS

```bash
aws configure
```

Ingresa:
- AWS Access Key ID
- AWS Secret Access Key
- Default region: `us-east-1`
- Default output format: `json`

### 2. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus valores
nano .env  # o usa tu editor favorito
```

**Valores mínimos requeridos:**
```bash
AWS_ACCOUNT_ID=123456789012  # Obtener con: aws sts get-caller-identity --query Account --output text
ORG_NAME=millas              # Tu organización en serverless.com
```

## Despliegue (5-7 minutos)

```bash
# Ejecutar script de setup
bash setup_backend.sh
```

Selecciona opción **1** (Desplegar todo)

El script automáticamente:
1. ✅ Crea 7 tablas DynamoDB
2. ✅ Crea buckets S3
3. ✅ Genera datos de prueba
4. ✅ Despliega 6 microservicios
5. ✅ Configura Step Functions
6. ✅ Configura EventBridge

## Verificación

### Obtener URLs de API

```bash
aws apigatewayv2 get-apis --query 'Items[].{Name:Name,Endpoint:ApiEndpoint}' --output table
```

### Probar el Sistema

1. **Importar Postman Collection**
   - Archivo: `200 Millas - API Collection COMPLETA.postman_collection.json`

2. **Registrar Usuario**
   ```bash
   curl -X POST https://TU_API_URL/users/register \
     -H "Content-Type: application/json" \
     -d '{
       "nombre": "Test User",
       "correo": "test@example.com",
       "contrasena": "password123",
       "role": "Cliente"
     }'
   ```

3. **Iniciar Sesión**
   ```bash
   curl -X POST https://TU_API_URL/users/login \
     -H "Content-Type: application/json" \
     -d '{
       "correo": "test@example.com",
       "contrasena": "password123"
     }'
   ```

4. **Crear Pedido**
   ```bash
   curl -X POST https://TU_API_URL/pedido/create \
     -H "Authorization: Bearer TU_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "tenant_id": "TENANT-001",
       "local_id": "LOCAL-001",
       "usuario_correo": "test@example.com",
       "direccion": "Av. Principal 123",
       "costo": 45.50,
       "estado": "procesando",
       "productos": [
         {
           "producto_id": "uuid-producto",
           "nombre": "Ceviche Clásico",
           "cantidad": 2,
           "precio": 22.75
         }
       ]
     }'
   ```

## Datos de Prueba

El sistema viene con datos precargados:

### Usuarios
- **Admin**: `admin@200millas.com` / `admin123`
- **Gerentes**: `gerente1@200millas.com` / `password123`
- **Clientes**: `cliente1@200millas.com` / `password123`

### Locales
- `LOCAL-001` - 200 Millas Miraflores
- `LOCAL-002` - 200 Millas San Isidro
- `LOCAL-003` - 200 Millas Barranco

### Productos
Cada local tiene 50+ productos en categorías:
- Ceviches
- Sopas Power
- Bowls Del Tigre
- Promociones
- Y más...

## Comandos Útiles

### Ver Logs
```bash
# Logs de una función específica
aws logs tail /aws/lambda/NOMBRE_FUNCION --follow

# Ejemplo: Ver logs de cambio de estado
aws logs tail /aws/lambda/service-orders-200-millas-dev-cambiarEstado --follow
```

### Ver Estado de Pedido
```bash
aws dynamodb get-item \
  --table-name Millas-Pedidos \
  --key '{"local_id":{"S":"LOCAL-001"},"pedido_id":{"S":"PEDIDO_ID"}}'
```

### Ver Historial de Pedido
```bash
aws dynamodb query \
  --table-name Millas-Historial-Estados \
  --key-condition-expression "pedido_id = :pid" \
  --expression-attribute-values '{":pid":{"S":"PEDIDO_ID"}}'
```

## Solución de Problemas

### Error: "AWS CLI no encontrado"
```bash
# Instalar AWS CLI
pip3 install awscli --upgrade --user
```

### Error: "sls: command not found"
```bash
# Instalar Serverless Framework
npm install -g serverless
```

### Error: "Falta AWS_ACCOUNT_ID en .env"
```bash
# Obtener tu Account ID
aws sts get-caller-identity --query Account --output text

# Agregar al .env
echo "AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)" >> .env
```

### Error: "Table already exists"
Si las tablas ya existen, usa la opción 4 del menú (Solo microservicios)

## Eliminar Todo

Para eliminar todos los recursos:

```bash
bash setup_backend.sh
```

Selecciona opción **2** (Eliminar todo) y confirma con `SI`

## Próximos Pasos

1. 📖 Lee el [README.md](./README.md) completo para entender la arquitectura
2. 📊 Explora el [servicio de analytics](./analytics/README.md)
3. 🔄 Revisa el [flujo de Step Functions](./stepFunction/FLUJO_CON_ERRORES.md)
4. 📮 Importa la colección de Postman para probar todos los endpoints

## Soporte

Si encuentras problemas:
1. Verifica que todas las variables en `.env` estén configuradas
2. Revisa los logs de CloudWatch
3. Consulta la documentación completa en [README.md](./README.md)

---

**¡Listo para empezar! 🎉**
