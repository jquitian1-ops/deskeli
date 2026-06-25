# Terraform Outputs Reference - TicketDesk

Después de ejecutar `terraform apply`, estos son los valores que obtienes para configurar la aplicación.

## Cómo Obtener Los Outputs

```bash
# Ver todos los outputs
terraform output

# Exportar como JSON
terraform output -json > outputs.json

# Ver un output específico
terraform output alb_dns_name
terraform output -raw database_connection_string

# Ejemplo completo
OUTPUTS=$(terraform output -json)
DATABASE_URL=$(echo $OUTPUTS | jq -r '.database_connection_string.value')
REDIS_URL=$(echo $OUTPUTS | jq -r '.redis_connection_string.value')
```

---

## Networking Outputs

### VPC

```
vpc_id: vpc-0a1b2c3d4e5f6g7h8
vpc_cidr: 10.0.0.0/16
```

**Uso:** Identificar la VPC para conectar recursos adicionales.

### Subnets

```
public_subnet_ids: [subnet-123abc, subnet-456def]
private_subnet_ids: [subnet-789ghi, subnet-012jkl]
```

**Uso:** Crear recursos en subnets específicas.

### NAT Gateway

```
nat_gateway_ip: 203.0.113.45
```

**Uso:** Configurar firewall corporativo para permitir salida de la app.

---

## Load Balancer Outputs

### ALB DNS

```
alb_dns_name: prod-ticketdesk-alb-123456789.us-east-1.elb.amazonaws.com
alb_zone_id: Z35SXDOTRQ7X7K
```

**Uso 1 - Acceso Directo (temporal):**
```bash
curl https://prod-ticketdesk-alb-123456789.us-east-1.elb.amazonaws.com/api/health
```

**Uso 2 - Crear DNS Record en Route53:**
```bash
aws route53 create-resource-record-set \
  --hosted-zone-id Z123456789 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "ticketdesk.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "Z35SXDOTRQ7X7K",
          "DNSName": "prod-ticketdesk-alb-123456789.us-east-1.elb.amazonaws.com",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

### ALB ARN

```
alb_arn: arn:aws:elasticloadbalancing:us-east-1:123456789:loadbalancer/app/prod-ticketdesk-alb/1234567890abcdef
```

**Uso:** Modificaciones de ALB vía AWS CLI o Lambda.

---

## ECS Compute Outputs

### Cluster

```
ecs_cluster_name: ticketdesk-prod
ecs_cluster_arn: arn:aws:ecs:us-east-1:123456789:cluster/ticketdesk-prod
```

**Usar en:**
```bash
aws ecs list-tasks --cluster ticketdesk-prod
aws ecs list-services --cluster ticketdesk-prod
```

### Service

```
ecs_service_name: prod-ticketdesk-app-service
ecs_service_arn: arn:aws:ecs:us-east-1:123456789:service/ticketdesk-prod/prod-ticketdesk-app-service
```

**Monitoreo:**
```bash
aws ecs describe-services \
  --cluster ticketdesk-prod \
  --services prod-ticketdesk-app-service
```

### Task Definition

```
ecs_task_definition_arn: arn:aws:ecs:us-east-1:123456789:task-definition/prod-ticketdesk-app:1
```

**Actualizar imagen:**
```bash
# Editar y crear nueva revisión
aws ecs register-task-definition \
  --cli-input-json file://task-definition.json

# Actualizar servicio a nueva revisión
aws ecs update-service \
  --cluster ticketdesk-prod \
  --service prod-ticketdesk-app-service \
  --task-definition prod-ticketdesk-app:2
```

### CloudWatch Logs

```
cloudwatch_log_group: /ecs/prod-ticketdesk-app
```

**Ver logs en tiempo real:**
```bash
aws logs tail /ecs/prod-ticketdesk-app --follow

