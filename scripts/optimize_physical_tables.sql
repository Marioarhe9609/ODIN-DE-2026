-- =====================================================================
-- ODIN V2 - OPTIMIZACIÓN FÍSICA DE TABLAS EN BIGQUERY
-- =====================================================================
-- Este script DDL demuestra cómo recrear o clonar las tablas relacionales 
-- principales de SECOP II en BigQuery aplicando Particionado y Clusterizado.
-- Ejecutar estas sentencias en la consola de Google BigQuery mejorará
-- drásticamente el rendimiento de las consultas y reducirá costos (> 80%).

-- ---------------------------------------------------------------------
-- 1. OPTIMIZACIÓN DE TABLA: contratos_electronicos
-- ---------------------------------------------------------------------
-- Particionado por fecha de firma (diario)
-- Clusterizado por documento_proveedor (nit), nombre_entidad y UNSPSC
-- ---------------------------------------------------------------------

-- Paso A: Crear tabla optimizada vacía o con base en datos actuales
CREATE OR REPLACE TABLE `odin-v2-495523.secop.contratos_electronicos_opt`
PARTITION BY DATE(fecha_de_firma)
CLUSTER BY documento_proveedor, nombre_entidad, codigo_de_categoria_principal
AS
SELECT * 
FROM `odin-v2-495523.secop.contratos_electronicos`
WHERE fecha_de_firma IS NOT NULL;

-- Paso B: Intercambiar tablas (opcional, ejecutar una vez validado)
-- DROP TABLE `odin-v2-495523.secop.contratos_electronicos`;
-- ALTER TABLE `odin-v2-495523.secop.contratos_electronicos_opt` RENAME TO `contratos_electronicos`;


-- ---------------------------------------------------------------------
-- 2. OPTIMIZACIÓN DE TABLA: procesos_contratacion
-- ---------------------------------------------------------------------
-- Particionado por fecha de publicación del proceso (diario)
-- Clusterizado por entidad, estado de procedimiento y UNSPSC
-- ---------------------------------------------------------------------

CREATE OR REPLACE TABLE `odin-v2-495523.secop.procesos_contratacion_opt`
PARTITION BY DATE(fecha_de_publicacion_del_proceso)
CLUSTER BY nombre_entidad, estado_del_procedimiento, codigo_principal_de_categoria
AS
SELECT *
FROM `odin-v2-495523.secop.procesos_contratacion`
WHERE fecha_de_publicacion_del_proceso IS NOT NULL;

-- Paso B: Intercambiar tablas
-- DROP TABLE `odin-v2-495523.secop.procesos_contratacion`;
-- ALTER TABLE `odin-v2-495523.secop.procesos_contratacion_opt` RENAME TO `procesos_contratacion`;


-- ---------------------------------------------------------------------
-- 3. OPTIMIZACIÓN DE TABLA: proponentes_proceso
-- ---------------------------------------------------------------------
-- Tabla de cruce de grafos. Clusterizado por ID del proceso (procedimiento)
-- y NIT del proveedor para JOINs instantáneos.
-- ---------------------------------------------------------------------

CREATE OR REPLACE TABLE `odin-v2-495523.secop.proponentes_proceso_opt`
CLUSTER BY id_procedimiento, nit_proveedor
AS
SELECT *
FROM `odin-v2-495523.secop.proponentes_proceso`;

-- Paso B: Intercambiar tablas
-- DROP TABLE `odin-v2-495523.secop.proponentes_proceso`;
-- ALTER TABLE `odin-v2-495523.secop.proponentes_proceso_opt` RENAME TO `proponentes_proceso`;
