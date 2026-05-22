# Guía de Despliegue Manual en Azure — SmartBus Unillanos

Esta guía contiene los pasos detallados y comandos exactos para desplegar la arquitectura completa de **SmartBus Unillanos** en la nube de Microsoft Azure utilizando el **Azure CLI** y el Portal de Azure.

---

## 📋 Arquitectura de Despliegue

```
                      ┌─────────────────────────────────────────┐
                      │             Microsoft Azure             │
                      │                                         │
    Usuario           │  ┌──────────────────────────────────┐   │
    (Navegador) ──────┼─►│      Azure Static Web Apps       │   │
                      │  │      (Frontend en React)         │   │
                      │  └──────────────┬───────────────────┘   │
                      │                 │ HTTPS (URLs Absolutas) │
                      │  ┌──────────────▼───────────────────┐   │
                      │  │      Azure Container Apps        │   │
                      │  │                                   │   │
                      │  │  ┌─────────────┐ ┌─────────────┐ │   │
                      │  │  │    auth     │ │  trip-log   │ │   │
                      │  │  │  (.NET 10)  │ │  (FastAPI)  │ │   │
                      │  │  └─────────────┘ └──────┬──────┘ │   │
                      │  └─────────────────────────┼────────┘   │
                      │                            │            │
                      │  ┌─────────────────────────▼────────┐   │
                      │  │  Azure Database for PostgreSQL   │   │
                      │  │  Flexible Server (Capa Gratis)   │   │
                      │  └──────────────────────────────────┘   │
                      └─────────────────────────────────────────┘
```

---

## 🛠️ Requisitos Previos

1. **Instalar Azure CLI** en tu máquina local.
2. **Instalar Docker** (asegúrate de que Docker Desktop esté iniciado).
3. Una cuenta de **Docker Hub** (gratuita) para subir las imágenes de contenedor.
4. Tu proyecto de **SmartBus Unillanos** subido a un repositorio público o privado en **GitHub**.

---

## Paso 1: Compilar y Subir Imágenes a Docker Hub

El servicio de autenticación (`auth`) y el microservicio de registro de viajes (`trip-log`) se empaquetarán como contenedores y se subirán a Docker Hub.

1. Abre tu terminal y haz login en Docker Hub:
   ```bash
   docker login
   ```
   *Ingresa tu usuario y contraseña de Docker Hub.*

2. Compilar y subir la imagen del **Servicio de Autenticación (.NET 10)**:
   > [!IMPORTANT]
   > Ejecuta los siguientes comandos desde la carpeta raíz del proyecto (`SmartBus-Unillanos`).
   
   ```bash
   # Reemplaza <tu_usuario_docker> con tu nombre de usuario de Docker Hub
   docker build -t <tu_usuario_docker>/smartbus-auth:latest -f Dockerfile.auth .
   
   # Subir la imagen
   docker push <tu_usuario_docker>/smartbus-auth:latest
   ```

3. Compilar y subir la imagen del **Microservicio de Viajes (FastAPI)**:
   ```bash
   # Compilar desde la raíz del proyecto usando el directorio del servicio
   docker build -t <tu_usuario_docker>/smartbus-trip-log:latest ./trip-log-service
   
   # Subir la imagen
   docker push <tu_usuario_docker>/smartbus-trip-log:latest
   ```

---

## Paso 2: Iniciar Sesión en Azure CLI y Crear Recursos Básicos

1. Inicia sesión en tu cuenta de Azure (si utilizas créditos de estudiante, asegúrate de iniciar sesión con ese correo):
   ```bash
   az login
   ```

2. Registrar los proveedores de Azure Container Apps (si no los tienes registrados):
   ```bash
   az provider register --namespace Microsoft.App
   az provider register --namespace Microsoft.OperationalInsights
   ```

3. Crear un **Grupo de Recursos** (Resource Group) donde vivirá toda nuestra infraestructura:
   ```bash
   az group create --name SmartBus-RG --location eastus
   ```

---

## Paso 3: Crear Azure Database for PostgreSQL

Desplegaremos un servidor administrado de PostgreSQL utilizando la capa gratuita (B1ms burstable) para garantizar la persistencia real de los datos.

