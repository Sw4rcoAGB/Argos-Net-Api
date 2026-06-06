-- Migración v2: campos del brief faltantes
-- Ejecutar contra la DB PostgreSQL antes de reiniciar el backend.
-- Tortoise generate_schemas() no agrega columnas a tablas existentes.

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS wallet_address VARCHAR(42);
ALTER TABLE cosechas ADD COLUMN IF NOT EXISTS latitud FLOAT;
ALTER TABLE cosechas ADD COLUMN IF NOT EXISTS longitud FLOAT;
