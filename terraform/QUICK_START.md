# TicketDesk Terraform - Quick Start (5 minutos)

Guía de inicio rápido para desplegar TicketDesk en AWS en 5 pasos.

## Requisitos Previos

```bash
# Instalar Terraform
brew install terraform  # macOS
choco install terraform # Windows

# Verificar
terraform --version  # ≥ 1.0

# Configurar AWS CLI
aws configure
# Ingresar: Access Key, Secret Key, región (us-east-1)
```

## 5 Pasos para Desplegar

### Paso 1: Clonar y Navegar (1 min)

```bash
cd C:\Users\jquitian\proyecto_funcionando\terraform
ls -la
# Deberías ver: main.tf, variables.tf, modules/, environments/
```

### Paso 2: Inicializar Terraform (2 min)

```bash
terraform init
# Descarga providers de AWS
# Inicializa estado local
```

**Resultado esperado:**
```
Terraform has been successfully initialized!
```

### Paso 3: Validar Configuración (1 min)

```bash
terraform validate
# Verifica sintaxis sin desplegar
```

**Resultado esperado:**
```
Success! The configuration is valid.
```

### Paso 4: Planificar Despliegue (1 min)

Para **DEVELOPMENT** (recomendado primero):

```bash
terraform plan -var-file=environments/dev/terraform.tfvars -out=tfplan
# Simula qué se va a crear
```

**Verificar:**
- ✓ ~65 recursos a crear
- ✓ 0 cambios, 0 destrucciones
- ✓ ALB, ECS, RDS, Redis, S3, etc.

### Paso 5: Aplicar (15-30 minutos según ambiente)

```bash
# Ver el plan
terraform show tfplan | head -50

# Aplicar (crear infraestructura)
terraform apply tfplan
# O sin plan previo:
terraform apply -var-file=environments/dev/terraform.tfvars
# Escribir 'yes' para confirmar
```

**Monitorear:**
```bash
# En otra terminal, ver los recursos creándose
watch -n 5 'aws ec2 describe-vpcs --query "Vpcs[0]"'
```

---

## Después del Despliegue

### Obtener URLs y Conexiones

```bash
# Ver todos los outputs
terraform output

# Exportar a JSON
terraform output -json > outputs.json

# URLs importantes
echo "ALB DNS: $(terraform output -raw alb_dns_name)"
echo "Database: $(terraform output -raw database_connection_string)"
echo "Redis: $(terraform output -raw redis_connection_string)"
echo "Dashboard: $(terraform output -raw dashboard_url)"
```

### Verificar Salud

```bash
ALB_DNS=$(terraform output -raw alb_dns_name)

# Test HTTP
curl -I http://$ALB_DNS
# Respuesta: 301 Moved Permanently (redirect a HTTPS)

# Ver CloudWatch Logs
aws logs tail /ecs/dev-ticketdesk-app --follow
```

### Crear archivo .env

```bash
# Copiar conexiones a .env de la aplicación
OUTPUTS=$(terraform output -json)

cat > ../app/.env << EOF
DATABASE_URL=$(echo $OUTPUTS | jq -r '.database_connection_string.value')
REDIS_URL=$(echo $OUTPUTS | jq -r '.redis_connection_string.value')
BACKUP_BUCKET=$(echo $OUTPUTS | jq -r '.backup_bucket_name.value')
EOF

cat ../app/.env
```

---

## Cambiar a Staging o Producción

### Desplegar Staging

```bash
# Plan
terraform plan -var-file=environments/staging/terraform.tfvars -out=tfplan-staging

# Verificar cambios
terraform show tfplan-staging | grep -E "create|destroy" | head -20

# Apply
terraform apply tfplan-staging
# O directo:
terraform apply -var-file=environments/staging/terraform.tfvars
```

**Diferencias respecto a Dev:**
- Multi-AZ RDS
- HTTPS con certificado ACM
- 2 tasks mínimo
- Redis con failover
- CloudFront CDN

### Desplegar Producción

⚠️ **NOTA:** Requiere más preparación

```bash
# 1. Crear certificado HTTPS
aws acm request-certificate \
  --domain-name "ticketdesk.example.com" \
  --validation-method DNS
# Nota el ARN del certificado

# 2. Actualizar prod/terraform.tfvars
vi environments/prod/terraform.tfvars
# Cambiar:
# - acm_certificate_arn = "arn:aws:acm:..."
# - alert_email = "oncall-prod@example.com"
# - allowed_admin_cidrs = ["YOUR_IP/32"]

# 3. Plan
terraform plan -var-file=environments/prod/terraform.tfvars -out=tfplan-prod

# 4. Review manual
terraform show tfplan-prod | less

# 5. Apply
terraform apply tfplan-prod
```