# Con filtros
aws logs tail /ecs/prod-ticketdesk-app --follow --filter-pattern "ERROR"
```

---

## Database Outputs (RDS PostgreSQL)

### Connection String

```
database_connection_string: postgresql://postgres:xyzpassword123@prod-ticketdesk-db.c12345abcde.us-east-1.rds.amazonaws.com:5432/ticketdesk
```

**Usar en .env:**
```bash
DATABASE_URL=postgresql://postgres:xyzpassword123@prod-ticketdesk-db.c12345abcde.us-east-1.rds.amazonaws.com:5432/ticketdesk
```

**Descomponerla:**
- **User:** postgres
- **Password:** xyzpassword123
- **Host:** prod-ticketdesk-db.c12345abcde.us-east-1.rds.amazonaws.com
- **Port:** 5432
- **Database:** ticketdesk

### Endpoint

```
db_endpoint: prod-ticketdesk-db.c12345abcde.us-east-1.rds.amazonaws.com:5432
```

**Conexión con psql:**
```bash
psql -h prod-ticketdesk-db.c12345abcde.us-east-1.rds.amazonaws.com -U postgres -d ticketdesk
# Pedir password
```

### Database Name

```
db_name: ticketdesk
```

### Database Port

```
db_port: 5432
```

### Multi-AZ Status

```
db_multi_az: true  # En prod
```

**Verificar:**
```bash
aws rds describe-db-instances \
  --db-instance-identifier prod-ticketdesk-db \
  --query 'DBInstances[0].MultiAZ'
```

### Master Username

```
db_master_username: postgres
```

---

## Cache Outputs (Redis)

### Connection String

```
redis_connection_string: redis://prod-ticketdesk-redis.abc123.ng.0001.use1.cache.amazonaws.com:6379
```

**Usar en .env:**
```bash
REDIS_URL=redis://prod-ticketdesk-redis.abc123.ng.0001.use1.cache.amazonaws.com:6379
```

### Endpoint

```
redis_endpoint: prod-ticketdesk-redis.abc123.ng.0001.use1.cache.amazonaws.com:6379
```

**Test de conexión:**
```bash
redis-cli -h prod-ticketdesk-redis.abc123.ng.0001.use1.cache.amazonaws.com -p 6379 ping
# Respuesta: PONG
```

### Cluster ID

```
redis_cluster_id: prod-ticketdesk-redis
```

---

## Storage Outputs (S3)

### Backup Bucket Name

```
backup_bucket_name: prod-ticketdesk-backups-123456789
```

**Usar en .env:**
```bash
BACKUP_BUCKET=prod-ticketdesk-backups-123456789
```

**Subir backup:**
```bash
aws s3 cp backup.json.gz s3://prod-ticketdesk-backups-123456789/
```

**Listar backups:**
```bash
aws s3 ls s3://prod-ticketdesk-backups-123456789/ --recursive --human-readable --summarize
```

### Backup Bucket ARN

```
backup_bucket_arn: arn:aws:s3:::prod-ticketdesk-backups-123456789
```

### Bucket Domain Name

```
backup_bucket_domain_name: prod-ticketdesk-backups-123456789.s3.us-east-1.amazonaws.com
```

---

## Security Outputs

### KMS Key

```
kms_key_id: 12345678-1234-1234-1234-123456789012
kms_key_arn: arn:aws:kms:us-east-1:123456789:key/12345678-1234-1234-1234-123456789012
```

**Usar para encriptación adicional:**
```bash
aws kms encrypt \
  --key-id 12345678-1234-1234-1234-123456789012 \
  --plaintext sensitive_data
```

### Security Groups

```
app_security_group_id: sg-0a1b2c3d4e5f6g7h
db_security_group_id: sg-1a2b3c4d5e6f7g8h
cache_security_group_id: sg-2a3b4c5d6e7f8g9h
alb_security_group_id: sg-3a4b5c6d7e8f9g0h
```

**Revisar reglas:**
```bash
aws ec2 describe-security-groups \
  --group-ids sg-0a1b2c3d4e5f6g7h \
  --query 'SecurityGroups[0].IpPermissions'
