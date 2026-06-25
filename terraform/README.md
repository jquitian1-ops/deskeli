# TicketDesk Enterprise - Terraform Infrastructure

Infraestructura completa de AWS para TicketDesk Enterprise usando Terraform. Soporta despliegue en dev, staging y producción con arquitectura de alta disponibilidad.

## Requisitos Previos

- **Terraform:** ≥ 1.0
- **AWS CLI:** ≥ 2.10
- **AWS Account:** Con permisos administrativos
- **AWS Credentials:** Configuradas en `~/.aws/credentials` o variables de entorno

```bash
# Verificar instalación
terraform --version
aws --version
```

## Estructura del Proyecto

```
terraform/
├── main.tf                    # Punto de entrada principal
├── variables.tf              # Definiciones de variables
├── outputs.tf                # Valores de salida
├── terraform.tfvars          # Valores por defecto
├── .terraformrc              # Configuración local
├── .gitignore               # Archivos ignorados
├── modules/
│   ├── vpc/                 # Networking (VPC, subnets, NAT)
│   ├── security/            # IAM roles, security groups, KMS
│   ├── database/            # RDS PostgreSQL
│   ├── cache/               # ElastiCache Redis
│   ├── storage/             # S3 backups
│   ├── lb/                  # Application Load Balancer
│   ├── compute/             # ECS Fargate cluster
│   └── monitoring/          # CloudWatch dashboards & alarms
└── environments/
    ├── dev/                 # Configuración desarrollo
    ├── staging/             # Configuración staging
    └── prod/                # Configuración producción
```

## Inicio Rápido

### 1. Preparar las Credenciales AWS

```bash
# Opción A: Usar credenciales guardadas
aws configure
# Ingresar: AWS Access Key ID, Secret Access Key, región (us-east-1)

# Opción B: Variables de entorno
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-east-1"
```

### 2. Inicializar Terraform

```bash
cd C:\Users\jquitian\proyecto_funcionando\terraform

# Descargar providers y módulos
terraform init

# Validar configuración
terraform validate
```

### 3. Despliegue en Desarrollo

```bash
# Ver plan (qué se va a crear)
terraform plan -var-file=environments/dev/terraform.tfvars

# Aplicar cambios
terraform apply -var-file=environments/dev/terraform.tfvars

# Confirmar con 'yes'
```

### 4. Obtener Outputs

```bash
# Ver todos los outputs
terraform output

# Exportar a archivo
terraform output -json > outputs.json

# Ver output específico
terraform output alb_dns_name
terraform output database_connection_string
```

## Configuración por Ambiente

### Desarrollo

```bash
terraform plan -var-file=environments/dev/terraform.tfvars
terraform apply -var-file=environments/dev/terraform.tfvars
```

**Características:**
- Single AZ (sin HA)
- Instancias pequeñas (db.t3.micro, cache.t3.micro)
- Sin Multi-AZ para RDS
- HTTP only (no HTTPS)
- 1 task ECS mínimo
- Logs retenidos 7 días

### Staging

```bash
terraform plan -var-file=environments/staging/terraform.tfvars
terraform apply -var-file=environments/staging/terraform.tfvars
```

**Características:**
- Multi-AZ para alta disponibilidad
- Instancias medianas (db.t3.small, cache.t3.small)
- HTTPS con ACM certificate
- 2 tasks ECS mínimo
- Logs retenidos 14 días
- CDN y WAF habilitados

### Producción

```bash
terraform plan -var-file=environments/prod/terraform.tfvars
terraform apply -var-file=environments/prod/terraform.tfvars
```

**Características:**
- 3 AZs para máxima redundancia
- Instancias grandes (db.r5.large, cache.r6g.xlarge)
- Multi-AZ obligatorio para RDS
- HTTPS con certificado
- 3 tasks ECS mínimo, hasta 10 máximo
- Logs retenidos 365 días
- Performance Insights habilitado
- MFA delete para S3

## Variables Importantes

Editar en `environments/{env}/terraform.tfvars`:

```hcl
# Imagen Docker (requiere registry ECR)
container_image = "123456789.dkr.ecr.us-east-1.amazonaws.com/ticketdesk:latest"

# Certificado HTTPS
acm_certificate_arn = "arn:aws:acm:us-east-1:123456789:certificate/xxxxx"

# Email para alertas
alert_email = "oncall@example.com"

# CIDR de acceso administrativo (prod)
allowed_admin_cidrs = ["203.0.113.0/24", "198.51.100.0/24"]
```

## Operaciones Comunes

### Ver estado actual

```bash
terraform state list
terraform state show aws_db_instance.main
```

### Actualizar una variable

