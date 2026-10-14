
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
