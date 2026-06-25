#!/usr/bin/env python3
"""
Inicialización de LocalStack para TicketDesk Enterprise v2.1

Este script crea los servicios AWS necesarios en LocalStack:
- Buckets S3 para archivos
- Tabla DynamoDB para caché
- Cola SQS para tareas asincrónicas
"""

import os
import sys
import boto3
import time
from botocore.exceptions import ClientError, ConnectionError

# Configuración
LOCALSTACK_ENDPOINT = os.getenv('LOCALSTACK_ENDPOINT', 'http://localhost:4566')
AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY_ID', 'test')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')

# Servicios a crear
S3_BUCKET = 'ticketdesk-attachments'
DYNAMODB_TABLE = 'ticketdesk-cache'
SQS_QUEUE = 'ticketdesk-tasks'

def wait_for_localstack(max_attempts=30):
    """Esperar a que LocalStack esté listo"""
    print("Esperando a que LocalStack esté listo...")
    for attempt in range(max_attempts):
        try:
            s3 = boto3.client(
                's3',
                endpoint_url=LOCALSTACK_ENDPOINT,
                region_name=AWS_REGION,
                aws_access_key_id=AWS_ACCESS_KEY,
                aws_secret_access_key=AWS_SECRET_KEY
            )
            s3.list_buckets()
            print("✓ LocalStack está listo")
            return True
        except (ConnectionError, Exception) as e:
            if attempt < max_attempts - 1:
                print(f"  Intento {attempt + 1}/{max_attempts}... esperando 2 segundos")
                time.sleep(2)
            else:
                print(f"✗ No se pudo conectar a LocalStack en {LOCALSTACK_ENDPOINT}")
                return False
    return False

def create_s3_bucket():
    """Crear bucket S3 para archivos"""
    try:
        s3 = boto3.client(
            's3',
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        # Crear bucket
        s3.create_bucket(Bucket=S3_BUCKET)
        print(f"✓ Bucket S3 '{S3_BUCKET}' creado")
        
        # Configurar política de acceso público (para desarrollo)
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": f"arn:aws:s3:::{S3_BUCKET}/*"
                }
            ]
        }
        s3.put_bucket_policy(Bucket=S3_BUCKET, Policy=str(policy).replace("'", '"'))
        print(f"✓ Política de acceso público configurada para {S3_BUCKET}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            print(f"✓ Bucket S3 '{S3_BUCKET}' ya existe")
        else:
            print(f"✗ Error creando bucket S3: {e}")
            return False
    except Exception as e:
        print(f"✗ Error creando bucket S3: {e}")
        return False
    
    return True

def create_dynamodb_table():
    """Crear tabla DynamoDB para caché"""
    try:
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        dynamodb.create_table(
            TableName=DYNAMODB_TABLE,
            KeySchema=[
                {'AttributeName': 'key', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'key', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        print(f"✓ Tabla DynamoDB '{DYNAMODB_TABLE}' creada")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"✓ Tabla DynamoDB '{DYNAMODB_TABLE}' ya existe")
        else:
            print(f"✗ Error creando tabla DynamoDB: {e}")
            return False
    except Exception as e:
        print(f"✗ Error creando tabla DynamoDB: {e}")
        return False
    
    return True

def create_sqs_queue():
    """Crear cola SQS para tareas asincrónicas"""
    try:
        sqs = boto3.client(
            'sqs',
            endpoint_url=LOCALSTACK_ENDPOINT,
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY,
            aws_secret_access_key=AWS_SECRET_KEY
        )
        
        response = sqs.create_queue(QueueName=SQS_QUEUE)
        print(f"✓ Cola SQS '{SQS_QUEUE}' creada")
        print(f"  URL: {response['QueueUrl']}")
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'QueueAlreadyExists':
            print(f"✓ Cola SQS '{SQS_QUEUE}' ya existe")
        else:
            print(f"✗ Error creando cola SQS: {e}")
            return False
    except Exception as e:
        print(f"✗ Error creando cola SQS: {e}")
        return False
    
    return True

def main():
    """Inicializar todos los servicios"""
    print("\n" + "="*70)
    print("LocalStack Setup - TicketDesk Enterprise v2.1")
    print("="*70 + "\n")
    
    print(f"Conectando a LocalStack en: {LOCALSTACK_ENDPOINT}")
    print(f"Región: {AWS_REGION}\n")
    
    # Esperar a que LocalStack esté listo
    if not wait_for_localstack():
        print("\n✗ No se pudo conectar a LocalStack")
        print("Asegúrate de ejecutar: .\start_localstack.bat")
        sys.exit(1)
    
    print()
    
    # Crear servicios
    all_ok = True
    all_ok &= create_s3_bucket()
    all_ok &= create_dynamodb_table()
    all_ok &= create_sqs_queue()
    
    print()
    if all_ok:
        print("✓ Todos los servicios inicializados correctamente")
        print("\nLocalStack está listo para TicketDesk:")
        print(f"  S3 Bucket: {S3_BUCKET}")
        print(f"  DynamoDB Table: {DYNAMODB_TABLE}")
        print(f"  SQS Queue: {SQS_QUEUE}")
        print(f"  Dashboard: http://localhost:4566/_localstack/console")
        print()
        sys.exit(0)
    else:
        print("✗ Algunos servicios fallaron")
        sys.exit(1)

if __name__ == '__main__':
    main()