```

### IAM Roles

```
ecs_task_execution_role_arn: arn:aws:iam::123456789:role/prod-ecs-task-execution-role
ecs_task_role_arn: arn:aws:iam::123456789:role/prod-ecs-task-role
```

---

## Monitoring Outputs

### CloudWatch Dashboard URL

```
dashboard_url: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=prod-ticketdesk
```

**Abrir directamente:**
```bash
# macOS
open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=prod-ticketdesk"

# Linux
xdg-open "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=prod-ticketdesk"

# Windows
start "https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=prod-ticketdesk"
```

### SNS Alert Topic

```
sns_alert_topic_arn: arn:aws:sns:us-east-1:123456789:prod-ticketdesk-alerts
```

**Publicar mensaje de test:**
```bash
aws sns publish \
  --topic-arn arn:aws:sns:us-east-1:123456789:prod-ticketdesk-alerts \
  --message "Test alert from Terraform" \
  --subject "TicketDesk Alert"
```

---

## Utility Outputs

### Environment

```
environment: prod
aws_region: us-east-1
```

### Terraform Version

```
terraform_version: ~> 1.0
```

### AWS Console Links

```json
{
  "vpc": "https://console.aws.amazon.com/vpc/home?region=us-east-1",
  "rds": "https://console.aws.amazon.com/rds/home?region=us-east-1",
  "ecs": "https://console.aws.amazon.com/ecs/v2/clusters/ticketdesk-prod",
  "s3": "https://s3.console.aws.amazon.com/s3/buckets/prod-ticketdesk-backups-123456789",
  "logs": "https://console.aws.amazon.com/logs/home?region=us-east-1"
}
```

---

## Script para Exportar Variables de Entorno

Guardar como `export-env.sh`:

```bash
#!/bin/bash

# Exportar outputs de Terraform a .env

OUTPUTS=$(terraform output -json)

# Database
DATABASE_URL=$(echo $OUTPUTS | jq -r '.database_connection_string.value')

# Redis
REDIS_URL=$(echo $OUTPUTS | jq -r '.redis_connection_string.value')

# S3
BACKUP_BUCKET=$(echo $OUTPUTS | jq -r '.backup_bucket_name.value')

# ALB
ALB_DNS=$(echo $OUTPUTS | jq -r '.alb_dns_name.value')

# ECS
CLUSTER_NAME=$(echo $OUTPUTS | jq -r '.ecs_cluster_name.value')
SERVICE_NAME=$(echo $OUTPUTS | jq -r '.ecs_service_name.value')

# Crear .env
cat > .env << EOF
DATABASE_URL=$DATABASE_URL
REDIS_URL=$REDIS_URL
BACKUP_BUCKET=$BACKUP_BUCKET
ALB_DNS=$ALB_DNS
ECS_CLUSTER=$CLUSTER_NAME
ECS_SERVICE=$SERVICE_NAME
EOF

echo ".env actualizado"
cat .env
```

**Ejecutar:**
```bash
chmod +x export-env.sh
./export-env.sh
```

---

## Ejemplo Completo: Iniciar Aplicación

```bash
# 1. Obtener todos los outputs
terraform output -json > outputs.json

# 2. Crear .env
./export-env.sh

# 3. Verificar conectividad
DATABASE_URL=$(terraform output -raw database_connection_string)
psql $DATABASE_URL -c "SELECT version();"

# 4. Verificar Redis
REDIS_URL=$(terraform output -raw redis_connection_string)
redis-cli -u $REDIS_URL ping

# 5. Verificar ALB
ALB_DNS=$(terraform output -raw alb_dns_name)
curl -I https://$ALB_DNS/api/health

# 6. Ver logs
aws logs tail /ecs/prod-ticketdesk-app --follow

# 7. Dashboard
open "$(terraform output -raw dashboard_url)"
```

---

**Última actualización:** 2026-05-29
