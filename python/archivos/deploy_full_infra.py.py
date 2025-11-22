#!/usr/bin/env python3
# deploy_full_infra.py
# Compatible con Python 3.8
# Requiere: boto3 instalado y credenciales AWS configuradas en el entorno

import os
import time
import json
import base64
import botocore
import boto3

# ============================================
# CONFIGURACIÓN — REEMPLAZAR ESTOS VALORES
# ============================================
REGION = "us-east-1"                          # Región AWS
AMI_ID = "ami-0c2d06d50ce30b442"              # Amazon Linux 2023 (ejemplo en us-east-1)
INSTANCE_TYPE = "t3.micro"
KEY_PAIR_NAME = "DevOpsKey"                   # Nombre del key-pair a crear (se guardará localmente)
BUCKET_NAME = "devops-obligatorio-diego-unique-12345"  # Cambiar a nombre globalmente único
LOCAL_FILES_DIR = "./archivos"                # Carpeta local con app files y password.txt
REMOTE_WEBROOT = "/var/www/html"
DB_INSTANCE_IDENTIFIER = "mi-rds-ejemplo"
DB_NAME = "app"
DB_USER = "admin"
DB_ALLOCATED_STORAGE = 20                     # GB
DB_INSTANCE_CLASS = "db.t3.medium"
DB_ENGINE = "mariadb"
DB_ENGINE_VERSION = "10.6.14"
# ============================================

# Comprobaciones iniciales
if not os.path.isdir(LOCAL_FILES_DIR):
    raise SystemExit("ERROR: LOCAL_FILES_DIR no existe: " + LOCAL_FILES_DIR)

password_file = os.path.join(LOCAL_FILES_DIR, "password.txt")
if not os.path.isfile(password_file):
    raise SystemExit("ERROR: No se encontró password.txt en " + LOCAL_FILES_DIR)

with open(password_file, "r") as f:
    DB_PASS = f.read().strip()

if len(DB_PASS) < 8:
    raise SystemExit("ERROR: La contraseña debe tener al menos 8 caracteres")

session = boto3.session.Session(region_name=REGION)
ec2 = session.client("ec2")
ec2_resource = session.resource("ec2")
s3 = session.client("s3")
iam = session.client("iam")
rds = session.client("rds")

def ensure_bucket(bucket_name):
    try:
        s3.head_bucket(Bucket=bucket_name)
        print("S3 bucket existe:", bucket_name)
    except botocore.exceptions.ClientError as e:
        code = int(e.response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0))
        if code == 404 or e.response['Error']['Code'] in ("NoSuchBucket", "404"):
            print("Creando bucket S3:", bucket_name)
            if REGION == "us-east-1":
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(
                    Bucket=bucket_name,
                    CreateBucketConfiguration={"LocationConstraint": REGION}
                )
            waiter = s3.get_waiter("bucket_exists")
            waiter.wait(Bucket=bucket_name)
            print("Bucket creado")
        else:
            raise

def upload_files_to_s3(bucket_name, local_dir, prefix="app/"):
    print("Subiendo archivos a s3://{}/{}".format(bucket_name, prefix))
    for root, _, files in os.walk(local_dir):
        for fname in files:
            local_path = os.path.join(root, fname)
            relative = os.path.relpath(local_path, local_dir)
            s3_key = prefix + relative.replace("\\", "/")
            print(" ->", s3_key)
            s3.upload_file(local_path, bucket_name, s3_key)
    print("Upload completo")

def ensure_keypair(key_name):
    key_path = key_name + ".pem"
    try:
        resp = ec2.describe_key_pairs(KeyNames=[key_name])
        print("Key pair ya existe:", key_name)
        if not os.path.isfile(key_path):
            print("Advertencia: key pair existe en AWS pero el .pem no está localmente:", key_path)
        return key_path
    except botocore.exceptions.ClientError as e:
        if "InvalidKeyPair.NotFound" in str(e):
            print("Creando key pair:", key_name)
            new_key = ec2.create_key_pair(KeyName=key_name)
            private_key = new_key["KeyMaterial"]
            with open(key_path, "w") as f:
                f.write(private_key)
            os.chmod(key_path, 0o600)
            print("Key pair guardado en:", key_path)
            return key_path
        else:
            raise

def get_default_vpc_id():
    resp = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])
    vpcs = resp.get("Vpcs", [])
    if vpcs:
        return vpcs[0]["VpcId"]
    # fallback: pick the first VPC
    resp = ec2.describe_vpcs()
    vpcs = resp.get("Vpcs", [])
    if not vpcs:
        raise SystemExit("No hay VPCs en la cuenta")
    return vpcs[0]["VpcId"]