---

## Troubleshooting

### Error: "InvalidParameterValue - Invalid DB instance identifier"

Solución: El nombre tiene caracteres inválidos. Verificar en `variables.tf` que el nombre cumple pattern `[a-z][a-z0-9]*`.

### Error: "Terraform is trying to ask a question but doesn't have input enabled"

Solución: Usar `-auto-approve` o pasar el plan con `-out`:
```bash
terraform apply -var-file=environments/dev/terraform.tfvars -auto-approve
```

### Outputs no aparecen

```bash
# Asegurarse que apply completó
terraform state list | wc -l
# Debería ser ~65 recursos

# Si no están, verificar que apply finalizó
terraform state show aws_lb.main
```

### ALB devuelve 502 Bad Gateway

```bash
# 1. Verificar tasks corriendo
CLUSTER=$(terraform output -raw ecs_cluster_name)
aws ecs list-tasks --cluster $CLUSTER

# 2. Ver logs
aws logs tail /ecs/$CLUSTER --follow

# 3. Reiniciar tasks
SERVICE=$(terraform output -raw ecs_service_name)
aws ecs update-service \
  --cluster $CLUSTER \
  --service $SERVICE \
  --force-new-deployment
```

---

## Limpiar / Destruir

⚠️ **CUIDADO:** Esto eliminará TODA la infraestructura

```bash
# Development (sin confirmación)
terraform destroy -var-file=environments/dev/terraform.tfvars -auto-approve

# Staging/Prod (requiere confirmación)
terraform destroy -var-file=environments/staging/terraform.tfvars
# Escribir 'yes' para confirmar

# Verificar que se eliminó
terraform state list
# Debería estar vacío
```

---

## Documentación Completa

Para más detalles, consultar:

| Documento | Contenido |
|-----------|----------|
| **README.md** | Inicio rápido, operaciones comunes |
| **DEPLOYMENT_GUIDE.md** | Paso a paso detallado con validaciones |
| **INFRASTRUCTURE_OVERVIEW.md** | Arquitectura, diagramas, componentes |
| **OUTPUTS_REFERENCE.md** | Referencia de todos los outputs |
| **TESTING_CHECKLIST.md** | Validación post-deployment |

---

## Resumen de Recursos Creados

### Development (~$43/mes)
```
✓ VPC con subnets públicas y privadas
✓ ALB en puerto 80 (HTTP)
✓ 1 task ECS (Flask app)
✓ RDS db.t3.micro (PostgreSQL)
✓ Redis 1 nodo
✓ S3 bucket para backups
✓ CloudWatch logs
```

### Staging (~$141/mes)
```
✓ VPC multi-AZ
✓ ALB en puerto 443 (HTTPS)
✓ 2-4 tasks ECS con auto-scaling
✓ RDS db.t3.small Multi-AZ
✓ Redis 2 nodos con failover
✓ CloudFront CDN
✓ WAF habilitado
```

### Production (~$851/mes)
```
✓ VPC 3 AZs
✓ ALB HTTPS con certificate
✓ 3-10 tasks ECS con auto-scaling
✓ RDS db.r5.large Multi-AZ
✓ Redis 3 nodos Multi-AZ
✓ Performance Insights
✓ Enhanced Monitoring
✓ Full logging y alertas
```

---

## Comandos Útiles

```bash
# Ver estado actual
terraform state list
terraform state show aws_rds_db_instance.main

# Exportar outputs
terraform output -json > outputs.json

# Actualizar single variable
terraform apply \
  -var-file=environments/prod/terraform.tfvars \
  -var="ecs_desired_count=5"

# Ver diffs antes de aplicar
terraform plan -var-file=environments/prod/terraform.tfvars | grep -A5 -B5 "~"

# Debug
TF_LOG=DEBUG terraform plan

# Formato
terraform fmt -recursive

# Validar
terraform validate
```

---

## Siguiente Paso

1. **Completar setup:** Editar `environments/{env}/terraform.tfvars` con valores específicos
2. **Desplegar:** Ejecutar `terraform apply -var-file=environments/dev/terraform.tfvars`
3. **Verificar:** Consultar `TESTING_CHECKLIST.md`
4. **Conectar app:** Ver `OUTPUTS_REFERENCE.md` para connection strings

---

**¡Listo para desplegar!** 🚀

Duración estimada: 5 min (plan) + 15 min (apply en dev) = **20 minutos total**

Para preguntas detalladas, consultar documentación en esta carpeta.
