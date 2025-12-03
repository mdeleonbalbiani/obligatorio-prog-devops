#!/usr/bin/python3
import boto3
import time
import json
import os
import sys

# ============================
# CONFIGURACIÓN GENERAL
# ============================
REGION = "us-east-1"
AMI_ID = "ami-06b21ccaeff8cd686"
INSTANCE_TYPE = "t3.micro"
EC2_NAME = "Banco_Riendo"
DB_INSTANCE_ID = "app-sqlbanco"
DB_NAME = "RRHHapp"
DB_USER = "admin"

LOCAL_FILES_DIR = os.path.expanduser("~/obligatorio-prog-devops/python/archivos")
PASSWORD_FILE = os.path.expanduser("~/obligatorio-prog-devops/python/archivos/password.txt")

BUCKET_NAME = "app-bancoriendo"

APP_USER = "admin"
APP_PASS = "admin123"

# ============================
# LEER PASSWORD DEL TXT
# ============================
if not os.path.exists(PASSWORD_FILE):
    print("ERROR: No existe password.txt")
    exit(1)

with open(PASSWORD_FILE, "r") as f:
    DB_PASS = f.read().strip()

print("Password cargado correctamente.")

# ============================
# CLIENTES AWS
# ============================
ec2 = boto3.client("ec2", region_name=REGION)
rds = boto3.client("rds", region_name=REGION)
s3 = boto3.client("s3", region_name=REGION)

# ============================
# Crear Security Group 1
# ============================
print("Creando Security Groups...")

vpc_id = ec2.describe_vpcs()["Vpcs"][0]["VpcId"]

# SG público para EC2
sg_ec2 = ec2.create_security_group(
    GroupName="SG_Publico_HTTP",
    Description="HTTP abierto al mundo",
    VpcId=vpc_id
)
sg_ec2_id = sg_ec2["GroupId"]

ec2.authorize_security_group_ingress(
    GroupId=sg_ec2_id,
    IpPermissions=[
        {
            "IpProtocol": "tcp",
            "FromPort": 80,
            "ToPort": 80,
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
        }
    ]
)

# ============================
# Crear Security Group 2
# ============================
sg_rds = ec2.create_security_group(
    GroupName="SG_RDS_Privado",
    Description="SQL permitido solo desde EC2",
    VpcId=vpc_id
)
sg_rds_id = sg_rds["GroupId"]

ec2.authorize_security_group_ingress(
    GroupId=sg_rds_id,
    IpPermissions=[
        {
            "IpProtocol": "tcp",
            "FromPort": 3306,
            "ToPort": 3306,
            "UserIdGroupPairs": [{"GroupId": sg_ec2_id}]
        }
    ]
)

print("SG EC2:", sg_ec2_id)
print("SG RDS:", sg_rds_id)

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
    VpcSecurityGroupIds=[sg_rds_id],
)

print("Esperando a que RDS esté disponible...")
waiter = rds.get_waiter("db_instance_available")
waiter.wait(DBInstanceIdentifier=DB_INSTANCE_ID)

rds_info = rds.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE_ID)
DB_ENDPOINT = rds_info["DBInstances"][0]["Endpoint"]["Address"]

print("RDS listo:", DB_ENDPOINT)

# ============================
# CREAR S3 Y SUBIR ARCHIVOS
# ============================
bucket_name = f"banco-riendo-static-{int(time.time())}"
print("Creando bucket:", bucket_name)

s3.create_bucket(Bucket=bucket_name)
time.sleep(3)

# Subir archivos
print("Subiendo archivos desde:", LOCAL_FILES_DIR)

for filename in os.listdir(LOCAL_FILES_DIR):
    path = os.path.join(LOCAL_FILES_DIR, filename)

    if not os.path.isfile(path):
        continue

    if filename.endswith(".html"):
        ctype = "text/html"
    elif filename.endswith(".css"):
        ctype = "text/css"
    elif filename.endswith(".js"):
        ctype = "application/javascript"
    else:
        ctype = "application/octet-stream"

    with open(path, "rb") as f:
        s3.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=f,
            ContentType=ctype
        )

print("Archivos cargados a S3 correctamente.")