def create_security_group(name, description, vpc_id):
    print("Creando Security Group:", name)
    resp = ec2.create_security_group(GroupName=name, Description=description, VpcId=vpc_id)
    sg_id = resp["GroupId"]
    print("SG creado:", sg_id)
    return sg_id

def authorize_sg_ingress(sg_id, ip_permissions):
    try:
        ec2.authorize_security_group_ingress(GroupId=sg_id, IpPermissions=ip_permissions)
        print("Reglas aplicadas a", sg_id)
    except botocore.exceptions.ClientError as e:
        if "InvalidPermission.Duplicate" in str(e):
            print("Regla ya existe en", sg_id)
        else:
            raise

def create_iam_role_for_s3(role_name):
    assume_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "ec2.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    try:
        iam.get_role(RoleName=role_name)
        print("IAM role ya existe:", role_name)
    except iam.exceptions.NoSuchEntityException:
        print("Creando IAM role:", role_name)
        iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(assume_policy),
            Description="Role para permitir que EC2 lea de S3"
        )

    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::" + BUCKET_NAME,
                    "arn:aws:s3:::" + BUCKET_NAME + "/*"
                ]
            }
        ]
    }
    policy_name = role_name + "-S3ReadPolicy"
    try:
        iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)
        print("Policy inline ya existe en role:", policy_name)
    except iam.exceptions.NoSuchEntityException:
        iam.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(policy_document)
        )
        print("Policy asignada al role:", policy_name)

    # Crear instance profile si no existe
    try:
        iam.get_instance_profile(InstanceProfileName=role_name)
    except iam.exceptions.NoSuchEntityException:
        iam.create_instance_profile(InstanceProfileName=role_name)
    # Añadir role al instance profile si no está
    try:
        iam.add_role_to_instance_profile(InstanceProfileName=role_name, RoleName=role_name)
    except iam.exceptions.EntityAlreadyExistsException:
        pass
    return role_name

def create_rds_instance(db_identifier, db_name, master_user, master_pass, sg_ids):
    print("Creando RDS instance:", db_identifier)
    try:
        rds.create_db_instance(
            DBInstanceIdentifier=db_identifier,
            AllocatedStorage=DB_ALLOCATED_STORAGE,
            DBInstanceClass=DB_INSTANCE_CLASS,
            Engine=DB_ENGINE,
            EngineVersion=DB_ENGINE_VERSION,
            MasterUsername=master_user,
            MasterUserPassword=master_pass,
            DBName=db_name,
            VpcSecurityGroupIds=sg_ids,
            PubliclyAccessible=True,
            MultiAZ=False,
            StorageType="gp2",
            Tags=[{"Key": "Name", "Value": db_identifier}]
        )
    except botocore.exceptions.ClientError as e:
        if "DBInstanceAlreadyExists" in str(e):
            print("RDS instance ya existe:", db_identifier)
        else:
            raise
    # esperar a que esté disponible
    print("Esperando a que RDS esté disponible, esto puede tardar varios minutos...")
    waiter = rds.get_waiter("db_instance_available")
    waiter.wait(DBInstanceIdentifier=db_identifier)
    resp = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)
    endpoint = resp["DBInstances"][0]["Endpoint"]["Address"]
    print("RDS disponible en:", endpoint)
    return endpoint

def create_ec2_instance(ami, instance_type, key_name, sg_id, iam_instance_profile_name, user_data):
    print("Lanzando EC2")
    instances = ec2_resource.create_instances(
        ImageId=ami,
        InstanceType=instance_type,
        KeyName=key_name,
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[sg_id],
        IamInstanceProfile={"Name": iam_instance_profile_name},
        UserData=user_data
    )
    inst = instances[0]
    print("Instancia creada, id:", inst.id)
    inst.wait_until_running()
    inst.reload()
    public_ip = inst.public_ip_address
    print("EC2 corriendo. IP pública:", public_ip)
    return inst.id, public_ip

