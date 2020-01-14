-- Creator:       MySQL Workbench 8.0.18/ExportSQLite Plugin 0.1.0
-- Author:        Joshua Taillon
-- Caption:       NexusLIMS DB
-- Project:       Nexus Microscopy LIMS
-- Changed:       2019-12-06 14:30
-- Changed:       2019-10-31 16:50
-- Created:       2019-10-30 14:21
PRAGMA foreign_keys = ON;

-- Schema: nexuslims_db
--   A database to hold information about the instruments and sessions logged in the Nexus Microscopy Facility
ATTACH "nexuslims_db.sqlite" AS "nexuslims_db";
BEGIN;
CREATE TABLE "nexuslims_db"."instruments"(
  "instrument_pid" VARCHAR(100) PRIMARY KEY NOT NULL,-- The unique identifier for an instrument in the Nexus Microscopy facility
  "api_url" TEXT NOT NULL,-- The calendar API url for this instrument
  "calendar_name" TEXT NOT NULL,-- "The "user-friendly" name of the calendar for this instrument as displayed on the sharepoint resource (e.g. "FEI Titan TEM")"
  "calendar_url" TEXT NOT NULL,-- "The URL to this instrument's web-accessible calendar on the sharepoint resource"
  "location" VARCHAR(100) NOT NULL,-- The physical location of this instrument (building and room number)
  "schema_name" TEXT NOT NULL,-- The name of instrument as defined in the Nexus Microscopy schema and displayed in the records
  "property_tag" VARCHAR(20) NOT NULL,-- The NIST property tag for this instrument
  "filestore_path" TEXT NOT NULL,-- The path (relative to the Nexus facility root) on the central file storage where this instrument stores its data
  "computer_name" TEXT,-- "The name of the 'support PC' connected to this instrument"
  "computer_ip" VARCHAR(15),-- "The REN IP address of the 'support PC' connected to this instrument"
  "computer_mount" TEXT,-- "The full path where the files are saved on the 'support PC' for the instrument (e.g. 'M:/')"
  CONSTRAINT "instrument_pid_UNIQUE"
    UNIQUE("instrument_pid"),
  CONSTRAINT "api_url_UNIQUE"
    UNIQUE("api_url"),
  CONSTRAINT "property_tag_UNIQUE"
    UNIQUE("property_tag"),
  CONSTRAINT "filestore_path_UNIQUE"
    UNIQUE("filestore_path"),
  CONSTRAINT "computer_name_UNIQUE"
    UNIQUE("computer_name"),
  CONSTRAINT "computer_ip_UNIQUE"
    UNIQUE("computer_ip")
);
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('FEI-Helios-DB-636663', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/FEIHeliosDBEvents', 'FEI HeliosDB', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/FEI%20HeliosDB/calendar.aspx', '***REMOVED***', 'FEI Helios', '636663', './Aphrodite', NULL, NULL, NULL);
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('FEI-Quanta200-ESEM-633137', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/FEIQuanta200Events', 'FEI Quanta200', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/FEI%20Quanta200%20Events/calendar.aspx', '***REMOVED***', 'FEI Quanta200', '633137', './Quanta', 'SUPPORT-D8439', '***REMOVED***3', 'M:/');
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('FEI-Titan-STEM-630901', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/FEITitanSTEMEvents', 'FEI Titan STEM', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/MMSD%20Titan/calendar.aspx', '***REMOVED***', 'FEI Titan STEM', '630901', './643Titan', 'WIN-DPB8312IFH6', NULL, 'X:/');
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('FEI-Titan-TEM-635816', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/FEITitanTEMEvents', 'FEI Titan TEM', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/FEI%20Titan%20Events/calendar.aspx', '***REMOVED***', 'FEI Titan TEM', '635816', './Titan', '***REMOVED***', '***REMOVED***', 'M:/');
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('Hitachi-S4700-SEM-606559', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/HitachiS4700Events', 'Hitachi S4700', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/Hitachi%20S4700%20Events/calendar.aspx', '***REMOVED***', 'Hitachi S4700', '606559', './Hitachi-S4700-SEM-606559', NULL, NULL, NULL);
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('Hitachi-S5500-SEM-635262', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/HitachiS5500Events', 'Hitachi-S5500', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/HitachiS5500/calendar.aspx', '***REMOVED***', 'Hitachi S5500', '635262', './S5500', NULL, NULL, NULL);
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('JEOL-JEM3010-TEM-565989', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/JEOLJEM3010Events', 'JEOL JEM3010', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/JEOL%20JEM3010%20Events/calendar.aspx', '***REMOVED***', 'JEOL JEM3010', '565989', './JEOL3010', NULL, NULL, NULL);
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('JEOL-JSM7100-SEM-N102656', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/JEOLJSM7100Events', 'JEOL JSM7100', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/JEOL%20JSM7100%20Events/calendar.aspx', '***REMOVED***', 'JEOL JSM7100', 'N102656', './7100Jeol', NULL, NULL, NULL);
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('Philips-CM30-TEM-540388', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/PhilipsCM30Events', 'Philips CM30', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/Philips%20CM30%20Events/calendar.aspx', 'Unknown', 'Philips CM30', '540388', './Philips-CM30-TEM-540388', NULL, NULL, NULL);
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('Philips-EM400-TEM-599910', 'https://***REMOVED***/Div/msed/MSED-MMF/_vti_bin/ListData.svc/PhilipsEM400Events', 'Philips EM400', 'https://***REMOVED***/Div/msed/MSED-MMF/Lists/Philips%20EM400%20Events/calendar.aspx', '***REMOVED***', 'Philips EM400', '599910', './EM400', NULL, NULL, NULL);
INSERT INTO "instruments"("instrument_pid","api_url","calendar_name","calendar_url","location","schema_name","property_tag","filestore_path","computer_name","computer_ip","computer_mount") VALUES('testsurface-CPU_P1111111', 'https://example.com/surface', 'Surface test instrument', 'https://example.com/surface', '2/2607', 'Surface test instrument', '***REMOVED***', './test_surface', '***REMOVED***', '***REMOVED***21', 'M:/');