# =========================
# SUBIR ARCHIVO .env
# =========================
env_content = f"""
DB_HOST={DB_ENDPOINT}
DB_NAME={DB_NAME}
DB_USER={DB_USER}
DB_PASS={DB_PASS}

APP_USER={APP_USER}
APP_PASS={APP_PASS}
"""

s3.put_object(
    Bucket=bucket_name,
    Key=".env",
    Body=env_content,
    ContentType="text/plain"
)

# ============================
# USER-DATA PARA EC2
# ============================
user_data = rf"""#!/bin/bash
exec > /var/log/user-data.log 2>&1
set -x

sudo dnf -y install awscli || sudo yum install -y awscli || true
sudo dnf -y update || sudo yum -y update || true

sudo amazon-linux-extras enable php8.2
sudo yum clean metadata || true
sudo dnf -y install httpd php php-cli php-fpm php-common php-mysqlnd mariadb105 || true

sudo systemctl enable --now php-fpm
sudo systemctl enable --now httpd
sudo systemctl start httpd || true

# Configuración php-fpm para Apache (FilesMatch necesita \.php$ — raw string evita warnings)
cat <<'EOF' | sudo tee /etc/httpd/conf.d/php-fpm.conf
<FilesMatch \.php$>
    SetHandler "proxy:unix:/run/php-fpm/www.sock|fcgi://localhost/"
</FilesMatch>
EOF

sudo mkdir -p /var/www/html
sudo mkdir -p /home/ec2-user
cd /var/www/html

# Descargar archivos web desde S3
sudo aws s3 cp s3://{bucket_name}/index.php ./
sudo aws s3 cp s3://{bucket_name}/config.php ./
sudo aws s3 cp s3://{bucket_name}/login.php ./
sudo aws s3 cp s3://{bucket_name}/app.js ./
sudo aws s3 cp s3://{bucket_name}/login.js ./
sudo aws s3 cp s3://{bucket_name}/app.css ./
sudo aws s3 cp s3://{bucket_name}/login.css ./
sudo aws s3 cp s3://{bucket_name}/index.html ./
sudo aws s3 cp s3://{bucket_name}/login.html ./

cd /var/www

sudo aws s3 cp s3://{bucket_name}/.env ./ || true
sudo chown apache:apache /var/www/.env
sudo chmod 600 /var/www/.env

cd /home/ec2-user
sudo aws s3 cp s3://{bucket_name}/init_db.sql ./ || true
if [ -f /home/ec2-user/init_db.sql ]; then
    # Esperar unos segundos a que MariaDB esté listo a responder conexiones
    sleep 10
    mysql -h {DB_ENDPOINT} -u {DB_USER} -p{DB_PASS} {DB_NAME} < /home/ec2-user/init_db.sql || true
else
    echo "init_db.sql no encontrado en S3: omitiendo import."
fi

sudo chown -R apache:apache /var/www
sudo chmod -R 755 /var/www/html || true

# Desactivar enforcement de SELinux en runtime (para evitar problemas de acceso)
if command -v setenforce >/dev/null 2>&1; then
    sudo setenforce 0 || true
    sudo sed -i 's/^SELINUX=enforcing/SELINUX=permissive/' /etc/selinux/config || true
fi

# Reiniciar servicios para aplicar cambios
sudo systemctl restart httpd php-fpm || true
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
    SecurityGroupIds=[sg_ec2_id],
    UserData=user_data,
    TagSpecifications=[
        {
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": EC2_NAME}]
        }
    ]
)

instance_id = instance["Instances"][0]["InstanceId"]
print("EC2 creada:", instance_id)

print("Esperando IP pública...")

waiter = ec2.get_waiter("instance_running")
waiter.wait(InstanceIds=[instance_id])

desc = ec2.describe_instances(InstanceIds=[instance_id])
public_ip = desc["Reservations"][0]["Instances"][0]["PublicIpAddress"]

print("=======================================================")
print("DEPLOY COMPLETADO")
print("IP pública del EC2:", public_ip)
print("URL:", f"http://{public_ip}/index.php")
print("Bucket S3:", bucket_name)
print("=======================================================")