```bash
# Cambiar task count
terraform apply -var-file=environments/prod/terraform.tfvars \
  -var="ecs_desired_count=4"
```

### Destruir infraestructura

```bash
# Ver qué se va a eliminar
terraform destroy -var-file=environments/prod/terraform.tfvars

# Confirmar con 'yes'
```

### Importar recursos existentes

```bash
# Si ya tienes un RDS y quieres tracked por Terraform
terraform import -var-file=environments/prod/terraform.tfvars \
  aws_db_instance.main instance-identifier
```

## Configurar Backend Remoto (Recomendado)

Descomentar en `main.tf`:

```hcl
terraform {
  backend "s3" {
    bucket         = "ticketdesk-terraform-state"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

Crear bucket y tabla primero:

```bash
aws s3api create-bucket --bucket ticketdesk-terraform-state --region us-east-1
aws s3api put-bucket-versioning --bucket ticketdesk-terraform-state --versioning-configuration Status=Enabled

# DynamoDB para locks
aws dynamodb create-table \
  --table-name terraform-locks \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

## Monitoreo y Dashboards

Después de aplicar:

1. **CloudWatch Dashboard:**
   - URL: `https://console.aws.amazon.com/cloudwatch/home#dashboards:name={environment}-ticketdesk`

2. **RDS Performance Insights:**
   - URL: `https://console.aws.amazon.com/rds/home`

3. **ECS Cluster:**
   - URL: `https://console.aws.amazon.com/ecs/v2/clusters/{cluster-name}`

4. **S3 Backups:**
   - Verificar bucket: `{environment}-ticketdesk-backups-{account-id}`
   - Lifecycle policies automáticas cada 30 días

## Seguridad

### Secrets Management

Las credenciales se almacenan en **AWS Secrets Manager**:
- `{env}/ticketdesk/SECRET_KEY` — Flask secret
- `{env}/ticketdesk/DB_CREDENTIALS` — PostgreSQL user/password
- `{env}/ticketdesk/ANTHROPIC_API_KEY` — API key

**ACTUALIZAR en producción:**

```bash
aws secretsmanager update-secret \
  --secret-id prod/ticketdesk/ANTHROPIC_API_KEY \
  --secret-string '{"ANTHROPIC_API_KEY": "sk-..."}'
```

### Encriptación

- **RDS:** KMS encryption at rest
- **Redis:** Encryption at rest (AES-256)
- **S3:** Server-side encryption con KMS
- **Logs:** Encriptados en CloudWatch

### Acceso de Red

- RDS: Solo desde subnets privadas + security group app
- Redis: Solo desde subnets privadas + security group app
- ALB: Acceso público en puertos 80/443
- NAT Gateway: Para salida de subnets privadas

## Troubleshooting

### Error: "Resource Already Exists"

```bash
# Listar recursos importados
terraform state list

# Si necesitas recrear:
terraform destroy -target=aws_db_instance.main
terraform apply
```

### ECS Tasks no iniciando

```bash
# Ver logs
aws logs tail /ecs/dev-ticketdesk-app --follow

# Ver task definition
terraform show aws_ecs_task_definition.main
```

### ALB retorna 502 Bad Gateway

1. Verificar health check: `aws elbv2 describe-target-health --target-group-arn {arn}`
2. Ver logs ECS: `aws logs tail /ecs/{env}-ticketdesk-app`
3. Verificar security groups (app + ALB)

### Base de datos llena

```bash
# Ver almacenamiento usado
aws rds describe-db-instances --query 'DBInstances[0].{Size:AllocatedStorage,Used:StorageUsed}'

# Expandir volumen
terraform apply -var="db_allocated_storage=200"
```

## Cost Optimization

- **Dev:** `t3.micro` instances, single-AZ, 1 task mínimo → ~$50/mes
- **Staging:** `t3.small` instances, multi-AZ, 2 tasks → ~$300/mes
- **Prod:** `r5.large` instances, 3 AZs, 3-10 tasks, Performance Insights → ~$2,000/mes

**Tips:**
- Usar FARGATE_SPOT para tasks no-críticas (50% descuento)
- Reducir log retention en dev (7 días vs 365)
- Usar RDS reservadas en prod (-40%)

## Actualización de Terraform

```bash
# Actualizar providers
terraform init -upgrade

# Ver cambios
terraform plan

# Aplicar
terraform apply
```

## Support & Documentation

- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS Best Practices](https://docs.aws.amazon.com/whitepapers/)
- [TicketDesk CLAUDE.md](../CLAUDE.md)

---

**Última actualización:** 2026-05-29
**Versión:** 2.1
**Mantenedor:** TicketDesk Team
