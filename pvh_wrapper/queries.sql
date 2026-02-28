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
    LISTAGG(DISTINCT class_name, ', ') WITHIN GROUP (ORDER BY class_name) AS system_types
FROM (
    SELECT
        REGEXP_SUBSTR(n.NAME, '^[A-Za-z][A-Za-z0-9]{2,3}') AS store_prefix,
        c.NAME AS class_name
    FROM sm_pvhprd.NODE n
    JOIN sm_pvhprd.CLASS c ON n.CLASS_ID = c.ID
    WHERE n.NAME LIKE '%TILL%'
      AND c.NAME LIKE 'PVH-OPOS-FAT-%'
      AND c.NAME NOT LIKE '%-WS'
      AND c.NAME NOT LIKE '%-WIDESCREEN'
) sub
WHERE store_prefix IS NOT NULL
GROUP BY store_prefix
HAVING COUNT(DISTINCT class_name) > 1
ORDER BY store_prefix;
