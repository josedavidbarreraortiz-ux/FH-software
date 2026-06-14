-- ============================================================
-- Script para unificar tablas users + cliente en fh2
-- HACER BACKUP ANTES DE EJECUTAR
-- ============================================================

USE fh2;

-- 1. Agregar columnas de contacto a users
ALTER TABLE `users`
  ADD COLUMN `telefono` VARCHAR(255) NULL AFTER `role`,
  ADD COLUMN `direccion` VARCHAR(255) NULL AFTER `telefono`,
  ADD COLUMN `numero_documento` VARCHAR(255) NULL AFTER `direccion`,
  ADD COLUMN `tipo_documento` VARCHAR(255) NULL AFTER `numero_documento`;

-- 2. Migrar datos de cliente → users
UPDATE `users` u
INNER JOIN `cliente` c ON c.user_id = u.id
SET
  u.telefono = c.cliente_telefono,
  u.direccion = c.cliente_direccion,
  u.numero_documento = c.cliente_numero_documento,
  u.tipo_documento = c.cliente_tipo_documento;

-- 3. En ventas: agregar comprador_id y copiar el user_id del cliente
ALTER TABLE `ventas`
  ADD COLUMN `comprador_id` BIGINT UNSIGNED NULL AFTER `cliente_id`;

UPDATE `ventas` v
INNER JOIN `cliente` c ON c.cliente_id = v.cliente_id
SET v.comprador_id = c.user_id;

ALTER TABLE `ventas`
  ADD CONSTRAINT `fk_ventas_comprador` FOREIGN KEY (`comprador_id`) REFERENCES `users` (`id`);

-- 4. En pqrs: agregar usuario_cliente_id y copiar
ALTER TABLE `pqrs`
  ADD COLUMN `usuario_cliente_id` BIGINT UNSIGNED NULL AFTER `cliente_id`;

UPDATE `pqrs` p
INNER JOIN `cliente` c ON c.cliente_id = p.cliente_id
SET p.usuario_cliente_id = c.user_id;

-- 5. Eliminar FK antiguas de ventas y pqrs que apuntan a cliente
ALTER TABLE `ventas` DROP FOREIGN KEY `ventas_ibfk_2`;
ALTER TABLE `pqrs` DROP FOREIGN KEY `FK3fku5wcuikhsw15k42yhiyncm`;

-- 6. Eliminar columna cliente_id de ventas y pqrs
ALTER TABLE `ventas` DROP COLUMN `cliente_id`;
ALTER TABLE `pqrs` DROP COLUMN `cliente_id`;

-- 7. Eliminar FK de cliente que apunta a users
ALTER TABLE `cliente` DROP FOREIGN KEY `fk_cliente_user`;
ALTER TABLE `cliente` DROP FOREIGN KEY `FK5928j6vwtyns9yr2cof9658hg`;

-- 8. Eliminar tabla cliente
DROP TABLE `cliente`;

-- Verificar
SELECT 'Migración completada exitosamente' AS resultado;
SELECT id, name, email, telefono, direccion, numero_documento FROM users LIMIT 10;
