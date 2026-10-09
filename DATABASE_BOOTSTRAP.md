# Clean Database Bootstrap

## Release rule

AI Voice Studio must not distribute the populated development database:

```text
backend/voice.db
```

That file can contain saved voice records, transcripts, generation history and other local data.

## First-run behaviour

The FastAPI application creates the SQLite schema when a new installation starts without `backend/voice.db`.

A new database must begin with:

- No saved voices
- No transcripts
- No generated-audio history
- No personal generation records

## Explicit initialisation

From the project root:

```powershell
& ".\.venv\Scripts\python.exe" `
    ".\backend\scripts\initialize_database.py"
```

## Custom path

```powershell
& ".\.venv\Scripts\python.exe" `
    ".\backend\scripts\initialize_database.py" `
    --database-path ".\backend\release_test.db"
```

## Existing-database protection

The initializer refuses to modify an existing non-empty database unless
`--allow-existing` is supplied.

Even with `--allow-existing`, it only validates that every application
table is empty. It never erases or resets a populated database.

## Upgrades

Never delete or overwrite a user's existing `voice.db` during an upgrade.

Before a migration:

1. Stop all AI Voice Studio services.
2. Back up the existing database.
3. Back up required reference voices.
4. Apply the migration.
5. Verify saved voices and generation history.
6. Keep the backup until validation is complete.

## Public release exclusions

A release package must exclude:

- `backend/voice.db`
- Other populated database files
- Saved reference voices
- Generated audio
- Logs
- Virtual environments
- Development backups
- Model caches and model weights

The release should include this guide and
`backend/scripts/initialize_database.py`.
