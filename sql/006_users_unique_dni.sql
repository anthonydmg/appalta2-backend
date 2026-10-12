-- El DNI (document_of_identity) solo puede pertenecer a un usuario.
-- Para bases creadas antes de este cambio; las nuevas ya lo traen en 001_schema.sql,
-- por eso es idempotente: si la restricción ya existe, no hace nada.
--
-- Antes de aplicarla, verificar que no haya DNI repetidos (la restricción fallaría):
--   SELECT document_of_identity, count(*) FROM users GROUP BY 1 HAVING count(*) > 1;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'users'::regclass AND conname = 'users_document_of_identity_key'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT users_document_of_identity_key UNIQUE (document_of_identity);
    END IF;
END $$;
