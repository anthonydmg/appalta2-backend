-- Gestión de usuarios (idempotente: se puede ejecutar más de una vez).
-- Debe aplicarse ANTES de desplegar la versión de la API que la usa (ver DEPLOY.md).

-- Fecha del último cambio de contraseña: invalida los refresh tokens emitidos antes.
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP WITH TIME ZONE;

-- La API busca el correo sin distinguir mayúsculas (lower(email) = ...): índice para ese filtro.
CREATE INDEX IF NOT EXISTS idx_users_email_lower ON users (lower(email));