1. Crear el servidor PostgreSQL Flexible Server:
   > [!WARNING]
   > - Cambia `<tu_password_segura>` por una contraseña que recuerdes.
   > - El nombre del servidor (`--name`) debe ser **globalmente único** en todo Azure. Te sugerimos cambiar `smartbus-db-server` por algo como `smartbus-db-server-<tu_nombre>` o similar. Anota el nombre del servidor generado.
   
   ```bash
   az postgres flexible-server create \
     --resource-group SmartBus-RG \
     --name smartbus-db-server-<tu_nombre_unico> \
     --admin-user smartbus \
     --admin-password <tu_password_segura> \
     --sku-name Standard_B1ms \
     --tier Burstable \
     --public-access 0.0.0.0 \
     --database-name smartbus \
     --active-directory-auth Disabled \
     --location eastus
   ```

2. Permitir el tráfico entrante de los servicios de Azure (abrir el firewall de Postgres a las IPs internas de Azure):
   ```bash
   az postgres flexible-server firewall-rule create \
     --resource-group SmartBus-RG \
     --name smartbus-db-server \
     --rule-name AllowAllAzureIPs \
     --start-ip-address 0.0.0.0 \
     --end-ip-address 0.0.0.0
   ```

---

## Paso 4: Crear y Desplegar los Microservicios en Azure Container Apps

1. Crear el **Entorno de Container Apps** (Container Apps Environment):
   ```bash
   az containerapp env create \
     --name smartbus-env \
     --resource-group SmartBus-RG \
     --location eastus
   ```

2. Desplegar el **Servicio de Autenticación (`auth`)**:
   > [!NOTE]
   > Recuerda reemplazar `<tu_usuario_docker>` con tu usuario de Docker Hub.
   
   ```bash
   az containerapp create \
     --name smartbus-auth \
     --resource-group SmartBus-RG \
     --environment smartbus-env \
     --image <tu_usuario_docker>/smartbus-auth:latest \
     --target-port 5000 \
     --ingress external \
     --query properties.configuration.ingress.fqdn
   ```
   *Copia la URL (FQDN) que se imprime al final del comando. Tendrá un formato similar a: `https://smartbus-auth.gentleriver-abc12345.eastus.azurecontainerapps.io`.*

3. **Habilitar CORS en el Ingress del Servicio Auth:**
   Dado que el backend de autenticación en C# no implementa CORS en el código y será consumido directamente desde el navegador (en el dominio de Static Web Apps), habilitamos CORS a nivel de la capa de red del Container App:
   
   ```bash
   az containerapp ingress cors enable \
     --name smartbus-auth \
     --resource-group SmartBus-RG \
     --allowed-origins "*" \
     --allowed-methods "GET" "POST" "OPTIONS" \
     --allowed-headers "*"
   ```

4. Desplegar el **Microservicio de Viajes (`trip-log`)**:
   > [!IMPORTANT]
   > - Cambia `<tu_password_segura>` por la contraseña de PostgreSQL configurada en el Paso 3.
   > - Configura tu `GROQ_API_KEY` real para permitir el análisis inteligente.
   
   ```bash
   az containerapp create \
     --name smartbus-trips \
     --resource-group SmartBus-RG \
     --environment smartbus-env \
     --image <tu_usuario_docker>/smartbus-trip-log:latest \
     --target-port 8000 \
     --ingress external \
     --env-vars \
       DATABASE_URL="postgresql+asyncpg://smartbus:<tu_password_segura>@smartbus-db-server-<tu_nombre_unico>.postgres.database.azure.com:5432/smartbus" \
       GROQ_API_KEY="gsk_your_groq_api_key_here" \
       JWT_SECRET="THIS_IS_A_DEMO_KEY_CHANGE_IT_123456789" \
       JWT_ISSUER="MiniIdentityApi" \
       JWT_AUDIENCE="MiniIdentityApiUsers" \
     --query properties.configuration.ingress.fqdn
   ```
   *Copia la URL (FQDN) generada para el servicio de viajes. Ejemplo: `https://smartbus-trips.gentleriver-abc12345.eastus.azurecontainerapps.io`.*

---

## Paso 5: Desplegar el Frontend en Azure Static Web Apps

El frontend en React se desplegará utilizando **Azure Static Web Apps**, el cual compilará automáticamente el proyecto directamente desde tu repositorio de GitHub cada vez que hagas un push.

