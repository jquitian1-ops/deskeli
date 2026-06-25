# TicketDesk - Guía Completa de Despliegue con Terraform

Guía paso a paso para desplegar TicketDesk Enterprise en AWS usando Terraform.

## Prerrequisitos

### 1. Herramientas Necesarias

```bash
# macOS / Linux
brew install terraform aws-cli

# Windows (PowerShell as Admin)
choco install terraform awscli

# Verificar versiones
terraform version
aws --version
```

### 2. Credenciales AWS

Necesitas una cuenta AWS con acceso administrativo.

```bash
# Configurar credenciales
aws configure

# Datos necesarios:
# AWS Access Key ID: [tu_access_key]
# AWS Secret Access Key: [tu_secret_key]
# Default region: us-east-1
# Default output format: json
```

**Verificar acceso:**

```bash
aws sts get-caller-identity
# Debería mostrar: Account, UserId, Arn
```

### 3. ECR Docker Repository

Antes de desplegar, necesitas la imagen Docker en ECR (Elastic Container Registry).

```bash
# Crear repositorio
aws ecr create-repository \
  --repository-name ticketdesk \
  --region us-east-1

# Obtener cuenta ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Login a ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# Build y push (desde raíz del proyecto)
docker build -t ticketdesk:latest .
docker tag ticketdesk:latest $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ticketdesk:latest
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ticketdesk:latest
```

### 4. Certificado HTTPS (para staging/prod)

```bash
# Crear certificado autofirmado (dev/test)
aws acm request-certificate \
  --domain-name "ticketdesk.example.com" \
  --validation-method DNS \
  --region us-east-1

# Obtener ARN del certificado
aws acm list-certificates --region us-east-1 --query 'CertificateSummaryList[0].CertificateArn'
```

Actualizar en `environments/staging/terraform.tfvars`:

```hcl
acm_certificate_arn = "arn:aws:acm:us-east-1:123456789:certificate/xxxxx"
```

## Paso 1: Inicializar Terraform

```bash
cd C:\Users\jquitian\proyecto_funcionando\terraform

# Descargar providers
terraform init

# Validar sintaxis
terraform validate

# Formato correcto
terraform fmt -recursive

# Listar errores
terraform validate -json
```

## Paso 2: Configurar Variables por Ambiente

### Development

Editar `environments/dev/terraform.tfvars`:

```hcl
environment             = "dev"
container_image         = "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ticketdesk:latest"
alert_email             = "dev-team@example.com"
enable_https            = false
acm_certificate_arn     = ""
```

### Staging

Editar `environments/staging/terraform.tfvars`:

```hcl
environment             = "staging"
container_image         = "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ticketdesk:latest"
alert_email             = "oncall-staging@example.com"
enable_https            = true
acm_certificate_arn     = "arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/xxxxx"
```

### Production

Editar `environments/prod/terraform.tfvars`:

```hcl
environment             = "prod"
container_image         = "YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ticketdesk:prod-latest"
alert_email             = "oncall-prod@example.com"
enable_https            = true
acm_certificate_arn     = "arn:aws:acm:us-east-1:ACCOUNT_ID:certificate/xxxxx"
allowed_admin_cidrs     = ["YOUR_OFFICE_CIDR", "YOUR_VPN_CIDR"]
```

## Paso 3: Planificar Despliegue

```bash
# Ver qué se va a crear (modo dry-run)
terraform plan -var-file=environments/dev/terraform.tfvars -out=tfplan

# Detalles del plan
terraform show tfplan | head -100

# Exportar a JSON para review
terraform show -json tfplan > plan.json
```

**Verificar:**
- ✅ Número correcto de subnets, security groups
- ✅ Tamaño de instancias RDS/Redis correcto
- ✅ Backups configurados
- ✅ Logs habilitados

## Paso 4: Aplicar Infraestructura

```bash
# Development (rápido, ~15 minutos)
terraform apply -var-file=environments/dev/terraform.tfvars

# Staging (~20 minutos)
terraform apply -var-file=environments/staging/terraform.tfvars

# Production (~30 minutos, requiere confirmación)
terraform apply -var-file=environments/prod/terraform.tfvars
```

Terraform pedirá confirmación. Escribir `yes` para proceder.

```
Plan: 65 to add, 0 to change, 0 to destroy.

Do you want to perform these actions?
  Terraform will perform the actions described above.
  Only 'yes' will be accepted to approve.

  Enter a value: yes
```

