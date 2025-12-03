# AWS Infrastructure Deployment Script

Este script automatiza el despliegue de una infraestructura web en AWS que incluye:
- Una instancia EC2 con servidor web Apache y PHP
- Una base de datos RDS (MariaDB)
- Un bucket S3 para almacenamiento de archivos estáticos
- Configuración de seguridad con Security Groups

## Requisitos Previos

1. **Credenciales de AWS** configuradas en `~/.aws/credentials`
2. **Python 3.6 o superior**
3. **Bibliotecas de Python requeridas**:
   - boto3
   - botocore

## Configuración

Antes de ejecutar el script, asegúrate de tener:

1. Un archivo `archivos/password.txt` con la contraseña para la base de datos
2. Los archivos de la aplicación web en el directorio `archivos/`

## Estructura del Proyecto

```
python/
├── deploy_full_infra.py  # Script principal de despliegue
├── archivos/
│   ├── index.php        # Página principal de la aplicación
│   ├── init_db.sql      # Script de inicialización de la base de datos
│   └── password.txt     # Contraseña para la base de datos (no incluido en control de versiones)
└── README.md            # Este archivo
```

## Recursos Creados

El script crea los siguientes recursos en AWS:

- **EC2 Instance**:
  - Tipo: t3.micro
  - AMI: Amazon Linux 2
  - Servicios: Apache, PHP 8.2, MySQL Client

- **RDS (MariaDB)**:
  - Motor: MariaDB 10.5.28
  - Clase: db.t3.micro
  - Almacenamiento: 20GB

- **S3 Bucket**:
  - Nombre: app-bancoriendo
  - Contenido: Archivos estáticos de la aplicación web

- **Security Groups**:
  - SG1_Puerto80_Publico: Permite tráfico HTTP (puerto 80) desde cualquier origen
  - SG2_SoloDesdeSG1: Permite tráfico MySQL (puerto 3306) solo desde SG1

## Uso

1. Clonar el repositorio:
   ```bash
   git clone <repositorio>
   cd obligatorio-prog-devops/python
   ```

2. Crea el archivo de contraseña:
   ```bash
   mkdir -p archivos
   echo "tu_contraseña_segura" > archivos/password.txt
   ```

3. Instala las dependencias:
   ```bash
   pip install boto3 botocore
   ```

4. Ejecuta el script:
   ```bash
   python3 deploy_full_infra.py
   ```

5. Una vez completado, el script mostrará la IP pública de la instancia EC2.

## Notas Importantes

- Este script crea recursos en AWS que pueden generar costos.
- Asegúrate de eliminar los recursos cuando ya no los necesites.
- El bucket S3 debe tener un nombre único a nivel global.
- La instancia RDS tarda varios minutos en estar disponible.

## Seguridad

- Nunca subas archivos de contraseñas al control de versiones.
- Asegúrate de que los Security Groups estén correctamente configurados.
- Considera usar AWS Secrets Manager para manejar credenciales en producción.

## Solución de Problemas

- **Error de permisos**: Verifica que las credenciales de AWS estén configuradas correctamente.
- **Error de región**: Asegúrate de que la región especificada sea válida.
- **Tiempo de espera**: Algunas operaciones como la creación de RDS pueden tardar varios minutos.

