#!/usr/bin/python3
import boto3
import time
import json
import os

# ============================
# CONFIGURACIÓN GENERAL
# ============================
REGION = "us-east-1"
AMI_ID = "ami-06b21ccaeff8cd686"
INSTANCE_TYPE = "t3.micro"
EC2_NAME = "Banco_Riendo"
DB_INSTANCE_ID = "app-sqlbanco"
DB_NAME = "app"
DB_USER = "admin"

LOCAL_FILES_DIR = os.path.expanduser("~/obligatorio-prog-devops/python/archivos")
PASSWORD_FILE = os.path.expanduser("~/obligatorio-prog-devops/python/archivos/password.txt")

REMOTE_WEBROOT = "/var/www/html"
REMOTE_VARWWW = "/var/www"

BUCKET_NAME = "app-bancoriendo"
SG1_NAME = "SG1_Puerto80_Publico"
SG2_NAME = "SG2_SoloDesdeSG1"

# ============================
# LEER PASSWORD DEL TXT
# ============================
if not os.path.exists(PASSWORD_FILE):
    print("ERROR: No existe password.txt")
    exit(1)

with open(PASSWORD_FILE, "r") as f:
    DB_PASS = f.read().strip()

# ============================
# CLIENTES AWS
# ============================
ec2 = boto3.client("ec2", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)

# ============================
# Obtener VPC por defecto
# ============================
vpcs = ec2.describe_vpcs().get("Vpcs", [])
if not vpcs:
    print("ERROR: No se encontraron VPCs en la cuenta/region.")
    exit(1)

vpc_id = vpcs[0]["VpcId"]
print("Usando VPC:", vpc_id)

# ============================
# Crear Security Group 1
# ============================
sg1 = ec2.create_security_group(
    GroupName="SG1_Puerto80_Publico",
    Description="SG puerto 80 abierto al mundo",
    VpcId=vpc_id
)
sg1_id = sg1["GroupId"]

ec2.authorize_security_group_ingress(
    GroupId=sg1_id,
    IpPermissions=[
        {
            "IpProtocol": "tcp",
            "FromPort": 80,
            "ToPort": 80,
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
        }
    ]
)

print("SG1 creado:", sg1_id)

# ============================
# Crear Security Group 2
# ============================
sg2 = ec2.create_security_group(
    GroupName="SG2_SoloDesdeSG1",
    Description="SG que solo permite trafico desde SG1",
    VpcId=vpc_id
)
sg2_id = sg2["GroupId"]

ec2.authorize_security_group_ingress(
    GroupId=sg2_id,
    IpPermissions=[
        {
            "IpProtocol": "tcp",
            "FromPort": 3306,
            "ToPort": 3306,
            "UserIdGroupPairs": [{"GroupId": sg1_id}]
        }
    ]
)

print("SG2 creado:", sg2_id)

# ============================
# CREAR RDS
# ============================
print("Creando instancia RDS...")

rds.create_db_instance(
    DBInstanceIdentifier=DB_INSTANCE_ID,
    AllocatedStorage=20,
    DBInstanceClass="db.t3.micro",
    Engine="mariadb",
    EngineVersion="10.5.28",
    MasterUsername=DB_USER,
    MasterUserPassword=DB_PASS,
    DBName=DB_NAME,
    PubliclyAccessible=True,
    VpcSecurityGroupIds=[sg2_id]
)

print("Esperando a que RDS esté disponible (puede tardar varios minutos)...")
waiter = rds.get_waiter("db_instance_available")
waiter.wait(DBInstanceIdentifier=DB_INSTANCE_ID)

rds_info = rds.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE_ID)
DB_ENDPOINT = rds_info["DBInstances"][0]["Endpoint"]["Address"]

print("RDS listo:", DB_ENDPOINT)