## Paso 5: Obtener Conexión Strings

```bash
# Almacenar outputs en archivo
terraform output -json > outputs.json

# Ver database connection string
terraform output -raw database_connection_string

# Ver Redis URL
terraform output -raw redis_connection_string

# Ver ALB DNS
terraform output -raw alb_dns_name
```

**Copiar estos valores a `.env` de la aplicación:**

```bash
DATABASE_URL=postgresql://postgres:PASSWORD@prod-ticketdesk-db.c...amazonaws.com:5432/ticketdesk
REDIS_URL=redis://prod-ticketdesk-redis.c...amazonaws.com:6379
BACKUP_BUCKET=prod-ticketdesk-backups-123456789
```

## Paso 6: Configurar Secrets Manager

```bash
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 1. Actualizar SECRET_KEY
aws secretsmanager update-secret \
  --secret-id prod/ticketdesk/SECRET_KEY \
  --secret-string '{"SECRET_KEY":"'$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')'"}'

# 2. Actualizar Anthropic API Key
aws secretsmanager update-secret \
  --secret-id prod/ticketdesk/ANTHROPIC_API_KEY \
  --secret-string '{"ANTHROPIC_API_KEY":"sk-..."}'

# 3. Verificar
aws secretsmanager get-secret-value \
  --secret-id prod/ticketdesk/DB_CREDENTIALS \
  --query SecretString --output text
```

## Paso 7: Verificar Despliegue

```bash
# Ver recursos creados
terraform state list | wc -l
# Debería mostrar: ~65 recursos

# Verificar ALB está recibiendo tráfico
ALB_DNS=$(terraform output -raw alb_dns_name)
curl -I http://$ALB_DNS/api/health

# Respuesta esperada: HTTP/1.1 200 OK
```

### Health Checks

```bash
# 1. ECS Tasks corriendo
aws ecs list-tasks \
  --cluster prod-ticketdesk \
  --service-name prod-ticketdesk-app-service

# 2. RDS Database disponible
aws rds describe-db-instances \
  --db-instance-identifier prod-ticketdesk-db \
  --query 'DBInstances[0].DBInstanceStatus'
# Debería mostrar: "available"

# 3. Redis funcionando
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint)
redis-cli -h $REDIS_ENDPOINT -p 6379 ping
# Debería mostrar: PONG

# 4. S3 Bucket accesible
aws s3 ls s3://prod-ticketdesk-backups-123456789/
```

## Paso 8: Configurar DNS

```bash
# Obtener Zone ID del ALB
ZONE_ID=$(terraform output -raw alb_zone_id)
ALB_DNS=$(terraform output -raw alb_dns_name)

# Crear registro Route53
aws route53 create-resource-record-set \
  --hosted-zone-id Z123456 \
  --change-batch '{
    "Changes": [{
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "ticketdesk.example.com",
        "Type": "A",
        "AliasTarget": {
          "HostedZoneId": "'$ZONE_ID'",
          "DNSName": "'$ALB_DNS'",
          "EvaluateTargetHealth": true
        }
      }
    }]
  }'
```

## Paso 9: Monitoreo Post-Despliegue

### CloudWatch Logs

```bash
# Ver logs en tiempo real
aws logs tail /ecs/prod-ticketdesk-app --follow

# Filtrar errores
aws logs filter-log-events \
  --log-group-name /ecs/prod-ticketdesk-app \
  --filter-pattern "ERROR"
```

### Métricas

```bash
# CPU ECS
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=prod-ticketdesk-app-service \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum

# Conexiones RDS
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=prod-ticketdesk-db \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

## Paso 10: Configurar Backups

```bash
# Backup manual inicial
python3 scripts/backup.py

