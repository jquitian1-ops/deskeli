// TIMEOUT CON AVISO RF-01-13
// Detectar inactividad y mostrar aviso de timeout (15 min inactividad + 60s aviso)

let lastActivity = Date.now();
const TIMEOUT_MINUTES = 15;
const WARNING_SECONDS = 60;
const TIMEOUT_MS = TIMEOUT_MINUTES * 60 * 1000;
const WARNING_MS = TIMEOUT_MS - (WARNING_SECONDS * 1000);

function resetActivityTimer() {
    lastActivity = Date.now();
}

function checkInactivity() {
    const elapsed = Date.now() - lastActivity;

    if (elapsed >= WARNING_MS && elapsed < TIMEOUT_MS) {
        showTimeoutWarning();
    } else if (elapsed >= TIMEOUT_MS) {
        // Logout automático
        window.location.href = '/logout';
    }
}

function showTimeoutWarning() {
    const warning = document.getElementById('timeoutWarning');
    if (!warning || warning.classList.contains('active')) return;

    warning.classList.add('active');
    startCountdown();
}

function startCountdown() {
    let remaining = WARNING_SECONDS;
    const display = document.getElementById('countdownDisplay');

    const countdown = setInterval(() => {
        remaining--;
        if (display) display.textContent = remaining;

        if (remaining <= 0) {
            clearInterval(countdown);
            window.location.href = '/logout';
        }
    }, 1000);
}

function extendSession() {
    resetActivityTimer();
    const warning = document.getElementById('timeoutWarning');
    if (warning) warning.classList.remove('active');
}

// Detectar actividad del usuario
document.addEventListener('mousedown', resetActivityTimer);
document.addEventListener('keydown', resetActivityTimer);
document.addEventListener('touchstart', resetActivityTimer);

// Verificar inactividad cada 5 segundos
setInterval(checkInactivity, 5000);