# Construir user-data (cloud-init)
def build_user_data(bucket, region, prefix="app/"):
    ud = """#!/bin/bash
# Actualizar e instalar paquetes
dnf clean all
dnf makecache
dnf -y update
dnf -y install httpd php php-cli php-fpm php-common php-mysqlnd mariadb105 awscli git unzip || true

systemctl enable --now httpd
systemctl enable --now php-fpm

# Sincronizar archivos desde S3 (requiere que la instancia tenga un role con permiso S3)
mkdir -p /var/www
aws s3 sync s3://{bucket}/{prefix} {webroot} --region {region}

# Mover init_db.sql y .env fuera del webroot si existieran
if [ -f {webroot}/init_db.sql ]; then
  mv {webroot}/init_db.sql /var/www/
fi
if [ -f {webroot}/.env ]; then
  mv {webroot}/.env /var/www/
fi

# Ajustar permisos
chown -R apache:apache {webroot}
chmod -R 755 {webroot}

# Configurar php-fpm en apache (si falta)
if [ ! -f /etc/httpd/conf.d/php-fpm.conf ]; then
cat > /etc/httpd/conf.d/php-fpm.conf <<'EOF'
<FilesMatch \\.php$>
  SetHandler "proxy:unix:/run/php-fpm/www.sock|fcgi://localhost/"
</FilesMatch>
EOF
fi

# Crear archivo de prueba
echo "<?php phpinfo(); ?>" > {webroot}/info.php

systemctl restart httpd php-fpm
""".format(bucket=bucket, prefix=prefix.rstrip("/"), webroot=REMOTE_WEBROOT, region=region)
    return ud

def main():
    print("Iniciando despliegue en region:", REGION)
    # 1) bucket
    ensure_bucket(BUCKET_NAME)
    upload_files_to_s3(BUCKET_NAME, LOCAL_FILES_DIR, prefix="app/")

    # 2) keypair
    key_path = ensure_keypair(KEY_PAIR_NAME)

    # 3) VPC y security groups
    vpc_id = get_default_vpc_id()
    print("VPC seleccionada:", vpc_id)

    ec2_sg_name = "ec2-sg-app"
    rds_sg_name = "rds-sg-db"

    ec2_sg_id = create_security_group(ec2_sg_name, "SG para EC2 (SSH, HTTP)", vpc_id)
    rds_sg_id = create_security_group(rds_sg_name, "SG para RDS (MySQL)", vpc_id)

    # Autorizar SSH(22) y HTTP(80) al EC2 SG (desde internet)
    ip_perms_ec2 = [
        {'IpProtocol': 'tcp', 'FromPort': 22, 'ToPort': 22, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]},
        {'IpProtocol': 'tcp', 'FromPort': 80, 'ToPort': 80, 'IpRanges': [{'CidrIp': '0.0.0.0/0'}]}
    ]
    authorize_sg_ingress(ec2_sg_id, ip_perms_ec2)

    # Autorizar MySQL(3306) al RDS SG solo desde el EC2 SG
    ip_perms_rds = [
        {'IpProtocol': 'tcp', 'FromPort': 3306, 'ToPort': 3306, 'UserIdGroupPairs': [{'GroupId': ec2_sg_id}]}
    ]
    authorize_sg_ingress(rds_sg_id, ip_perms_rds)

    # 4) IAM role para que EC2 lea S3
    role_name = "EC2S3ReadRole-DevOps"
    create_iam_role_for_s3(role_name)

    # Espacio para que IAM repique role/instance profile en todo AWS (puede tardar unos segundos)
    print("Esperando 10s para que IAM propague cambios...")
    time.sleep(10)

    # 5) Crear RDS
    endpoint = None
    try:
        endpoint = create_rds_instance(DB_INSTANCE_IDENTIFIER, DB_NAME, DB_USER, DB_PASS, [rds_sg_id])
    except Exception as e:
        print("Error creando RDS:", e)
        raise

    # 6) Crear EC2 con user-data que sincroniza desde S3
    user_data = build_user_data(BUCKET_NAME, REGION, prefix="app/")
    try:
        instance_id, public_ip = create_ec2_instance(AMI_ID, INSTANCE_TYPE, KEY_PAIR_NAME, ec2_sg_id, role_name, user_data)
    except Exception as e:
        print("Error creando EC2:", e)
        raise

    print("\nResumen:")
    print("Bucket S3: s3://{}".format(BUCKET_NAME))
    print("EC2 instance id:", instance_id)
    print("EC2 public IP:", public_ip)
    print("Key pair local file:", key_path)
    print("RDS endpoint:", endpoint)
    print("\nAcciones manuales recomendadas:")
    print("- Asegurá que en RDS el security group permite acceso al puerto 3306 desde la instancia EC2 (este script ya lo configuró).")
    print("- Si querés ejecutar el init_db.sql desde la EC2 a la RDS, conectate via ssh y ejecutá:")
    print("    mysql -h {} -u {} -p{} {} < /var/www/init_db.sql".format(endpoint, DB_USER, DB_PASS, DB_NAME))
    print("- Las credenciales de la app (APP_USER/APP_PASS) está en tu archivo .env que subiste en S3. Si querés generarlo aquí, se puede agregar esa parte.")
    print("\nListo.")

if __name__ == "__main__":
    main()
