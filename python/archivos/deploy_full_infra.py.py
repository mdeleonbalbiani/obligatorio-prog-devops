#!/usr/bin/python3

import boto3
import time
import base64
import json
import os

# ============================================
# CONFIGURACIÓN — REEMPLAZAR ESTOS VALORES
# ============================================
AMI_ID = "ami-0c2d06d50ce30b442"   # Amazon Linux 2023
INSTANCE_TYPE = "t3.micro"

DB_NAME = "demo_db"
DB_USER = "demo_user"
DB_PASS = "demo_pass"
DB_ALLOCATED_STORAGE = 20

KEY_PAIR_NAME = "DevOpsKey"
BUCKET_NAME = "devops-obligatorio-diego"
REGION = "us-east-1"

# Archivos locales para copiar al EC2
LOCAL_FILES_DIR = "./archivos"
REMOTE_WEBROOT = "/var/www/html"
REMOTE_VARWWW = "/var/www"

# ============================================
# CLIENTES AWS
# ============================================
ec2 = boto3.client("ec2", region_name=REGION)
iam = boto3.client("iam")
rds = boto3.client("rds", region_name=REGION)
s3 = boto3.client("s3")

# ============================================
# FUNCIONES AUXILIARES
# ============================================

def create_security_group():
    print(" Creando Security Group...")

    resp = ec2.create_security_group(
        GroupName="EC2SecurityDiego",
        Description="SG para EC2 obligatorio DevOps"
    )

    sg_id = resp["GroupId"]

    # SSH, HTTP, MySQL
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {"IpProtocol": "tcp", "FromPort": 22, "ToPort": 22,
             "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
            {"IpProtocol": "tcp", "FromPort": 80, "ToPort": 80,
             "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
            {"IpProtocol": "tcp", "FromPort": 3306, "ToPort": 3306,
             "IpRanges": [{"CidrIp": "0.0.0.0/0"}]},
        ]
    )

    print("✔ SG creado:", sg_id)
    return sg_id


def create_s3_bucket():
    print(" Creando bucket S3...")

    try:
        s3.create_bucket(
            Bucket=BUCKET_NAME,
            CreateBucketConfiguration={"LocationConstraint": REGION}
        )
        print("✔ Bucket creado:", BUCKET_NAME)

    except Exception as e:
        print("ℹ Bucket puede existir:", e)


def create_iam_role():
    print(" Creando IAM Role...")

    assume_role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "ec2.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }

    try:
        iam.create_role(
            RoleName="EC2ObligatorioRole",
            AssumeRolePolicyDocument=json.dumps(assume_role_policy)
        )
    except Exception as e:
        print("ℹ Role puede existir:", e)

    # Attach policy
    iam.attach_role_policy(
        RoleName="EC2ObligatorioRole",
        PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess"
    )

    # Crear Instance Profile
    try:
        iam.create_instance_profile(InstanceProfileName="EC2ObligatorioProfile")
    except Exception:
        pass

    try:
        iam.add_role_to_instance_profile(
            InstanceProfileName="EC2ObligatorioProfile",
            RoleName="EC2ObligatorioRole"
        )
    except Exception:
        pass

    print("✔ IAM Role listo")
    return "EC2ObligatorioProfile"


def create_rds_instance(sg_id):
    print(" Creando RDS MySQL...")

    try:
        rds.create_db_instance(
            DBName=DB_NAME,
            DBInstanceIdentifier="devops-obligatorio-db",
            AllocatedStorage=DB_ALLOCATED_STORAGE,
            DBInstanceClass="db.t3.micro",
            Engine="mysql",
            MasterUsername=DB_USER,
            MasterUserPassword=DB_PASS,
            VpcSecurityGroupIds=[sg_id],
            PubliclyAccessible=True
        )
    except Exception as e:
        print("ℹ Error o ya existe:", e)

    print(" Esperando RDS (5–10 minutos)...")

    waiter = rds.get_waiter("db_instance_available")
    waiter.wait(DBInstanceIdentifier="devops-obligatorio-db")

    resp = rds.describe_db_instances(DBInstanceIdentifier="devops-obligatorio-db")
    endpoint = resp["DBInstances"][0]["Endpoint"]["Address"]

    print("✔ RDS listo, endpoint:", endpoint)
    return endpoint


def build_cloud_init(rds_endpoint):
    print(" Generando cloud-init...")

    cloud_init = f"""#cloud-config
package_update: true
package_upgrade: true

runcmd:
  - dnf -y install httpd php php-cli php-fpm php-common php-mysqlnd mariadb105
  - systemctl enable --now httpd
  - systemctl enable --now php-fpm

  - mkdir -p {REMOTE_WEBROOT}
  - mkdir -p {REMOTE_VARWWW}

  - echo "Creando archivos desde script..."
"""

    # Copiar tus archivos
    for file_name in os.listdir(LOCAL_FILES_DIR):
        full_path = os.path.join(LOCAL_FILES_DIR, file_name)

        if os.path.isfile(full_path):
            with open(full_path, "r") as f:
                encoded = base64.b64encode(f.read().encode()).decode()

            target = f"{REMOTE_WEBROOT}/{file_name}"

            cloud_init += f"""
  - echo "{encoded}" | base64 -d > {target}
"""

    # Crear .env
    cloud_init += f"""
  - echo "DB_HOST={rds_endpoint}" > {REMOTE_VARWWW}/.env
  - echo "DB_NAME={DB_NAME}" >> {REMOTE_VARWWW}/.env
  - echo "DB_USER={DB_USER}" >> {REMOTE_VARWWW}/.env
  - echo "DB_PASS={DB_PASS}" >> {REMOTE_VARWWW}/.env
  - echo "APP_USER=admin" >> {REMOTE_VARWWW}/.env
  - echo "APP_PASS=admin123" >> {REMOTE_VARWWW}/.env
  - chmod 600 {REMOTE_VARWWW}/.env

  - mysql -h {rds_endpoint} -u {DB_USER} -p{DB_PASS} {DB_NAME} < {REMOTE_WEBROOT}/init_db.sql

  - systemctl restart httpd php-fpm
"""

    return cloud_init


def create_ec2_instance(sg_id, instance_profile, user_data):
    print(" Lanzando EC2...")

    resp = ec2.run_instances(
        ImageId=AMI_ID,
        InstanceType=INSTANCE_TYPE,
        KeyName=KEY_PAIR_NAME,
        SecurityGroupIds=[sg_id],
        MinCount=1,
        MaxCount=1,
        IamInstanceProfile={"Name": instance_profile},
        UserData=user_data
    )

    instance_id = resp["Instances"][0]["InstanceId"]
    print("⏳ Esperando EC2 listo...")

    ec2.get_waiter("instance_status_ok").wait(InstanceIds=[instance_id])

    desc = ec2.describe_instances(InstanceIds=[instance_id])
    public_ip = desc["Reservations"][0]["Instances"][0]["PublicIpAddress"]

    print("✔ EC2 listo:", public_ip)
    return public_ip


# ================================
# MAIN
# ================================
if __name__ == "__main__":
    sg_id = create_security_group()
    create_s3_bucket()
    instance_profile = create_iam_role()
    rds_endpoint = create_rds_instance(sg_id)

    cloud_init = build_cloud_init(rds_endpoint)
    ec2_ip = create_ec2_instance(sg_id, instance_profile, cloud_init)

    print("\n DEPLOY COMPLETO")
    print(" EC2:", ec2_ip)
    print(" Login:", f"http://{ec2_ip}/login.php")