CREATE TABLE "nexuslims_db"."session_log"(
  "id_session_log" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, -- the auto-incrementing primary key identifier for this table (just a generic number)
  "session_identifier" VARCHAR(36) NOT NULL,-- A UUID4 (36-character string) that is consistent among a single record's "START", "END", and "RECORD_GENERATION" events
  "instrument" VARCHAR(100) NOT NULL,-- The instrument associated with this session (foreign key reference to the 'instruments' table)
  "timestamp" DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),-- The date and time of the logged event
  "event_type" TEXT NOT NULL CHECK("event_type" IN('START', 'END', 'RECORD_GENERATION')),-- The type of log for this session either "START" or "END"
  "record_status" TEXT NOT NULL CHECK("record_status" IN('COMPLETED', 'WAITING_FOR_END', 'TO_BE_BUILT')) DEFAULT 'WAITING_FOR_END',-- The status of the record associated with this session. One of 'WAITING_FOR_END' (has a start event, but no end event), 'TO_BE_BUILT' (session has ended, but record not yet built), or 'COMPLETED' (record has been built)
  "user" VARCHAR(50),-- The NIST "short style" username associated with this session (if known)
  CONSTRAINT "id_session_log_UNIQUE"
    UNIQUE("id_session_log"),
  CONSTRAINT "fk_instrument"
    FOREIGN KEY("instrument")
    REFERENCES "instruments"("instrument_pid")
    ON DELETE CASCADE
    ON UPDATE CASCADE
);
CREATE INDEX "nexuslims_db"."session_log.fk_instrument_idx" ON "session_log" ("instrument");
COMMIT;
