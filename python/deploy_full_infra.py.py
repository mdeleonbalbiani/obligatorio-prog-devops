#!/usr/bin/python3
import boto3
import time
import json
import os

# ============================
# CONFIGURACIÓN GENERAL
# ============================
REGION = "us-east-1"
AMI_ID = "ami-0c2d06d50ce30b442" 
INSTANCE_TYPE = "t3.micro"

# Nombres personalizados
EC2_NAME = "Banco_Riendo"
DB_INSTANCE_ID = "app-mysql"
DB_NAME = "app"
DB_USER = "admin"

LOCAL_FILES_DIR = "~/obligatorio-prog-devops/python/archivos"
PASSWORD_FILE = "./password.txt"

REMOTE_WEBROOT = "/var/www/html"
REMOTE_VARWWW = "/var/www"

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
iam = boto3.client("iam")
s3 = boto3.client("s3")


# ============================
# CREAR SECURITY GROUP
# ============================
print("Creando Security Group...")

sg = ec2.create_security_group(
    GroupName="SG-BancoRiendo",
    Description="SG para Banco_Riendo — solo puerto 80"
)

sg_id = sg["GroupId"]

ec2.authorize_security_group_ingress(
    GroupId=sg_id,
    IpPermissions=[
        {
            "IpProtocol": "tcp",
            "FromPort": 80,
            "ToPort": 80,
            "IpRanges": [{"CidrIp": "0.0.0.0/0"}]
        }
    ]
)
print("Security Group creado:", sg_id)


# ============================
# CREAR RDS
# ============================
print("Creando instancia RDS...")

rds.create_db_instance(
    DBInstanceIdentifier=DB_INSTANCE_ID,
    AllocatedStorage=20,
    DBInstanceClass="db.t3.micro",
    Engine="mariadb",
    EngineVersion="10.6.14",
    MasterUsername=DB_USER,
    MasterUserPassword=DB_PASS,
    DBName=DB_NAME,
    PubliclyAccessible=True,
    VpcSecurityGroupIds=[sg_id]
)

print("Esperando a que RDS esté disponible (~4-8 min)...")
waiter = rds.get_waiter("db_instance_available")
waiter.wait(DBInstanceIdentifier=DB_INSTANCE_ID)

rds_info = rds.describe_db_instances(DBInstanceIdentifier=DB_INSTANCE_ID)
DB_ENDPOINT = rds_info["DBInstances"][0]["Endpoint"]["Address"]

print("RDS listo:", DB_ENDPOINT)


# ============================
# USER-DATA CLOUD INIT
# ============================
cloud_init = f"""#cloud-config
package_update: true
package_upgrade: true

runcmd:
  - dnf clean all
  - dnf makecache
  - dnf -y update
  - dnf -y install httpd php php-cli php-fpm php-common php-mysqlnd mariadb105

  - systemctl enable --now httpd
  - systemctl enable --now php-fpm

  # Config PHP-FPM
  - |
    cat << 'EOF' > /etc/httpd/conf.d/php-fpm.conf
    <FilesMatch \\.php$>
      SetHandler "proxy:unix:/run/php-fpm/www.sock|fcgi://localhost/"
    </FilesMatch>
    EOF

  - systemctl restart httpd php-fpm

  # Crear estructura
  - mkdir -p {REMOTE_WEBROOT}
  - mkdir -p {REMOTE_VARWWW}

  # Descargar archivos desde S3
  - aws s3 sync s3://app-bancoriendo {REMOTE_WEBROOT}

  # Mover init_db.sql fuera del webroot
  - mv {REMOTE_WEBROOT}/init_db.sql {REMOTE_VARWWW}/init_db.sql || true

  # Crear archivo .env
  - |
    cat << 'EOF' > {REMOTE_VARWWW}/.env
    DB_HOST={DB_ENDPOINT}
    DB_NAME={DB_NAME}
    DB_USER={DB_USER}
    DB_PASS={DB_PASS}

    APP_USER=admin
    APP_PASS=admin123
    EOF

  - chown apache:apache {REMOTE_VARWWW}/.env
  - chmod 600 {REMOTE_VARWWW}/.env

  # Ejecutar script SQL contra RDS
  - mysql -h {DB_ENDPOINT} -u {DB_USER} -p{DB_PASS} {DB_NAME} < {REMOTE_VARWWW}/init_db.sql

  - systemctl restart httpd
"""

# ============================
# SUBIR ARCHIVOS A S3
# ============================
bucket_name = "app-bancoriendo"

print("Creando bucket S3...")
s3.create_bucket(
    Bucket=bucket_name,
    CreateBucketConfiguration={"LocationConstraint": REGION}
)

print("Subiendo archivos al bucket S3...")

for root, dirs, files in os.walk(LOCAL_FILES_DIR):
    for file in files:
        full = os.path.join(root, file)
        key = file
        print("Subiendo:", key)
        s3.upload_file(full, bucket_name, key)


# ============================
# CREAR INSTANCIA EC2
# ============================
print("Creando instancia EC2...")

instance = ec2.run_instances(
    ImageId=AMI_ID,
    InstanceType=INSTANCE_TYPE,
    MinCount=1,
    MaxCount=1,
    SecurityGroupIds=[sg_id],
    UserData=cloud_init,
    TagSpecifications=[
        {
            "ResourceType": "instance",
            "Tags": [{"Key": "Name", "Value": EC2_NAME}]
        }
    ]
)

instance_id = instance["Instances"][0]["InstanceId"]
print("Esperando a que la instancia esté en running...")

waiter = ec2.get_waiter("instance_running")
waiter.wait(InstanceIds=[instance_id])

desc = ec2.describe_instances(InstanceIds=[instance_id])
public_ip = desc["Reservations"][0]["Instances"][0]["PublicIpAddress"]

print("=======================================================")
print("DEPLOY COMPLETADO")
print("IP pública del EC2:", public_ip)
print("URL:", f"http://{public_ip}/login.php")
print("RDS Endpoint:", DB_ENDPOINT)
print("=======================================================")
