# Terraform Testing & Validation Checklist - TicketDesk

Lista de verificación para validar que la infraestructura está correctamente desplegada.

## Pre-Deployment Testing

### [ ] Validación de Código Terraform

```bash
# Formato
terraform fmt -recursive
# Debería completar sin errores

# Validación
terraform validate
# Debería mostrar: Success! The configuration is valid.

# Linting (opcional, requiere tflint)
tflint --init
tflint
```

### [ ] Verificación de Variables

```bash
# Validar variables.tf
terraform validate -var-file=environments/prod/terraform.tfvars

# Simular plan
terraform plan -var-file=environments/prod/terraform.tfvars -out=test.tfplan

# Verificar cantidad de recursos
terraform show test.tfplan | grep -c "^  "
# Debería ser ~65 recursos
```

### [ ] Revisión de Secrets

```bash
# Verificar secrets no están en código
grep -r "password\|secret\|api.*key" --include="*.tf" .
# No debería haber valores en claro

# Todos deberían ser referencias a variables o random_password
grep -r "sensitive = true" --include="*.tf" .
# Debería haber outputs sensibles marcados
```

### [ ] AWS Permissions

```bash
# Verificar permisos necesarios
aws iam get-user
# Debería retornar Usuario corriente

# Crear policy simulada
aws iam simulate-principal-policy \
  --policy-source-arn $(aws sts get-caller-identity --query Arn --output text) \
  --action-names ec2:CreateVpc rds:CreateDBInstance
```

---

## Post-Deployment Testing

### [ ] Infrastructure Health

**VPC & Networking**

```bash
# Verificar VPC creada
VPC_ID=$(terraform output -raw vpc_id)
aws ec2 describe-vpcs --vpc-ids $VPC_ID
# Status debe ser "available"

# Verificar subnets
aws ec2 describe-subnets \
  --filters "Name=vpc-id,Values=$VPC_ID" \
  --query 'Subnets[*].{Id:SubnetId,State:State,AZ:AvailabilityZone}'
# Todos deben estar "available"

# Verificar NAT Gateway
NAT_IP=$(terraform output -raw nat_gateway_ip)
echo "NAT Gateway IP: $NAT_IP"
```

**Load Balancer**

```bash
# Verificar ALB health
ALB_ARN=$(terraform output -raw alb_arn)
aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN

# Verificar target group health
TG_ARN=$(terraform output -raw target_group_arn)
aws elbv2 describe-target-health --target-group-arn $TG_ARN
# HealthState debe ser "healthy" para todos los targets

# Test HTTP
ALB_DNS=$(terraform output -raw alb_dns_name)
curl -I http://$ALB_DNS
# Status: 301 (redirect a HTTPS)

curl -I https://$ALB_DNS
# Status: 502 (normal si app no está lista)
```

**ECS Cluster**

```bash
# Verificar cluster
CLUSTER=$(terraform output -raw ecs_cluster_name)
aws ecs describe-clusters --clusters $CLUSTER

# Listar servicios
aws ecs list-services --cluster $CLUSTER

# Verificar tasks corriendo
aws ecs list-tasks \
  --cluster $CLUSTER \
  --service-name prod-ticketdesk-app-service

# Ver status de tasks
aws ecs describe-tasks \
  --cluster $CLUSTER \
  --tasks $(aws ecs list-tasks --cluster $CLUSTER --query 'taskArns[0]' --output text) \
  --query 'tasks[0].{Status:lastStatus,Health:healthStatus}'
# lastStatus debe ser "RUNNING"

# Ver logs
aws logs tail /ecs/$CLUSTER --follow
```

**RDS Database**

```bash
# Verificar instancia RDS
DB_ID=$(terraform output -raw db_instance_id)
aws rds describe-db-instances --db-instance-identifier $DB_ID \
  --query 'DBInstances[0].{Status:DBInstanceStatus,MultiAZ:MultiAZ,Engine:Engine}'

# Verificar Multi-AZ (prod)
aws rds describe-db-instances --db-instance-identifier $DB_ID \
  --query 'DBInstances[0].MultiAZ'
# Debe ser true en prod

# Probar conexión
DB_ENDPOINT=$(terraform output -raw db_endpoint)
# psql -h $DB_ENDPOINT -U postgres -d ticketdesk -c "SELECT version();"
# (Requiere psql y acceso desde red)

# Verificar backups
aws rds describe-db-instances --db-instance-identifier $DB_ID \
  --query 'DBInstances[0].{BackupWindow:PreferredBackupWindow,RetentionDays:BackupRetentionPeriod}'

# Ver snapshots
aws rds describe-db-snapshots \
  --db-instance-identifier $DB_ID \
  --query 'DBSnapshots[*].{Name:DBSnapshotIdentifier,Status:Status,Created:SnapshotCreateTime}'
```

**Redis Cache**

