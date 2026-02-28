-- PVH Store Node Query
-- Returns all POS workstation nodes with their system type (class) and parent store path.
-- Used to generate pvh_store_mapping.properties from production data.
--
-- Columns:
--   NAME               - Workstation name (e.g., A313TILL01 in prod, A319_POS1 in QA)
--   UNIQUE_NAME        - Structure unique name
--   class_name         - System type / template (e.g., PVH-OPOS-FAT-EN_GB-TH-FULL)
--   parent_system_name - Parent node path (store location)
--
-- Schemas: sm_qa2 (QA, uses _POS naming), sm_pvhprd (Production, uses TILL naming)

-- Production (TILL naming)
SELECT
    n.NAME,
    n.UNIQUE_NAME,
    c.NAME AS class_name,
    p.UNIQUE_NAME AS parent_system_name
FROM sm_pvhprd.NODE n
JOIN sm_pvhprd.NODE p ON n.PARENT_ID = p.ID
JOIN sm_pvhprd.CLASS c ON n.CLASS_ID = c.ID
WHERE n.NAME LIKE '%TILL%'
  AND c.NAME LIKE 'PVH-OPOS-%'
ORDER BY c.NAME, n.NAME;

-- QA (_POS naming)
-- SELECT
--     n.NAME,
--     n.UNIQUE_NAME,
--     c.NAME AS class_name,
--     p.UNIQUE_NAME AS parent_system_name
-- FROM sm_qa2.NODE n
-- JOIN sm_qa2.NODE p ON n.PARENT_ID = p.ID
-- JOIN sm_qa2.CLASS c ON n.CLASS_ID = c.ID
-- WHERE n.NAME LIKE '%[_]POS%'
--   AND n.NAME NOT LIKE '%POS Server%'
--   AND n.NAME NOT LIKE '%POS-Server%'
-- ORDER BY c.NAME, n.NAME;


-- PVH System Types Query
-- Returns all PVH-OPOS system types (classes/templates) defined in Store Manager.
-- Useful for getting a complete overview of available system types.
--
-- Columns:
--   ID   - System type ID
--   NAME - System type name (e.g., PVH-OPOS-FAT-EN_GB-TH-FULL)
--
-- Schemas: sm_qa2 (QA), sm_pvhprd (Production)

SELECT c.ID, c.NAME
FROM sm_pvhprd.CLASS c
WHERE c.NAME LIKE 'PVH-OPOS%'
ORDER BY c.NAME;


-- Stores with mixed system types (Production - TILL naming)
-- Finds stores where different workstations are assigned different system types.
-- These stores cannot be reliably mapped with a single store_prefix=system_type entry.
-- Run this BEFORE generating the mapping file to identify conflicts.
--
-- Schemas: sm_qa2 (QA), sm_pvhprd (Production)

SELECT
    store_prefix,
    COUNT(DISTINCT class_name) AS type_count,
    STRING_AGG(class_name, ', ') WITHIN GROUP (ORDER BY class_name) AS system_types
FROM (
    SELECT DISTINCT
        LEFT(n.NAME, PATINDEX('%TILL%', n.NAME) - 1) AS store_prefix,
        c.NAME AS class_name
    FROM sm_pvhprd.NODE n
    JOIN sm_pvhprd.CLASS c ON n.CLASS_ID = c.ID
    WHERE n.NAME LIKE '%TILL%'
      AND c.NAME LIKE 'PVH-OPOS-FAT-%'
      AND c.NAME NOT LIKE '%-WS'
      AND c.NAME NOT LIKE '%-WIDESCREEN'
) sub
WHERE store_prefix IS NOT NULL AND store_prefix <> ''
GROUP BY store_prefix
HAVING COUNT(DISTINCT class_name) > 1
ORDER BY store_prefix;


-- ============================================================
-- QA2: SDC-STORE / PSVR-STORE Class ID Migration
-- ============================================================
-- Migrates SDC component nodes from old class names to new class names.
-- Transformation: after the "PVH-sdc-store" prefix, swap all hyphens and underscores.
--   Old: PVH-sdc-store-de_AT-ck-full
--   New: PVH-sdc-store_de-AT_ck_full
--
-- STEP 1: Preview - show current vs target class names (DRY RUN)
-- Run this first to verify the mapping looks correct before updating.
-- Swap hyphens/underscores via REPLACE chain: - -> ~ -> then _ -> - -> then ~ -> _

