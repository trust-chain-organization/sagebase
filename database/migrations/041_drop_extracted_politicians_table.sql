-- Drop extracted_politicians table
-- This table is no longer needed as politician data is now managed manually only
-- Related Issue: #921 (PBI-006)

-- Drop the table with CASCADE to remove related constraints and indexes
DROP TABLE IF EXISTS extracted_politicians CASCADE;