```bash
# Verificar cluster
REDIS_ID=$(terraform output -raw redis_cluster_id)
aws elasticache describe-replication-groups \
  --replication-group-id $REDIS_ID \
  --query 'ReplicationGroups[0].{Status:Status,Engine:Engine,NumCacheClusters:MemberClusters}'

# Probar conexión
REDIS_ENDPOINT=$(terraform output -raw redis_endpoint | cut -d: -f1)
# redis-cli -h $REDIS_ENDPOINT -p 6379 ping
# Debe responder PONG
```

**S3 Storage**

```bash
# Verificar bucket
BUCKET=$(terraform output -raw backup_bucket_name)
aws s3api head-bucket --bucket $BUCKET
# Sin errores = existe y tienes acceso

# Ver configuración
aws s3api get-bucket-versioning --bucket $BUCKET
aws s3api get-bucket-encryption --bucket $BUCKET
aws s3api get-bucket-lifecycle-configuration --bucket $BUCKET

# Verificar permisos
aws s3 ls s3://$BUCKET/
# Debería estar vacío inicialmente
```

### [ ] Security Validation

**IAM Roles**

```bash
# Verificar roles creados
aws iam list-roles --query 'Roles[?contains(RoleName, `prod`)]' | grep RoleName

# Ver permisos
ROLE=$(terraform output -raw ecs_task_execution_role_arn | cut -d/ -f2)
aws iam list-attached-role-policies --role-name $ROLE
aws iam list-role-policies --role-name $ROLE
```

**Security Groups**

```bash
# Verificar security groups
APP_SG=$(terraform output -raw app_security_group_id)
DB_SG=$(terraform output -raw db_security_group_id)
CACHE_SG=$(terraform output -raw cache_security_group_id)
ALB_SG=$(terraform output -raw alb_security_group_id)

# Revisar reglas ALB (debe permitir 80 y 443)
aws ec2 describe-security-groups \
  --group-ids $ALB_SG \
  --query 'SecurityGroups[0].IpPermissions'

# Revisar reglas App (debe permitir 5050 solo desde ALB)
aws ec2 describe-security-groups \
  --group-ids $APP_SG \
  --query 'SecurityGroups[0].IpPermissions'

# Revisar reglas DB (debe permitir 5432 solo desde App SG)
aws ec2 describe-security-groups \
  --group-ids $DB_SG \
  --query 'SecurityGroups[0].IpPermissions'
```

**Encryption**

```bash
# Verificar KMS key existe
KMS_KEY=$(terraform output -raw kms_key_id)
aws kms describe-key --key-id $KMS_KEY

# Verificar rotación habilitada
aws kms get-key-rotation-status --key-id $KMS_KEY

# Verificar RDS encriptado
aws rds describe-db-instances --db-instance-identifier $DB_ID \
  --query 'DBInstances[0].StorageEncrypted'
# Debe ser true

# Verificar S3 encriptado
aws s3api get-bucket-encryption --bucket $BUCKET
```

**Secrets Manager**

```bash
# Listar secrets
aws secretsmanager list-secrets --query 'SecretList[?contains(Name, `prod`)].Name'

# Verificar acceso (sin ver contenido)
aws secretsmanager get-secret-value \
  --secret-id prod/ticketdesk/SECRET_KEY \
  --query 'ARN'

# Verificar están encriptadas con KMS
aws secretsmanager describe-secret \
  --secret-id prod/ticketdesk/SECRET_KEY \
  --query '{Name:Name,KmsKeyId:KmsKeyId,LastRotated:LastRotatedDate}'
```

### [ ] Monitoring & Logging

**CloudWatch Logs**

```bash
# Verificar log groups
aws logs describe-log-groups \
  --log-group-name-prefix /ecs/prod

# Ver logs recientes
aws logs tail /ecs/prod-ticketdesk-app --max-items 20

# Buscar errores
aws logs filter-log-events \
  --log-group-name /ecs/prod-ticketdesk-app \
  --filter-pattern "ERROR" \
  --query 'events[*].message'

# Ver estadísticas
aws logs describe-log-streams \
  --log-group-name /ecs/prod-ticketdesk-app \
  --query 'logStreams[0].{Name:logStreamName,Created:creationTime,Size:storedBytes}'
```

**CloudWatch Alarms**

```bash
# Listar alarms
aws cloudwatch describe-alarms \
  --query 'MetricAlarms[*].{Name:AlarmName,State:StateValue,Threshold:Threshold}' | head -20

# Ver alarms en ALARM state
aws cloudwatch describe-alarms \
  --state-value ALARM \
  --query 'MetricAlarms[*].{Name:AlarmName,Reason:StateReason}'

# Verificar SNS topic
SNS_TOPIC=$(terraform output -raw sns_alert_topic_arn)
aws sns get-topic-attributes --topic-arn $SNS_TOPIC
```