1. **Crear la Static Web App desde el portal de Azure o mediante el CLI:**
   ```bash
   # Recuerda cambiar <usuario_github> y <repositorio_github> por tu repo real
   az staticwebapp create \
     --name smartbus-frontend \
     --resource-group SmartBus-RG \
     --source https://github.com/<usuario_github>/<repositorio_github> \
     --branch main \
     --location eastus2 \
     --app-location "/frontend" \
     --output-location "dist" \
     --login-with-github
   ```
   *Este comando abrirá tu navegador para autorizar a Azure a acceder a tu cuenta de GitHub y creará un archivo de GitHub Actions workflow en tu repositorio.*

2. **Configurar las variables de entorno de compilación (Vite Env Vars):**
   Vite requiere inyectar las URLs absolutas de los contenedores de Azure en tiempo de compilación. Por ello, debemos agregarlas al archivo de Workflow generado por Azure en tu repositorio de GitHub:
   
   A. Ve a tu repositorio en GitHub y abre el archivo `.github/workflows/azure-static-web-apps-*.yml`.
   B. Ubica la sección `with:` dentro del paso de despliegue (`build_and_deploy_job`).
   C. Añade una clave `env` al paso de compilación con las URLs de tus Container Apps:
   
   ```yaml
         - name: Build And Deploy
           id: builddeploy
           uses: Azure/static-web-apps-deploy@v1
           with:
             azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
             repo_token: ${{ secrets.GITHUB_TOKEN }}
             action: "upload"
             ###### Configuración del Directorio ######
             app_location: "/frontend"
             api_location: ""
             output_location: "dist"
           ###### Añade esta sección env debajo de 'with' ######
           env:
             VITE_AUTH_BASE_URL: "https://smartbus-auth.<tu-sufijo>.eastus.azurecontainerapps.io/api"
             VITE_TRIP_LOG_BASE_URL: "https://smartbus-trips.<tu-sufijo>.eastus.azurecontainerapps.io"
   ```
   
   D. Guarda y haz un `git commit` y `git push` de este cambio a tu rama `main`.
   E. GitHub Actions iniciará automáticamente una nueva compilación y en un par de minutos tu frontend estará activo con las URLs correctas.

3. **Verificar el dominio público del frontend:**
   Obtén la URL pública de tu frontend en React:
   ```bash
   az staticwebapp show --name smartbus-frontend --query defaultHostname --output tsv
   ```
   *Verás una dirección similar a: `white-sea-0123456.azurestaticapps.net`.*

---

## Paso 6: Verificación E2E en la Nube 🚀

Ahora que todos los componentes están desplegados y conectados, realiza las siguientes acciones en tu navegador:

1. **Registro Inicial**:
   Utiliza Postman o `curl` para registrar al menos un usuario administrador en el microservicio de autenticación en la nube:
   ```bash
   curl -X POST "https://smartbus-auth.<tu-sufijo>.eastus.azurecontainerapps.io/api/auth/register" \
     -H "Content-Type: application/json" \
     -d '{"username": "conductor1", "email": "conductor@unillanos.edu.co", "password": "Password123*"}'
   ```

2. **Inicio de Sesión**:
   - Abre la URL de tu **Azure Static Web App** (ej. `https://white-sea-*.azurestaticapps.net`).
   - Ingresa las credenciales (`conductor1` / `Password123*`).
   - Iniciará sesión correctamente, te redirigirá al Dashboard y cargará la tarjeta de la **Ruta Parque**.

3. **Registrar un Viaje (ML context)**:
   - Haz clic en **"Registrar Viaje"**.
   - Diligencia los campos: pasajeros, ID del bus, clima (**Soleado**), semana académica (**Semana 8 — Parciales**) y activa la casilla **"Hay evento especial hoy"**.
   - Envía el formulario. Te redirigirá al Historial y verás el registro en la tabla.

4. **Análisis Inteligente de Demanda (IA Groq)**:
   - Vuelve al Dashboard.
   - Presiona el botón de gradiente violeta **"Generar análisis de demanda"**.
   - El microservicio de viajes consultará los datos reales de PostgreSQL, construirá el prompt (limitado a los 30 viajes más recientes) y llamará al modelo `llama-3.1-8b-instant` en Groq.
   - En segundos, verás el análisis en español dentro de la tarjeta con borde animado.
