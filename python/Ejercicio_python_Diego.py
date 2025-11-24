#!/usr/bin/python3
import boto3
import time
import os
from botocore.exceptions import ClientError

# ============================
# CLIENTES GLOBALES
# ============================
s3 = boto3.client('s3')
ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')
rds = boto3.client('rds')

# ============================
# PARÁMETROS GENERALES
# ============================
BUCKET_NAME = 'Banco Riendo'
FILE_PATH = 'archivo.txt'
OBJECT_NAME = FILE_PATH.split('/')[-1]
AMI_ID = 'ami-06b21ccaeff8cd686'


# ============================================================
# SECURITY GROUP – Crear SG y asignarlo al webserver luego
# ============================================================
def configurar_security_group():
    sg_name = 'web-sg-boto3'
    try:
        response = ec2.create_security_group(
            GroupName=sg_name,
            Description='Permitir trafico web desde cualquier IP'
        )
        sg_id = response['GroupId']
        print(f"Security Group creado: {sg_id}")

        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[{
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }]
        )

    except Exception as e:
        if 'InvalidGroup.Duplicate' in str(e):
            sg_id = ec2.describe_security_groups(GroupNames=[sg_name])['SecurityGroups'][0]['GroupId']
            print(f"Security Group ya existe: {sg_id}")
        else:
            raise

    return sg_id


# ============================
# S3 – Crear bucket, subir, listar, descargar, eliminar
# ============================
def crear_bucket():
    try:
        s3.create_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket creado: {BUCKET_NAME}")
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"El bucket {BUCKET_NAME} ya existe y es tuyo.")
        else:
            print(f"Error creando bucket: {e}")
            exit(1)

def subir_archivo():
    try:
        s3.upload_file(FILE_PATH, BUCKET_NAME, OBJECT_NAME)
        print(f"Archivo {FILE_PATH} subido.")
    except FileNotFoundError:
        print(f"El archivo {FILE_PATH} no existe")
    except ClientError as e:
        print(f"Error subiendo archivo: {e}")

def listar_objetos():
    try:
        response = s3.list_objects_v2(Bucket=BUCKET_NAME)
        if 'Contents' in response:
            print("Objetos en el bucket:")
            for obj in response['Contents']:
                print(" -", obj['Key'])
        else:
            print("No hay objetos en el bucket.")
    except Exception as e:
        print(f"Error listando objetos: {e}")

def descargar_archivo():
    try:
        s3.download_file(BUCKET_NAME, OBJECT_NAME, OBJECT_NAME)
        print(f'Archivo {OBJECT_NAME} descargado.')
    except Exception as e:
        print(f'Error descargando archivo: {e}')

def eliminar_objeto():
    try:
        s3.delete_object(Bucket=BUCKET_NAME, Key=OBJECT_NAME)
        print(f'Objeto {OBJECT_NAME} eliminado.')
    except Exception as e:
        print(f'Error eliminando objeto: {e}')


# ============================
# EC2 – Crear instancias
# ============================
def crear_ec2_simple():
    response = ec2.run_instances(
        ImageId=AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro'
    )
    instance_id = response['Instances'][0]['InstanceId']
    print(f"EC2 simple creada: {instance_id}")
    return instance_id


def ec2_con_ssm():
    response = ec2.run_instances(
        ImageId=AMI_ID,
        MinCount=1,
        MaxCount=1,
        InstanceType='t2.micro',
        IamInstanceProfile={'Name': 'LabInstanceProfile'},
    )
    instance_id = response['Instances'][0]['InstanceId']
    print(f"EC2 con SSM creada: {instance_id}")

    ec2.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])

    command = 'echo "Hello world"'
    cmd = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName="AWS-RunShellScript",
        Parameters={'commands': [command]}
    )
    command_id = cmd['Command']['CommandId']

    while True:
        output = ssm.get_command_invocation(CommandId=command_id, InstanceId=instance_id)
        if output['Status'] in ['Success', 'Failed', 'Cancelled', 'TimedOut']:
            break
        time.sleep(2)

    print("Salida del comando:")
    print(output['StandardOutputContent'])


def crear_webserver(sg_id):
    user_data = '''#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "¡Sitio personalizado!" > /var/www/html/index.html
'''

    response = ec2.run_instances(
        ImageId=AMI_ID,
        InstanceType='t2.micro',
        MinCount=1,
        MaxCount=1,
        IamInstanceProfile={'Name': 'LabInstanceProfile'},
        SecurityGroupIds=[sg_id],
        UserData=user_data
    )

    instance_id = response['Instances'][0]['InstanceId']
    ec2.create_tags(
        Resources=[instance_id],
        Tags=[{'Key': 'Name', 'Value': 'webserver-devops'}]
    )
    print(f"Webserver creado: {instance_id}")
    return instance_id


# ============================
# RDS – Crear instancia MySQL
# ============================
def crear_rds():
    DB_INSTANCE_ID = 'app-mysql'
    DB_NAME = 'app'
    DB_USER = 'admin'
    DB_PASS = os.environ.get('RDS_ADMIN_PASSWORD')

    if not DB_PASS:
        raise Exception('Debes exportar RDS_ADMIN_PASSWORD en tu entorno.')

    try:
        rds.create_db_instance(
            DBInstanceIdentifier=DB_INSTANCE_ID,
            AllocatedStorage=20,
            DBInstanceClass='db.t3.micro',
            Engine='mysql',
            MasterUsername=DB_USER,
            MasterUserPassword=DB_PASS,
            DBName=DB_NAME,
            PubliclyAccessible=True,
            BackupRetentionPeriod=0
        )
        print(f'RDS {DB_INSTANCE_ID} creado.')
    except rds.exceptions.DBInstanceAlreadyExistsFault:
        print(f'RDS {DB_INSTANCE_ID} ya existe.')


# ============================
# MAIN – EJECUCIÓN ORDENADA
# ============================
if __name__ == "__main__":

    print("\n=== CONFIGURAR SECURITY GROUP ===")
    sg_id = configurar_security_group()

    print("\n=== OPERACIONES S3 ===")
    crear_bucket()
    subir_archivo()
    listar_objetos()
    descargar_archivo()
    eliminar_objeto()

    print("\n=== CREACIÓN DE INSTANCIAS EC2 ===")
    crear_ec2_simple()
    ec2_con_ssm()
    crear_webserver(sg_id)

    print("\n=== CREAR RDS ===")
    crear_rds()

    print("\n EJECUCIÓN COMPLETA")