**CloudWatch Dashboard**

```bash
# Verificar dashboard existe
DASHBOARD=$(terraform output -raw dashboard_url | grep -oP 'name=\K[^&]*')
aws cloudwatch get-dashboard --dashboard-name $DASHBOARD

# Abrir en navegador
echo "Dashboard URL: $(terraform output -raw dashboard_url)"
```

### [ ] Performance Baseline

**Network Latency**

```bash
# Ping a ALB
ALB_DNS=$(terraform output -raw alb_dns_name)
for i in {1..5}; do
  curl -w "Time: %{time_total}s\n" -o /dev/null -s https://$ALB_DNS/api/health
done
# Debería ser <500ms
```

**Database Latency**

```bash
# Conectar y hacer query
# psql -h $DB_ENDPOINT -U postgres -c "EXPLAIN ANALYZE SELECT 1;"
# Debería ser <100ms

# Ver via CloudWatch
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name ReadLatency \
  --dimensions Name=DBInstanceIdentifier,Value=$DB_ID \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

**Redis Performance**

```bash
# Conectar y hacer PING
# redis-cli -h $REDIS_ENDPOINT -p 6379 PING
# PONG (should be instant)

# Ver memory usage
# redis-cli -h $REDIS_ENDPOINT -p 6379 INFO memory
```

---

## Load Testing

### [ ] Simulate User Traffic

```bash
# Usando Apache Bench (ab)
ALB_DNS=$(terraform output -raw alb_dns_name)

ab -n 1000 -c 10 https://$ALB_DNS/api/health
# Requests per second: >100
# Failed requests: 0

# Usando wrk (más realista)
wrk -t4 -c100 -d30s https://$ALB_DNS/api/health
```

### [ ] Monitor under Load

```bash
# En otra terminal, monitorear
watch -n 1 'aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=prod-ticketdesk-app-service \
  --start-time $(date -u -d "1 min ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average'

# CPU no debería superar 80%
# Memory no debería superar 85%
```

---

## Disaster Recovery Testing

### [ ] RDS Failover

```bash
# Forzar failover (si Multi-AZ)
DB_ID=$(terraform output -raw db_instance_id)
aws rds reboot-db-instance \
  --db-instance-identifier $DB_ID \
  --force-failover
  
# Esperar failover
aws rds wait db-instance-available \
  --db-instance-identifier $DB_ID

# Verificar
aws rds describe-db-instances \
  --db-instance-identifier $DB_ID \
  --query 'DBInstances[0].PendingModifiedValues'
# Debería estar vacío si completó
```

### [ ] Database Restore from Snapshot

```bash
# Listar snapshots
LATEST_SNAPSHOT=$(aws rds describe-db-snapshots \
  --db-instance-identifier $DB_ID \
  --query 'DBSnapshots | sort_by(@, &SnapshotCreateTime) | [-1].DBSnapshotIdentifier' \
  --output text)

# Restaurar a instancia test
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier $DB_ID-restore-test \
  --db-snapshot-identifier $LATEST_SNAPSHOT

# Esperar a que esté listo
aws rds wait db-instance-available \
  --db-instance-identifier $DB_ID-restore-test

# Conectar y verificar
# psql -h $DB_ID-restore-test.xxxxx.us-east-1.rds.amazonaws.com -U postgres

# Eliminar instancia test
aws rds delete-db-instance \
  --db-instance-identifier $DB_ID-restore-test \
  --skip-final-snapshot
```

### [ ] S3 Backup Restore

```bash
# Listar backups
BUCKET=$(terraform output -raw backup_bucket_name)
aws s3 ls s3://$BUCKET/ --human-readable

# Descargar backup
LATEST_BACKUP=$(aws s3 ls s3://$BUCKET/ | tail -1 | awk '{print $NF}')
aws s3 cp s3://$BUCKET/$LATEST_BACKUP ./restore/

# Verificar integridad
gunzip -t restore/$LATEST_BACKUP
```

---

## Final Validation Checklist

- [ ] VPC con subnets públicas y privadas
- [ ] Internet Gateway y NAT Gateway funcionales
- [ ] ALB recibiendo tráfico en puertos 80/443
- [ ] ECS tasks corriendo y healthy
- [ ] RDS disponible con Multi-AZ (prod)
- [ ] Redis cluster activo
- [ ] S3 bucket con versionado y encriptación
- [ ] Security groups restrictivos
- [ ] IAM roles con permisos correctos
- [ ] Secrets Manager con credenciales
- [ ] CloudWatch logs y alarms activas
- [ ] Dashboard visible con métricas
- [ ] Latencia <500ms para API calls
- [ ] CPU <80% y Memory <85% en carga normal
- [ ] Backups automáticos habilitados
- [ ] Encriptación end-to-end

---

**Documento actualizado:** 2026-05-29
