from pathlib import Path


def migration_sql(migration_file: str) -> str:
    migration = Path(migration_file)
    sqlfile = migration.parent / 'sql' / migration.with_suffix('.sql').name
    return sqlfile.read_text()
