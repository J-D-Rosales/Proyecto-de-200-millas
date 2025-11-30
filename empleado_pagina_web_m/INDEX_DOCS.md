# 📚 Documentación - Sistema 200 Millas

## 🚀 Inicio

```bash
./test_local.sh
```
Abre http://localhost:8080

## 📖 Documentación

- **[README_API.md](README_API.md)** - Guía completa
- **[DEPLOY.md](DEPLOY.md)** - Despliegue en producción

## 🎯 Uso Rápido

1. **Registrarse**: Nombre, email, contraseña, rol
2. **Login**: Email y contraseña  
3. **Gerente**: Ve analytics del local
4. **Empleado**: Gestiona pedidos

## 🔗 APIs Integradas

- ✅ Registro/Login: `users/register`, `users/login`
- ✅ Estados pedidos: `empleados/cocina/*`, `empleados/delivery/*`
- ✅ Analytics: `analytics/pedidos-por-local`, `analytics/ganancias-por-local`

## ⚠️ Nota

Los pedidos en el grid son mock (no existe endpoint para listarlos).
Los cambios de estado SÍ van a la API real.