# ============================
# CREAR S3 Y SUBIR ARCHIVOS
# ============================
def upload_static_to_s3(bucket, directory, region):
    s3 = boto3.client("s3", region_name=region)

    # Crear bucket
    existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
    if bucket not in existing:
        params = {"Bucket": bucket}
        if region != "us-east-1":
            params["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**params)
        print(f"Bucket creado: {bucket}")
    else:
        print("Bucket ya existe.")

    # Subir archivos
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if not os.path.isfile(filepath):
            continue

        # Tipo de archivo
        if filename.endswith(".html"):
            ctype = "text/html"
        elif filename.endswith(".css"):
            ctype = "text/css"
        elif filename.endswith(".js"):
            ctype = "application/javascript"
        elif filename.endswith(".php"):
            ctype = "application/x-httpd-php"
        elif filename.endswith(".sql"):
           ctype = "application/sql"
        else:
            ctype = "application/octet-stream"
        with open(filepath, "rb") as f:
            content = f.read()

        s3.put_object(
            Bucket=bucket,
            Key=filename,
            Body=content,
            ContentType=ctype
        )

        print("Archivo subido:", filename)

print("Subiendo archivos a S3...")
upload_static_to_s3(BUCKET_NAME, LOCAL_FILES_DIR, REGION)


# ============================
# USER-DATA PARA EC2
# ============================
user_data = f"""#!/bin/bash
exec > /var/log/user-data.log 2>&1
set -x
sudo yum update -y
sudo dnf -y install awscli
sudo amazon-linux-extras enable php8.2
sudo yum clean metadata
sudo dnf clean all
sudo dnf makecache
sudo dnf -y update
sudo dnf -y install httpd php php-cli php-fpm php-common php-mysqlnd mariadb105 mariadb

sudo systemctl enable --now httpd
sudo systemctl enable --now php-fpm

echo '<FilesMatch \\.php$>
  SetHandler "proxy:unix:/run/php-fpm/www.sock|fcgi://localhost/"
</FilesMatch>' | sudo tee /etc/httpd/conf.d/php-fpm.conf

echo "<?php phpinfo(); ?>" | sudo tee /var/www/html/info.php

# =============================
# Descarga de archivos desde S3
# =============================
sudo mkdir -p /var/www/html
cd /var/www/html
sudo aws s3 cp s3://{BUCKET_NAME}/ . --recursive

# =============================
# Crear archivo .env con credenciales dinámicas
# =============================
sudo tee /var/www/.env >/dev/null <<ENV
DB_HOST={DB_ENDPOINT}
DB_NAME={DB_NAME}
DB_USER={DB_USER}
DB_PASS={DB_PASS}

# Variables de aplicación
APP_USER=admin
APP_PASS=admin123
ENV

sudo chown apache:apache /var/www/.env
sudo chmod 600 /var/www/.env

# =============================
# Inicializar base de datos
# =============================
mysql -h {DB_ENDPOINT} -u {DB_USER} -p{DB_PASS} {DB_NAME} < /var/www/html/init_db.sql

# =============================
# Permisos correctos para Apache
# =============================
sudo chown -R apache:apache /var/www/html
sudo setenforce 0

# =============================
# Reiniciar servicios
# =============================
sudo systemctl restart httpd php-fpm

"""

# ============================
# CREAR INSTANCIA EC2
# ============================
print("Creando instancia EC2...")

instance = ec2.run_instances(
    ImageId=AMI_ID,
    InstanceType=INSTANCE_TYPE,
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[sg1_id],
    UserData=user_data,
    TagSpecifications=[
        {
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": EC2_NAME}]
        }
    ]
)

instance_id = instance["Instances"][0]["InstanceId"]
waiter = ec2.get_waiter("instance_running")
waiter.wait(InstanceIds=[instance_id])

desc = ec2.describe_instances(InstanceIds=[instance_id])
public_ip = desc["Reservations"][0]["Instances"][0]["PublicIpAddress"]

print("=======================================================")
print("DEPLOY COMPLETADO")
print("IP pública del EC2:", public_ip)
print("URL:", f"http://{public_ip}/index.php")
print("RDS Endpoint:", DB_ENDPOINT)
print("=======================================================")
