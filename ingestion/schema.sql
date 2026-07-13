-- ============================================================
-- Odin v2 - BigQuery Schema
-- Dataset: secop
-- Table: contratos_electronicos
-- Source: SECOP II - Contratos Electrónicos (datos.gov.co)
-- Dataset ID: jbjy-vk9h
-- ============================================================

-- Create dataset
-- bq mk --dataset --location=US odin-v2-495523:secop

CREATE TABLE IF NOT EXISTS `odin-v2-495523.secop.contratos_electronicos`
(
  -- === Entidad ===
  nombre_entidad                          STRING      OPTIONS(description="Nombre de la entidad del estado que publica el contrato"),
  nit_entidad                             STRING      OPTIONS(description="NIT de la entidad del estado"),
  departamento                            STRING      OPTIONS(description="Departamento de la entidad"),
  ciudad                                  STRING      OPTIONS(description="Ciudad de la entidad"),
  localizacion                            STRING      OPTIONS(description="Ubicación completa de la entidad"),
  orden                                   STRING      OPTIONS(description="Orden de la entidad (Nacional/Territorial)"),
  sector                                  STRING      OPTIONS(description="Sector de la entidad"),
  rama                                    STRING      OPTIONS(description="Rama del estado"),
  entidad_centralizada                    STRING      OPTIONS(description="Centralizada o descentralizada"),
  codigo_entidad                          INT64       OPTIONS(description="Código de la entidad en SECOP II"),

  -- === Contrato ===
  proceso_de_compra                       STRING      OPTIONS(description="Identificador del proceso de compra"),
  id_contrato                             STRING      OPTIONS(description="Identificador del contrato (PK)"),
  referencia_del_contrato                 STRING      OPTIONS(description="Referencia del contrato por la entidad"),
  estado_contrato                         STRING      OPTIONS(description="Estado: Borrador, Activo, Cerrado, Liquidado, etc."),
  codigo_de_categoria_principal           STRING      OPTIONS(description="Código UNSPSC categoría principal"),
  descripcion_del_proceso                 STRING      OPTIONS(description="Descripción del objeto del proceso"),
  objeto_del_contrato                     STRING      OPTIONS(description="Objeto del contrato electrónico"),
  tipo_de_contrato                        STRING      OPTIONS(description="Tipo de contrato (Suministros, Prestación de Servicios, etc.)"),
  modalidad_de_contratacion               STRING      OPTIONS(description="Modalidad de contratación"),
  justificacion_modalidad_de              STRING      OPTIONS(description="Justificación de la modalidad"),
  condiciones_de_entrega                  STRING      OPTIONS(description="Condiciones de entrega del producto/servicio"),
  duracion_del_contrato                   STRING      OPTIONS(description="Duración del contrato"),

  -- === Fechas ===
  fecha_de_firma                          TIMESTAMP   OPTIONS(description="Fecha de firma del contrato"),
  fecha_de_inicio_del_contrato            TIMESTAMP   OPTIONS(description="Fecha de inicio de responsabilidades"),
  fecha_de_fin_del_contrato               TIMESTAMP   OPTIONS(description="Fecha de fin de responsabilidades"),
  fecha_inicio_liquidacion                TIMESTAMP   OPTIONS(description="Fecha de inicio de liquidación"),
  fecha_fin_liquidacion                   TIMESTAMP   OPTIONS(description="Fecha de fin de liquidación"),
  ultima_actualizacion                    TIMESTAMP   OPTIONS(description="Fecha de última actualización"),
  fecha_de_notificacion_de_prorrogacion   TIMESTAMP   OPTIONS(description="Fecha de notificación de prórroga"),

  -- === Proveedor ===
  tipodocproveedor                        STRING      OPTIONS(description="Tipo de documento del proveedor"),
  documento_proveedor                     STRING      OPTIONS(description="Número de documento del proveedor"),
  proveedor_adjudicado                    STRING      OPTIONS(description="Nombre del proveedor adjudicado"),
  codigo_proveedor                        STRING      OPTIONS(description="Código del proveedor en SECOP II"),
  es_grupo                                STRING      OPTIONS(description="Si el proveedor es un grupo"),
  es_pyme                                 STRING      OPTIONS(description="Si la empresa es Pyme"),

  -- === Valores monetarios (COP) ===
  valor_del_contrato                      NUMERIC     OPTIONS(description="Valor total del contrato en COP"),
  valor_de_pago_adelantado                NUMERIC     OPTIONS(description="Valor del pago por adelantado"),
  valor_facturado                         NUMERIC     OPTIONS(description="Valor facturado a la fecha"),
  valor_pendiente_de_pago                 NUMERIC     OPTIONS(description="Valor pendiente de pago"),
  valor_pagado                            NUMERIC     OPTIONS(description="Valor pagado a la fecha"),
  valor_amortizado                        NUMERIC     OPTIONS(description="Valor amortizado a la fecha"),
  valor_pendiente_de_amortizacion         NUMERIC     OPTIONS(description="Valor pendiente de amortización"),
  valor_pendiente_de_ejecucion            NUMERIC     OPTIONS(description="Valor pendiente de ejecución"),
  saldo_cdp                               NUMERIC     OPTIONS(description="Saldo del CDP"),
  saldo_vigencia                          NUMERIC     OPTIONS(description="Saldo vigencia del CDP"),

  -- === Origen de recursos ===
  origen_de_los_recursos                  STRING      OPTIONS(description="Origen de los recursos"),
  destino_gasto                           STRING      OPTIONS(description="Destino del gasto"),
  presupuesto_general_de_la_nacion_pgn    NUMERIC     OPTIONS(description="Recursos del PGN"),
  sistema_general_de_participaciones      NUMERIC     OPTIONS(description="Recursos del SGP"),
  sistema_general_de_regalias             NUMERIC     OPTIONS(description="Recursos del SGR"),
  recursos_propios_territorial            NUMERIC     OPTIONS(description="Recursos propios alcaldías/gobernaciones"),
  recursos_de_credito                     NUMERIC     OPTIONS(description="Recursos de crédito"),
  recursos_propios                        NUMERIC     OPTIONS(description="Recursos propios"),

  -- === Flags ===
  habilita_pago_adelantado                STRING      OPTIONS(description="Habilita pago adelantado"),
  liquidacion                             STRING      OPTIONS(description="Si ha sido liquidado"),
  obligacion_ambiental                    STRING      OPTIONS(description="Obligaciones ambientales"),
  obligaciones_postconsumo                STRING      OPTIONS(description="Obligaciones postconsumo"),
  reversion                               STRING      OPTIONS(description="Si ha sido reversado"),
  espostconflicto                         STRING      OPTIONS(description="Asociado a acuerdo de paz"),
  dias_adicionados                        INT64       OPTIONS(description="Días adicionados al contrato"),
  puntos_del_acuerdo                      STRING      OPTIONS(description="Puntos del acuerdo de paz"),
  pilares_del_acuerdo                     STRING      OPTIONS(description="Pilares del acuerdo de paz"),
  el_contrato_puede_ser_prorrogado        STRING      OPTIONS(description="Si puede ser prorrogado"),

  -- === URL ===
  urlproceso                              STRING      OPTIONS(description="URL del proceso en SECOP II"),

  -- === Representante Legal ===
  nombre_representante_legal              STRING      OPTIONS(description="Nombre del representante legal"),
  nacionalidad_representante_legal        STRING      OPTIONS(description="Nacionalidad del representante legal"),
  domicilio_representante_legal           STRING      OPTIONS(description="Domicilio del representante legal"),
  tipo_identificacion_representante_legal STRING      OPTIONS(description="Tipo identificación representante legal"),
  identificacion_representante_legal      STRING      OPTIONS(description="Número identificación representante legal"),
  genero_representante_legal              STRING      OPTIONS(description="Género del representante legal"),

  -- === Ordenador del gasto ===
  nombre_ordenador_del_gasto              STRING      OPTIONS(description="Nombre del ordenador del gasto"),
  tipo_documento_ordenador_del_gasto      STRING      OPTIONS(description="Tipo documento ordenador del gasto"),
  numero_documento_ordenador_del_gasto    STRING      OPTIONS(description="Número documento ordenador del gasto"),

  -- === Supervisor ===
  nombre_supervisor                       STRING      OPTIONS(description="Nombre del supervisor"),
  tipo_documento_supervisor               STRING      OPTIONS(description="Tipo documento supervisor"),
  numero_documento_supervisor             STRING      OPTIONS(description="Número documento supervisor"),

  -- === Ordenador de pago ===
  nombre_ordenador_de_pago                STRING      OPTIONS(description="Nombre del ordenador de pago"),
  tipo_documento_ordenador_de_pago        STRING      OPTIONS(description="Tipo documento ordenador de pago"),
  numero_documento_ordenador_de_pago      STRING      OPTIONS(description="Número documento ordenador de pago"),

  -- === Bancario ===
  nombre_del_banco                        STRING      OPTIONS(description="Banco para pagos"),
  tipo_de_cuenta                          STRING      OPTIONS(description="Tipo de cuenta bancaria"),
  numero_de_cuenta                        STRING      OPTIONS(description="Número de cuenta bancaria"),

  -- === Documentos tipo ===
  documentos_tipo                         STRING      OPTIONS(description="Si se usaron documentos tipo"),
  descripcion_documentos_tipo             STRING      OPTIONS(description="Descripción de documentos tipo"),

  -- === Metadata ===
  _ingested_at                            TIMESTAMP   OPTIONS(description="Fecha de ingesta en Odin"),
  _source_hash                            STRING      OPTIONS(description="Hash del registro fuente para dedup")
)
PARTITION BY DATE(fecha_de_firma)
CLUSTER BY departamento, nombre_entidad, estado_contrato
OPTIONS(
  description="Contratos electrónicos registrados en SECOP II - Datos Abiertos Colombia",
  labels=[("source", "secop_ii"), ("project", "odin_v2")]
);

