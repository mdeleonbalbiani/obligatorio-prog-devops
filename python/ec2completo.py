#!/usr/bin/python3

import boto3

AMI = 'ami-06b21ccaeff8cd686'
SECURITY_GROUP_NAME = 'SG_Banco_Riendop80'
DESCRIPTION = 'Security group para la EC2 que habilita puerto 80' 
INSTANCE_NAME = 'Banco_Riendo'

# Crear cliente EC2 con región
ec2 = boto3.client('ec2', region_name='us-east-1')

# Crear Security Group
response = ec2.create_security_group(
    GroupName=SECURITY_GROUP_NAME,
    Description=DESCRIPTION
)

sg_id = response['GroupId']
print(f"Security Group creado: {sg_id}")

# Permitir tráfico HTTP (80)
ec2.authorize_security_group_ingress(
    GroupId=sg_id,
    IpPermissions=[
        {
            'IpProtocol': 'tcp',
            'FromPort': 80,
            'ToPort': 80,
            'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
        }
    ]
)

# Crear instancia EC2
instance = ec2.run_instances(
    ImageId=AMI,
    InstanceType='t2.micro',
    SecurityGroupIds=[sg_id],
    MinCount=1,
    MaxCount=1,
    UserData=UserData="""#!/bin/bash
    # -----------------------------
    # 1) Actualizar e instalar paquetes
    # -----------------------------
    dnf clean all
    dnf makecache
    dnf -y update
    dnf -y install httpd php php-cli php-fpm php-common php-mysqlnd mariadb105 git

    systemctl enable --now httpd
    systemctl enable --now php-fpm

    # -----------------------------
    # 2) Descargar aplicación desde GitHub
    # (Reemplazar REPO_URL por tu repo)
    # -----------------------------
    cd /tmp
    git clone https://github.com/USUARIO/REPO.git app

    # Copiar archivos de la app al webroot
    mkdir -p /var/www/html
    cp -R app/* /var/www/html

    # -----------------------------
    # 3) Mover archivos fuera del webroot
    # -----------------------------
    # init_db.sql → /var/www
    mv /var/www/html/init_db.sql /var/www/

    # Crear archivo .env con las credenciales del RDS
    cat << 'EOF' > /var/www/.env
    DB_HOST=REEMPLAZAR_ENDPOINT
    DB_NAME=REEMPLAZAR_DBNAME
    DB_USER=REEMPLAZAR_USER
    DB_PASS=REEMPLAZAR_PASS

    APP_USER=admin
    APP_PASS=admin123
    EOF

    chown apache:apache /var/www/.env
    chmod 600 /var/www/.env

    # -----------------------------
    # 4) Configuración PHP-FPM para Apache (si el archivo no existe)
    # -----------------------------
    cat << 'EOF' > /etc/httpd/conf.d/php-fpm.conf
    <FilesMatch \.php$>
    SetHandler "proxy:unix:/run/php-fpm/www.sock|fcgi://localhost/"
    </FilesMatch>
    EOF

    # -----------------------------
    # 5) Ejecutar script SQL contra el RDS
    # -----------------------------
    mysql -h REEMPLAZAR_ENDPOINT -u REEMPLAZAR_USER -pREEMPLAZAR_PASS REEMPLAZAR_DBNAME < /var/www/init_db.sql

    # -----------------------------
    # 6) Permisos de Apache
    # -----------------------------
    chown -R apache:apache /var/www/html
    chmod -R 755 /var/www/html

    # -----------------------------
    # 7) Reiniciar servicios
    # -----------------------------
    systemctl restart httpd php-fpm

    # Archivo de prueba PHP
    echo "<?php phpinfo(); ?>" > /var/www/html/info.php
    """
,

)

instance_id = instance["Instances"][0]["InstanceId"]
print(f"Instancia creada con ID: {instance_id}")

# Agregar Tag
ec2.create_tags(
    Resources=[instance_id],
    Tags=[{'Key': 'Name', 'Value': INSTANCE_NAME}]
)

print(f'Security Group creado con ID: {sg_id}')
print(f'Instancia etiquetada como: {INSTANCE_NAME}')