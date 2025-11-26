# 🚀 Guía Rápida - Analytics

## 🔧 Solución Rápida a Problemas Comunes

### Problema: "COLUMN_NOT_FOUND" o datos aparecen como arrays

Si ves errores como `COLUMN_NOT_FOUND: line X:X: Column 'local_id' cannot be resolved` o las queries devuelven arrays en lugar de filas individuales, ejecuta:

```bash
cd analytics
bash fix_and_reexport.sh
```

Esto:
1. Limpia los datos antiguos en S3
2. Recrea las tablas de Glue con el schema correcto
3. Re-exporta los datos en formato JSON Lines (correcto para Athena)
4. Espera a que los crawlers procesen

**Tiempo estimado:** 2-3 minutos

---

## Flujo de Trabajo

### 1️⃣ Exportar Datos (Manual o Automático)

#### ✅ Opción A: Exportación Manual via API
```bash
curl -X POST https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/export
```

**Ventajas:**
- ✅ Fácil de usar desde cualquier lugar
- ✅ Respuesta inmediata con detalles
- ✅ Inicia automáticamente los crawlers
- ✅ No requiere AWS CLI configurado

#### ✅ Opción B: Exportación Automática (Programada)

**Para habilitar:**
1. Editar `analytics/serverless.yml`
2. Buscar la sección `schedule` en `ExportDynamoDBToS3`
3. Cambiar `enabled: false` a `enabled: true`
4. Redesplegar: `serverless deploy`

```yaml
- schedule:
    rate: cron(0 2 * * ? *)  # 2 AM diaria
    enabled: true  # ← Cambiar aquí
```

**Ventajas:**
- ✅ Datos siempre actualizados
- ✅ No requiere intervención manual
- ✅ Ejecuta a las 2 AM (hora de bajo tráfico)

### 2️⃣ Esperar Crawlers (1-2 minutos)

Los crawlers se inician automáticamente después de la exportación y:
- Escanean los archivos JSON en S3
- Detectan el esquema automáticamente
- Crean/actualizan las tablas en Glue

**Verificar estado:**
```bash
aws glue get-crawler --name millas-pedidos-crawler --query 'Crawler.State'
aws glue get-crawler --name millas-historial-crawler --query 'Crawler.State'
```

### 3️⃣ Consultar Analytics

Una vez que los crawlers terminan, puedes consultar los endpoints:

```bash
# Total de pedidos por local
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/pedidos-por-local

# Ganancias por local
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/ganancias-por-local

# Tiempo de pedido
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/tiempo-pedido

# Promedio por estado
curl https://your-api-id.execute-api.us-east-1.amazonaws.com/analytics/promedio-por-estado
```

## 📊 Ejemplo Completo

### Paso 1: Exportar datos
```bash
curl -X POST https://abc123.execute-api.us-east-1.amazonaws.com/analytics/export
```

**Respuesta:**
```json
{
  "message": "Exportación completada exitosamente",
  "duration_seconds": 12.5,
  "exports": {
    "pedidos": {
      "total_items": 150,
      "crawler_started": true
    },
    "historial_estados": {
      "total_items": 450,
      "crawler_started": true
    }
  }
}
```

### Paso 2: Esperar 1-2 minutos ⏳

### Paso 3: Consultar analytics
```bash
curl https://abc123.execute-api.us-east-1.amazonaws.com/analytics/ganancias-por-local
```

**Respuesta:**
```json
{
  "query": "Ganancias totales por local",
  "data": [
    {
      "local_id": "LOCAL-001",
      "total_pedidos": 150,
      "ganancias_totales": 4500.50,
      "ganancia_promedio": 30.00
    }
  ]
}
```

## 🔄 Frecuencia Recomendada

### Exportación Manual
- **Desarrollo**: Cada vez que cambien los datos
- **Testing**: Antes de cada prueba de analytics
- **Demo**: Antes de mostrar los dashboards

### Exportación Automática
- **Producción**: Diaria a las 2 AM
- **Staging**: Diaria a las 3 AM
- **Desarrollo**: Deshabilitada (manual)

## 🛠️ Troubleshooting

### ❌ Error: "Table not found"
**Causa**: Los crawlers no han terminado o fallaron

**Solución:**
```bash
# Verificar estado
aws glue get-crawler --name millas-pedidos-crawler

# Reiniciar crawler
aws glue start-crawler --name millas-pedidos-crawler
```

### ❌ Error: "No data"
**Causa**: No hay datos en DynamoDB o la exportación falló

**Solución:**
1. Verificar que hay datos en DynamoDB
2. Ejecutar exportación nuevamente
3. Verificar archivos en S3:
```bash
aws s3 ls s3://bucket-analytic-{account-id}/pedidos/
aws s3 ls s3://bucket-analytic-{account-id}/historial_estados/
```

### ❌ Error: "Query timeout"
**Causa**: Query muy compleja o muchos datos

**Solución:**
- Esperar y reintentar
- Los resultados se cachean en S3
- Consultas subsecuentes serán más rápidas

## 💰 Costos Estimados

### S3
- **Almacenamiento**: ~$0.023 por GB/mes
- **Estimado**: <$1/mes para 10,000 pedidos

### Glue Crawlers
- **Costo**: $0.44 por hora de DPU
- **Duración**: ~1 minuto por crawler
- **Estimado**: <$0.02 por ejecución

### Athena
- **Costo**: $5 por TB escaneado
- **Estimado**: <$0.01 por query (datos pequeños)

### Lambda
- **Costo**: Incluido en free tier
- **Estimado**: $0 para uso normal

**Total estimado**: <$5/mes

## 📝 Checklist de Despliegue

- [ ] Desplegar analytics: `cd analytics && bash setup_analytics.sh`
- [ ] Exportar datos iniciales: `POST /analytics/export`
- [ ] Esperar crawlers (1-2 min)
- [ ] Probar queries de analytics
- [ ] (Opcional) Habilitar exportación automática
- [ ] Documentar API ID para el equipo

## 🎯 Mejores Prácticas

1. **Exportar datos regularmente** - Mantén los analytics actualizados
2. **Monitorear crawlers** - Verifica que terminen exitosamente
3. **Cachear resultados** - Athena cachea queries en S3
4. **Usar filtros** - Reduce costos limitando datos escaneados
5. **Revisar logs** - CloudWatch tiene logs de todas las funciones

## 📞 Soporte

Si tienes problemas:
1. Revisar logs en CloudWatch
2. Verificar permisos de LabRole
3. Consultar README.md para más detalles
4. Revisar la documentación de AWS Glue/Athena
