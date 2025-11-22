### Proyecto 200 Millas

Este documento proporciona una descripción general del proyecto **200_millas** y explica cómo usar los servicios incluidos en la colección de Postman proporcionada. El proyecto utiliza una arquitectura sin servidor (serverless) para desplegar los servicios y ofrece funcionalidades básicas para la gestión de usuarios, empleados y productos.

### Servicios Disponibles

El proyecto consta de tres servicios:

1. **Usuarios**
   El servicio "Usuarios" gestiona el registro y el inicio de sesión de los usuarios.

   * **Registrar Usuario**: Este endpoint permite registrar un nuevo usuario.

     * **Método**: POST
     * **URL**: `https://5u1x1lmc46.execute-api.us-east-1.amazonaws.com/users/register`
     * **Cuerpo de la solicitud**:

       ```json
       {
         "tenant_id": "200millas",
         "user_id": "yaritza@elmer.com",
         "password": "123456"
       }
       ```
   * **Iniciar sesión Usuario**: Este endpoint permite iniciar sesión con un usuario ya registrado.

     * **Método**: POST
     * **URL**: `https://5u1x1lmc46.execute-api.us-east-1.amazonaws.com/users/login`
     * **Cuerpo de la solicitud**:

       ```json
       {
         "tenant_id": "200millas",
         "user_id": "yaritza@elmer.com",
         "password": "123456"
       }
       ```

2. **Productos**
   El servicio "Productos" gestiona la creación, actualización, listado y eliminación de productos.

   * **Crear Producto**: Este endpoint permite crear un nuevo producto y sube su imagen en S3. Además, necesita el token del employee.

     * **Método**: POST
     * **URL**: `https://9qyel2o126.execute-api.us-east-1.amazonaws.com/productos/create`
     * **Cuerpo de la solicitud**:

       ```json
       {
         "tenant_id": "restaurante_1",
         "product_id": "pro2",
         "name": "ceviche de conchas negras 2",
         "price": 40,
         "stock": 50,
         "image": {
           "key": "producto-1.png",
           "file_base64": "image_data_here"
         }
       }
       ```
   * **Actualizar Producto**: Este endpoint permite actualizar un producto existente y necesita el token del employee.

     * **Método**: PUT
     * **URL**: `https://9qyel2o126.execute-api.us-east-1.amazonaws.com/productos/update`
     * **Cuerpo de la solicitud**:

       ```json
       {
         "tenant_id": "restaurante_1",
         "product_id": "pro2",
         "name": "ceviche de conchas negras actualizado",
         "price": 40,
         "stock": 50
       }
       ```
   * **Eliminar Producto**: Este endpoint permite eliminar un producto existente y necesita el token del employee.

     * **Método**: DELETE
     * **URL**: `https://9qyel2o126.execute-api.us-east-1.amazonaws.com/productos/delete`
     * **Cuerpo de la solicitud**:

       ```json
       {
         "tenant_id": "restaurante_1",
         "product_id": "pro2"
       }
       ```
   * **Listar Productos**: Este endpoint lista los productos con paginación.

     * **Método**: POST
     * **URL**: `https://9qyel2o126.execute-api.us-east-1.amazonaws.com/productos/list`
     * **Cuerpo de la solicitud**:

       ```json
       {
         "tenant_id": "restaurante_1",
         "size": 10
       }
       ```

3. **Empleado**
   El servicio "Empleado" permite registrar e iniciar sesión con empleados.

   * **Registrar Empleado**: Este endpoint permite registrar un nuevo empleado.

     * **Método**: POST
     * **URL**: `https://lgmxqmwhz8.execute-api.us-east-1.amazonaws.com/employees/register`
     * **Cuerpo de la solicitud**:

       ```json
       {
         "tenant_id": "200millas",
         "user_id": "chef1@200millas.pe",
         "password": "Secreta123"
       }
       ```
   * **Iniciar sesión Empleado**: Este endpoint permite que un empleado inicie sesión.

     * **Método**: POST
     * **URL**: `https://lgmxqmwhz8.execute-api.us-east-1.amazonaws.com/employees/login`
     * **Cuerpo de la solicitud**:

       ```json
       {
         "tenant_id": "200millas",
         "user_id": "chef1@200millas.pe",
         "password": "Secreta123"
       }
       ```

### Despliegue sin servidor (Serverless)

El proyecto utiliza **Serverless Framework** para desplegar las funciones en un entorno sin servidor (serverless).

El archivo `serverless-compose.yml` se usa para definir la configuración del despliegue, incluyendo las funciones, los recursos y el entorno.

Para desplegar los servicios, sigue estos pasos:

1. Dirígete a la raíz del directorio del proyecto.
2. Ejecuta el siguiente comando para desplegar:

   ```bash
   sls deploy
   ```
3. Para eliminar los servicios desplegados, utiliza el siguiente comando:

   ```bash
   sls remove
   ```

Esto se encargará automáticamente de la configuración, despliegue y eliminación de los servicios en el entorno sin servidor.
