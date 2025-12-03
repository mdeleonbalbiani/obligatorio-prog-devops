# Proyecto de Automatización DevOps

Este repositorio contiene herramientas de automatización para despliegue de infraestructura y gestión de usuarios en entornos Linux.

## Estructura del Proyecto

```
.
├── bash/               # Scripts de administración de sistema
│   ├── ej1_crea_usuarios.sh  # Script para creación masiva de usuarios
│   └── README.md            # Documentación de scripts bash
│
└── python/             # Automatización de infraestructura AWS
    ├── deploy_full_infra.py  # Script de despliegue en AWS
    ├── archivos/             # Archivos de la aplicación web
    └── README.md             # Documentación de despliegue AWS
```

## Módulos Principales

### 1. Scripts de Administración (bash/)

Herramientas para la gestión de usuarios en sistemas Linux:
- Creación masiva de usuarios desde archivo de configuración
- Personalización de directorios home y shells
- Configuración de permisos y seguridad básica

**Documentación detallada:** [bash/README.md](bash/README.md)

### 2. Infraestructura en AWS (python/)

Automatización del despliegue de una infraestructura web completa en AWS que incluye:
- Instancia EC2 con Apache y PHP
- Base de datos RDS (MariaDB)
- Almacenamiento S3 para archivos estáticos
- Configuración de seguridad con Security Groups

**Documentación detallada:** [python/README.md](python/README.md)

## Requisitos Previos

- **Para scripts bash**:
  - Sistema operativo Linux
  - Permisos de superusuario (root)
  - Bash 4.0 o superior

- **Para scripts Python**:
  - Python 3.6 o superior
  - Cuenta de AWS con credenciales configuradas
  - Paquetes Python: boto3, botocore

## Cómo Empezar

1. Clonar el repositorio:
   ```bash
   git clone <repositorio>
   cd obligatorio-prog-devops
   ```

2. Seguir las instrucciones específicas de cada módulo:
   - [bash/README.md](bash/README.md) para gestión de usuarios
   - [python/README.md](python/README.md) para despliegue en AWS

## Consideraciones de Seguridad

- Nunca subas credenciales o contraseñas al control de versiones
- Revisa y ajusta los permisos de los scripts antes de ejecutarlos
- Las instancias de AWS pueden generar costos, asegúrate de detener o eliminar los recursos cuando no los necesites