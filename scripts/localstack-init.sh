#!/bin/bash
# LocalStack Initialization Script
# Crea recursos AWS simulados necesarios para TicketDesk

set -e

echo "=== Iniciando LocalStack Setup ==="

# Configuración AWS Local
export AWS_ACCESS_KEY_ID=test
export AWS_SECRET_ACCESS_KEY=test
export AWS_DEFAULT_REGION=us-east-1

# Endpoint local
ENDPOINT_URL="http://localhost:4566"

# Esperar a que LocalStack esté listo
echo "Esperando LocalStack..."
for i in {1..30}; do
  if curl -s "${ENDPOINT_URL}/health" > /dev/null 2>&1; then
    echo "LocalStack está listo!"
    break
  fi
  echo "Intento $i/30 - Esperando LocalStack..."
  sleep 1
done

# ========================================================================
# 1. Crear instancia RDS (base de datos relacional)
# ========================================================================
echo "Creando RDS Database..."
aws --endpoint-url="${ENDPOINT_URL}" rds create-db-instance \
  --db-instance-identifier ticketdesk-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username ticketdesk \
  --master-user-password "ticketdesk123" \
  --allocated-storage 20 \
  --backup-retention-period 7 \
  --db-name ticketdesk \
  --port 5432 \
  --publicly-accessible \
  --no-enable-iam-database-authentication \
  --storage-encrypted \
  2>/dev/null || echo "RDS ya existe"

# ========================================================================
# 2. Crear bucket S3 para backups y archivos
# ========================================================================
echo "Creando S3 Buckets..."
aws --endpoint-url="${ENDPOINT_URL}" s3 mb s3://ticketdesk-backups 2>/dev/null || echo "Bucket backups ya existe"
aws --endpoint-url="${ENDPOINT_URL}" s3 mb s3://ticketdesk-uploads 2>/dev/null || echo "Bucket uploads ya existe"
aws --endpoint-url="${ENDPOINT_URL}" s3 mb s3://ticketdesk-logs 2>/dev/null || echo "Bucket logs ya existe"

# Configurar versionado en backup bucket
aws --endpoint-url="${ENDPOINT_URL}" s3api put-bucket-versioning \
  --bucket ticketdesk-backups \
  --versioning-configuration Status=Enabled 2>/dev/null || echo "Versionado ya configurado"

# ========================================================================
# 3. Crear Secret Manager para credenciales
# ========================================================================
echo "Creando Secrets Manager..."
aws --endpoint-url="${ENDPOINT_URL}" secretsmanager create-secret \
  --name ticketdesk/db-credentials \
  --description "Database credentials for TicketDesk" \
  --secret-string '{"username":"ticketdesk","password":"ticketdesk123"}' \
  2>/dev/null || echo "Secret ya existe"

aws --endpoint-url="${ENDPOINT_URL}" secretsmanager create-secret \
  --name ticketdesk/api-keys \
  --description "API keys for integrations" \
  --secret-string '{"anthropic_api_key":"","teams_webhook":""}' \
  2>/dev/null || echo "Secret de API keys ya existe"

# ========================================================================
# 4. Crear Security Group (VPC)
# ========================================================================
echo "Configurando VPC y Security Groups..."

# Crear VPC
VPC_ID=$(aws --endpoint-url="${ENDPOINT_URL}" ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=ticketdesk-vpc}]' \
  --query 'Vpc.VpcId' \
  --output text 2>/dev/null) || VPC_ID=""

if [ ! -z "$VPC_ID" ] && [ "$VPC_ID" != "None" ]; then
  echo "VPC creado: $VPC_ID"

  # Crear subnet
  SUBNET_ID=$(aws --endpoint-url="${ENDPOINT_URL}" ec2 create-subnet \
    --vpc-id "$VPC_ID" \
    --cidr-block 10.0.1.0/24 \
    --query 'Subnet.SubnetId' \
    --output text 2>/dev/null) || SUBNET_ID=""

  # Crear security group
  SG_ID=$(aws --endpoint-url="${ENDPOINT_URL}" ec2 create-security-group \
    --group-name ticketdesk-sg \
    --description "Security group for TicketDesk" \
    --vpc-id "$VPC_ID" \
    --query 'GroupId' \
    --output text 2>/dev/null) || SG_ID=""

  if [ ! -z "$SG_ID" ] && [ "$SG_ID" != "None" ]; then
    echo "Security Group creado: $SG_ID"

    # Autorizar tráfico
    aws --endpoint-url="${ENDPOINT_URL}" ec2 authorize-security-group-ingress \
      --group-id "$SG_ID" \
      --protocol tcp \
      --port 5432 \
      --cidr 0.0.0.0/0 2>/dev/null || echo "Rule ya existe"

    aws --endpoint-url="${ENDPOINT_URL}" ec2 authorize-security-group-ingress \
      --group-id "$SG_ID" \
      --protocol tcp \
      --port 5050 \
      --cidr 0.0.0.0/0 2>/dev/null || echo "Rule ya existe"
  fi
else
  echo "VPC no se creó (puede ser esperado en LocalStack)"
fi

# ========================================================================
# 5. Crear CloudWatch Alarms para monitoreo
# ========================================================================
echo "Configurando CloudWatch..."

aws --endpoint-url="${ENDPOINT_URL}" cloudwatch put-metric-alarm \
  --alarm-name ticketdesk-db-cpu \
  --alarm-description "Database CPU usage" \
  --metric-name CPUUtilization \
  --namespace AWS/RDS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2 \
  2>/dev/null || echo "Alarma CPU ya existe"

aws --endpoint-url="${ENDPOINT_URL}" cloudwatch put-metric-alarm \
  --alarm-name ticketdesk-app-health \
  --alarm-description "Application health check" \
  --metric-name HealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  2>/dev/null || echo "Alarma health ya existe"

# ========================================================================
# 6. Crear ECS Cluster (Opcional - para despliegues contenido)
# ========================================================================
echo "Configurando ECS..."

aws --endpoint-url="${ENDPOINT_URL}" ecs create-cluster \
  --cluster-name ticketdesk-cluster \
  --tags key=Environment,value=development 2>/dev/null || echo "Cluster ya existe"

# ========================================================================
# 7. Crear SQS Queue (Opcional - para procesamiento asincrónico)
# ========================================================================
echo "Configurando SQS..."

aws --endpoint-url="${ENDPOINT_URL}" sqs create-queue \
  --queue-name ticketdesk-tasks \
  --attributes VisibilityTimeout=300,MessageRetentionPeriod=1209600 \
  2>/dev/null || echo "Queue ya existe"

# ========================================================================
# 8. Crear SNS Topics (Notificaciones)
# ========================================================================
echo "Configurando SNS..."

aws --endpoint-url="${ENDPOINT_URL}" sns create-topic \
  --name ticketdesk-notifications 2>/dev/null || echo "Topic ya existe"

aws --endpoint-url="${ENDPOINT_URL}" sns create-topic \
  --name ticketdesk-alerts 2>/dev/null || echo "Topic ya existe"

echo "=== Setup de LocalStack completado ==="
echo ""
echo "Recursos creados:"
echo "- S3: ticketdesk-backups, ticketdesk-uploads, ticketdesk-logs"
echo "- RDS: ticketdesk-db (endpoint: localhost:5432)"
echo "- Secrets Manager: ticketdesk/db-credentials, ticketdesk/api-keys"
echo "- ECS Cluster: ticketdesk-cluster"
echo "- SQS: ticketdesk-tasks"
echo "- SNS: ticketdesk-notifications, ticketdesk-alerts"
echo ""
