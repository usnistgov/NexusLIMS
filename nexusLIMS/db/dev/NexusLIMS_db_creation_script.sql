-- Author:        Joshua Taillon
-- Caption:       NexusLIMS DB
-- Project:       Nexus Microscopy LIMS
-- Changed:       2019-12-06 14:30
-- Changed:       2019-10-31 16:50
-- Updated:       2022-06-10 18:00

PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;
DROP TABLE IF EXISTS "session_log";

-- the "session_log" table is used internally by the NexusLIMS harvesters and record builder to keep track of the work
-- that needs to be and has been done
CREATE TABLE IF NOT EXISTS "session_log" (
	"id_session_log"	INTEGER NOT NULL,
	"session_identifier"	VARCHAR(36) NOT NULL,
	"instrument"	VARCHAR(100) NOT NULL,
	"timestamp"	DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%f', 'now', 'localtime')),
	"event_type"	TEXT NOT NULL CHECK("event_type" IN ('START', 'END', 'RECORD_GENERATION')),
	"record_status"	TEXT NOT NULL DEFAULT 'WAITING_FOR_END' CHECK("record_status" IN ('COMPLETED', 'WAITING_FOR_END', 'TO_BE_BUILT', 'ERROR', 'NO_FILES_FOUND')),
	"user"	VARCHAR(50),
	CONSTRAINT "fk_instrument" FOREIGN KEY("instrument") REFERENCES "instruments"("instrument_pid") ON DELETE CASCADE ON UPDATE CASCADE,
	CONSTRAINT "id_session_log_UNIQUE" UNIQUE("id_session_log"),
	PRIMARY KEY("id_session_log" AUTOINCREMENT)
);

-- The system administrator should add rows to the "instruments" table representing each instrument that is part of the
-- NexusLIMS system; the "filestore_path" should be a relative path underneath the path specified in the "mmfnexus_path" environment variable
DROP TABLE IF EXISTS "instruments";
CREATE TABLE IF NOT EXISTS "instruments" (
	"instrument_pid"	VARCHAR(100) NOT NULL,
	"api_url"	TEXT NOT NULL,
	"calendar_name"	TEXT NOT NULL,
	"calendar_url"	TEXT NOT NULL,
	"location"	VARCHAR(100) NOT NULL,
	"schema_name"	TEXT NOT NULL,
	"property_tag"	VARCHAR(20) NOT NULL,
	"filestore_path"	TEXT NOT NULL,
	"computer_name"	TEXT,
	"computer_ip"	VARCHAR(15),
	"computer_mount"	TEXT,
	"harvester"	TEXT, -- currently only "nemo" or "sharepoint" supported
	"timezone"	TEXT NOT NULL DEFAULT 'America/New_York',
	CONSTRAINT "instrument_pid_UNIQUE" UNIQUE("instrument_pid"),
	PRIMARY KEY("instrument_pid"),
	CONSTRAINT "computer_ip_UNIQUE" UNIQUE("computer_ip"),
	CONSTRAINT "api_url_UNIQUE" UNIQUE("api_url"),
	CONSTRAINT "computer_name_UNIQUE" UNIQUE("computer_name")
);
DROP INDEX IF EXISTS "session_log.fk_instrument_idx";
CREATE INDEX IF NOT EXISTS "session_log.fk_instrument_idx" ON "session_log" (
	"instrument"
);
COMMIT;