-- ============================================================
-- Table: tienda_virtual_consolidado
-- Source: Tienda Virtual del Estado Colombiano - Consolidado
-- Dataset ID: rgxm-mmea
-- ============================================================

CREATE TABLE IF NOT EXISTS `odin-v2-495523.secop.tienda_virtual_consolidado` (
  a_o                             STRING      OPTIONS(description="Año de la orden"),
  identificador_de_la_orden       STRING      OPTIONS(description="ID de la orden de compra"),
  rama_de_la_entidad              STRING      OPTIONS(description="Rama de la entidad pública"),
  orden_de_la_entidad             STRING      OPTIONS(description="Orden de la entidad"),
  sector_de_la_entidad            STRING      OPTIONS(description="Sector administrativo de la entidad"),
  entidad                         STRING      OPTIONS(description="Nombre de la entidad compradora"),
  solicitante                     STRING      OPTIONS(description="Nombre del solicitante"),
  fecha                           TIMESTAMP   OPTIONS(description="Fecha de emisión"),
  fecha_vence                     TIMESTAMP   OPTIONS(description="Fecha de vencimiento"),
  proveedor                       STRING      OPTIONS(description="Nombre del proveedor"),
  estado                          STRING      OPTIONS(description="Estado de la orden"),
  solicitud                       STRING      OPTIONS(description="Número de solicitud"),
  items                           STRING      OPTIONS(description="Detalle de ítems"),
  total                           NUMERIC     OPTIONS(description="Valor total en COP"),
  agregacion                      STRING      OPTIONS(description="Acuerdo Marco o agregación"),
  ciudad                          STRING      OPTIONS(description="Ciudad de la entidad"),
  entidad_obigada                 STRING      OPTIONS(description="Si la entidad está obligada"),
  espostconflicto                 STRING      OPTIONS(description="Asociado a postconflicto"),
  nit_proveedor                   STRING      OPTIONS(description="NIT del proveedor"),
  actividad_economica_proveedor   STRING      OPTIONS(description="Actividad económica del proveedor"),
  nit_entidad                     STRING      OPTIONS(description="NIT de la entidad"),
  id_entidad                      STRING      OPTIONS(description="ID de la entidad"),
  _ingested_at                    TIMESTAMP   OPTIONS(description="Fecha de ingesta en Odin"),
  _source_hash                    STRING      OPTIONS(description="Hash del registro fuente")
)
OPTIONS(
  description="Consolidado de transacciones de la Tienda Virtual del Estado Colombiano - TVEC",
  labels=[("source", "tvec"), ("project", "odin_v2")]
);