SELECT
    n.ID AS node_id,
    n.UNIQUE_NAME,
    c_old.ID AS old_class_id,
    c_old.NAME AS old_class_name,
    'PVH-sdc-store' + REPLACE(REPLACE(REPLACE(
        SUBSTRING(c_old.NAME, 14, LEN(c_old.NAME)),
        '-', '~'), '_', '-'), '~', '_') AS new_class_name,
    c_new.ID AS new_class_id,
    CASE WHEN c_new.ID IS NULL THEN '** NEW CLASS NOT FOUND **' ELSE 'OK' END AS status
FROM sm_qa2.NODE n
JOIN sm_qa2.CLASS c_old ON n.CLASS_ID = c_old.ID
LEFT JOIN sm_qa2.CLASS c_new
    ON c_new.NAME = 'PVH-sdc-store' + REPLACE(REPLACE(REPLACE(
        SUBSTRING(c_old.NAME, 14, LEN(c_old.NAME)),
        '-', '~'), '_', '-'), '~', '_')
WHERE c_old.NAME LIKE 'PVH-sdc-store-%'
ORDER BY c_old.NAME, n.UNIQUE_NAME;


-- STEP 2: Update - reassign CLASS_ID from old to new class
-- Only updates nodes where the new class exists. Run STEP 1 first to verify.

UPDATE n
SET n.CLASS_ID = c_new.ID
FROM sm_qa2.NODE n
JOIN sm_qa2.CLASS c_old ON n.CLASS_ID = c_old.ID
JOIN sm_qa2.CLASS c_new
    ON c_new.NAME = 'PVH-sdc-store' + REPLACE(REPLACE(REPLACE(
        SUBSTRING(c_old.NAME, 14, LEN(c_old.NAME)),
        '-', '~'), '_', '-'), '~', '_')
WHERE c_old.NAME LIKE 'PVH-sdc-store-%';


-- ============================================================
-- QA2: POS-SERVER-STORE Class ID Migration
-- ============================================================
-- Migrates POS Server Store nodes from old class names to new class names.
-- Transformation: just a case change in the prefix, suffix stays the same.
--   Old: PVH-POS-SERVER-STORE_TH_AT
--   New: PVH-pos-server-STORE_TH_AT
--
-- STEP 1: Preview

SELECT
    n.ID AS node_id,
    n.UNIQUE_NAME,
    c_old.ID AS old_class_id,
    c_old.NAME AS old_class_name,
    'PVH-pos-server-' + SUBSTRING(c_old.NAME, 16, LEN(c_old.NAME)) AS new_class_name,
    c_new.ID AS new_class_id,
    CASE WHEN c_new.ID IS NULL THEN '** NEW CLASS NOT FOUND **' ELSE 'OK' END AS status
FROM sm_qa2.NODE n
JOIN sm_qa2.CLASS c_old ON n.CLASS_ID = c_old.ID
LEFT JOIN sm_qa2.CLASS c_new
    ON c_new.NAME = 'PVH-pos-server-' + SUBSTRING(c_old.NAME, 16, LEN(c_old.NAME))
WHERE c_old.NAME COLLATE Latin1_General_CS_AS LIKE 'PVH-POS-SERVER-%'
ORDER BY c_old.NAME, n.UNIQUE_NAME;


-- STEP 2: Update

UPDATE n
SET n.CLASS_ID = c_new.ID
FROM sm_qa2.NODE n
JOIN sm_qa2.CLASS c_old ON n.CLASS_ID = c_old.ID
JOIN sm_qa2.CLASS c_new
    ON c_new.NAME = 'PVH-pos-server-' + SUBSTRING(c_old.NAME, 16, LEN(c_old.NAME))
WHERE c_old.NAME COLLATE Latin1_General_CS_AS LIKE 'PVH-POS-SERVER-%';
