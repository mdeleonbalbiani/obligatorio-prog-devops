#!/usr/bin/python3

import boto3

AMI = 'ami-06b21ccaeff8cd686'
SECURITY_GROUP_NAME = 'EC2SecurityDiego'
DESCRIPTION = 'Security group para la instancia EC2 de Diego' 
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
    UserData="""#!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
    systemctl enable httpd
    echo "Probando" > /var/www/html/index.html
    """,


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