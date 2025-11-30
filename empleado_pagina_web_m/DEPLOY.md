# Guía de Despliegue - Panel de Empleado

Esta guía te muestra varias formas de desplegar y ejecutar el panel web de empleados.

---

## 🖥️ Opción 1: Servidor Local (Desarrollo)

### Método A: Usando Python (Recomendado)

```bash
# Navega a la carpeta
cd empleado_pagina_web_m

# Inicia el servidor
python3 -m http.server 8000

# O usa el script incluido
./start_server.sh
```

Abre en tu navegador: **http://localhost:8000**

### Método B: Usando Node.js

```bash
# Instala http-server (solo una vez)
npm install -g http-server

# Navega a la carpeta
cd empleado_pagina_web_m

# Inicia el servidor
http-server -p 8000
```

### Método C: Usando PHP

```bash
cd empleado_pagina_web_m
php -S localhost:8000
```

---

## ☁️ Opción 2: Desplegar en AWS S3 (Producción)

### Paso 1: Crear bucket S3

```bash
# Crea un bucket (cambia el nombre por uno único)
aws s3 mb s3://200-millas-panel-empleado

# Configura el bucket para hosting web
aws s3 website s3://200-millas-panel-empleado \
  --index-document index.html \
  --error-document index.html
```

### Paso 2: Configurar política pública

Crea un archivo `bucket-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "PublicReadGetObject",
      "Effect": "Allow",
      "Principal": "*",
      "Action": "s3:GetObject",
      "Resource": "arn:aws:s3:::200-millas-panel-empleado/*"
    }
  ]
}
```

Aplica la política:

```bash
aws s3api put-bucket-policy \
  --bucket 200-millas-panel-empleado \
  --policy file://bucket-policy.json
```

### Paso 3: Subir archivos

```bash
# Sube todos los archivos
cd empleado_pagina_web_m
aws s3 sync . s3://200-millas-panel-empleado \
  --exclude ".git/*" \
  --exclude "*.md" \
  --exclude "*.sh" \
  --cache-control "public, max-age=3600"

# Configura correctos Content-Type
aws s3 cp index.html s3://200-millas-panel-empleado/index.html \
  --content-type "text/html" \
  --cache-control "no-cache"

aws s3 cp styles.css s3://200-millas-panel-empleado/styles.css \
  --content-type "text/css"

aws s3 cp app.js s3://200-millas-panel-empleado/app.js \
  --content-type "application/javascript"

aws s3 cp config.js s3://200-millas-panel-empleado/config.js \
  --content-type "application/javascript"
```

### Paso 4: Obtener URL

```bash
# Tu sitio estará disponible en:
echo "http://200-millas-panel-empleado.s3-website-$(aws configure get region).amazonaws.com"
```

---

## 🌐 Opción 3: Desplegar en Netlify (Gratis y Fácil)

### Método A: Usando Netlify CLI

```bash
# Instala Netlify CLI (solo una vez)
npm install -g netlify-cli

# Navega a la carpeta
cd empleado_pagina_web_m

# Inicia sesión
netlify login

# Despliega
netlify deploy --prod
```

### Método B: Usando la interfaz web

1. Ve a https://app.netlify.com
2. Arrastra la carpeta `empleado_pagina_web_m` al navegador
3. ¡Listo! Obtendrás una URL como: `https://tu-app.netlify.app`

---

## 🔧 Opción 4: Desplegar en Vercel

```bash
# Instala Vercel CLI (solo una vez)
npm install -g vercel

# Navega a la carpeta
cd empleado_pagina_web_m

# Despliega
vercel --prod
```

---

## 📋 Script de Despliegue Automatizado para S3

Crea un archivo `deploy_s3.sh`:

```bash
#!/bin/bash

BUCKET_NAME="200-millas-panel-empleado"
REGION="us-east-1"

echo "🚀 Desplegando Panel de Empleado a S3..."

# Validar que AWS CLI esté configurado
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ Error: AWS CLI no está configurado"
    exit 1
fi

echo "📦 Sincronizando archivos..."
aws s3 sync . s3://$BUCKET_NAME \
  --exclude "*.md" \
  --exclude "*.sh" \
  --exclude ".git/*" \
  --delete \
  --cache-control "public, max-age=3600"

echo "🔄 Actualizando cache headers..."
aws s3 cp s3://$BUCKET_NAME/index.html s3://$BUCKET_NAME/index.html \
  --metadata-directive REPLACE \
  --content-type "text/html" \
  --cache-control "no-cache" \
  --acl public-read

echo "✅ Despliegue completado!"
echo "🌐 URL: http://$BUCKET_NAME.s3-website-$REGION.amazonaws.com"
```

---

## 🔐 Configurar CORS en tu API

Para que la página funcione, necesitas configurar CORS en tu API Gateway:

```json
{
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "Content-Type,Authorization",
  "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
}
```

O para un dominio específico:

```json
{
  "Access-Control-Allow-Origin": "https://tu-dominio.com",
  "Access-Control-Allow-Headers": "Content-Type,Authorization",
  "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
}
```

---

## ⚙️ Checklist Antes de Desplegar

- [ ] Configurar URLs en `config.js`
- [ ] Probar localmente con el servidor de desarrollo
- [ ] Verificar que la API responda correctamente
- [ ] Configurar CORS en la API
- [ ] Probar login y carga de pedidos
- [ ] Probar actualización de estados
- [ ] Verificar en diferentes navegadores
- [ ] Probar en dispositivos móviles

---

## 🆘 Problemas Comunes

### Error de CORS
**Problema:** "Access-Control-Allow-Origin" error
**Solución:** Configura CORS en tu API Gateway de AWS

### Los archivos no cargan
**Problema:** 404 en archivos CSS/JS
**Solución:** Verifica que todos los archivos estén en la misma carpeta

### La API no responde
**Problema:** Network error o timeout
**Solución:** Verifica que la URL en `config.js` sea correcta

---

## 📊 Comparación de Opciones

| Opción | Costo | Dificultad | Velocidad | Mejor para |
|--------|-------|------------|-----------|------------|
| Local (Python) | Gratis | Muy fácil | Inmediato | Desarrollo |
| AWS S3 | ~$0.50/mes | Media | Rápido | Producción |
| Netlify | Gratis | Fácil | Muy rápido | Prototipo/Producción |
| Vercel | Gratis | Fácil | Muy rápido | Prototipo/Producción |

---

## 🎯 Recomendación

- **Para desarrollo local:** Usa el script `start_server.sh` o Python
- **Para producción rápida:** Usa Netlify (drag & drop)
- **Para integración con AWS:** Usa S3 con tu infraestructura existente

¡Elige la opción que mejor se adapte a tus necesidades! 🚀
