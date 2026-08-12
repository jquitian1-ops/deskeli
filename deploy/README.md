# Deploy — recursos de operación

## Rotación de logs

Ver `logrotate.conf` para el detalle. Resumen:

| Escenario | Cómo rotan los logs |
|---|---|
| **Coolify / Docker (producción)** | `GUNICORN_LOG_TO_FILES=0` (default). Gunicorn escribe a stdout/stderr, el runtime del contenedor lo captura y aplica su propio logging driver. En Coolify, configurar en el panel: `Settings → Logging → Driver: json-file, max-size=100m, max-files=10`. |
| **Bare metal / systemd** | `GUNICORN_LOG_TO_FILES=1` en el `.env`. Se escribe a `./logs/access.log` y `./logs/error.log`. Instalar el archivo `deploy/logrotate.conf` en `/etc/logrotate.d/deskeli` — rota diariamente, 30 días de retención, comprimido. |
| **Desarrollo local (Windows/Mac)** | `GUNICORN_LOG_TO_FILES=0` recomendado. Los logs salen por la terminal directamente. |

### Comandos útiles

```bash
# Ver logs en Coolify (via CLI de Docker/podman)
docker logs -f --tail=200 <container-id>

# Ver los últimos 500 líneas del access log si está en archivo
tail -n 500 -F logs/access.log

# Forzar rotación en el host (test)
sudo logrotate -f /etc/logrotate.d/deskeli

# Verificar la config sin ejecutar
sudo logrotate -d /etc/logrotate.d/deskeli
```

### Por qué stdout es la default

En un contenedor Docker el filesystem es efímero. Escribir a `logs/access.log` significa:
1. Los logs quedan **atrapados** en la capa de escritura del contenedor y se pierden al recrearlo.
2. El disco del contenedor puede saturarse silenciosamente si no hay logrotate corriendo dentro.
3. Los sistemas de observabilidad (Loki, Datadog, ELK) esperan leer `stdout` — no hacer `tail -f` a un archivo.

Por eso el default es stdout: **el runtime del contenedor** (`json-file` driver en Docker, o el driver que Coolify use) rota, comprime y expira los logs. Vos configurás los límites en Coolify una vez y te olvidás.