# Subir a S3
BACKUP_FILE=$(ls -t backups/*.json.gz | head -1)
aws s3 cp $BACKUP_FILE s3://prod-ticketdesk-backups-123456789/

# Verificar lifecycle policy
aws s3api get-bucket-lifecycle-configuration \
  --bucket prod-ticketdesk-backups-123456789
```

## Actualización de Infraestructura

### Cambiar CPU/Memoria ECS

```bash
# Editar variables
sed -i 's/task_cpu = 512/task_cpu = 1024/' environments/prod/terraform.tfvars

# Plan
terraform plan -var-file=environments/prod/terraform.tfvars

# Apply (el ALB reemplazará tasks)
terraform apply -var-file=environments/prod/terraform.tfvars
```

### Expandir Base de Datos

```bash
# Plan
terraform plan \
  -var-file=environments/prod/terraform.tfvars \
  -var="db_allocated_storage=500"

# Apply (RDS aumentará automáticamente)
terraform apply \
  -var-file=environments/prod/terraform.tfvars \
  -var="db_allocated_storage=500"
```

### Actualizar Imagen Docker

```bash
# Push nueva versión
docker tag ticketdesk:vX.Y.Z $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ticketdesk:vX.Y.Z
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/ticketdesk:vX.Y.Z

# Actualizar variable
sed -i 's|ticketdesk:latest|ticketdesk:vX.Y.Z|' environments/prod/terraform.tfvars

# Forzar new deployment
aws ecs update-service \
  --cluster prod-ticketdesk \
  --service prod-ticketdesk-app-service \
  --force-new-deployment

# Esperar rollout
aws ecs wait services-stable \
  --cluster prod-ticketdesk \
  --services prod-ticketdesk-app-service
```

## Destruir Infraestructura

**⚠️ CUIDADO: Esto eliminará toda la infraestructura y datos**

```bash
# Dev (sin confirmación de backups)
terraform destroy -var-file=environments/dev/terraform.tfvars -auto-approve

# Staging/Prod (requiere confirmación)
terraform destroy -var-file=environments/prod/terraform.tfvars

# Confirmar escribiendo: yes
```

## Troubleshooting

### Error: "InvalidParameterValue - Invalid DB instance identifier"

```bash
# RDS identifier tiene caracteres inválidos
# Solución: Renombrar en variables.tf
# Los nombres deben cumplir: [a-z][a-z0-9]*
```

### Error: "Instances from more than one IPv6 CIDR block"

```bash
# Solución: Asegurarse que subnets usnen mismo CIDR
# Validar en variables.tf:
# private_subnet_cidrs = ["10.0.10.0/24", "10.0.11.0/24"]
```

### ECS Tasks constantemente restarting

```bash
# Ver logs
aws logs tail /ecs/prod-ticketdesk-app --follow

# Ver task definition
aws ecs describe-task-definition \
  --task-definition prod-ticketdesk-app \
  --query 'taskDefinition.containerDefinitions[0].logConfiguration'

# Verificar secrets accesibles
aws secretsmanager get-secret-value --secret-id prod/ticketdesk/ANTHROPIC_API_KEY
```

### ALB returns 502 Bad Gateway

```bash
# 1. Verificar target health
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw target_group_arn)

# 2. Ver logs ECS
aws logs tail /ecs/prod-ticketdesk-app --follow

# 3. Verificar security group app allows 5050
aws ec2 describe-security-groups \
  --group-ids $(terraform output -raw app_security_group_id)

# 4. Reiniciar tasks
aws ecs update-service \
  --cluster prod-ticketdesk \
  --service prod-ticketdesk-app-service \
  --force-new-deployment
```

### Rollback a estado anterior

```bash
# Ver histórico de state
terraform state list

# Obtener backup automático
ls -la .terraform.tfstate.d/

# Restaurar
cp .terraform.tfstate.d/state.backup terraform.tfstate
terraform apply
```

## Cost Estimation

```bash
# Ver plan con costos estimados (requiere Terraform Cloud)
terraform plan -var-file=environments/prod/terraform.tfvars | \
  grep -E "^  \+"

# Costos aproximados:
# Dev:     $50-100/mes
# Staging: $200-400/mes
# Prod:    $1,500-2,500/mes
```

## Performance Tuning

### Reducir tiempo de inicio ECS

```hcl
# En modules/compute/main.tf, aumentar healthCheck.startPeriod
healthCheck = {
  startPeriod = 120  # Dar 2 minutos para app startup
}
```

### Mejorar latencia RDS

```hcl
# Aumentar IOPS
storage_iops = 5000  # De 3000 default

# Usar db.r5.2xlarge en prod
db_instance_class = "db.r5.2xlarge"
```

### Optimizar Redis

```hcl
# Usar read replicas para scaling
redis_num_cache_nodes = 5

# Habilitar cluster mode
automatic_failover_enabled = true
```

---

**Documento actualizado:** 2026-05-29
**Versión:** 1.0
