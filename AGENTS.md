# Wine Flask - thiswinedoesnotexist.com

## Nested Repository Structure

**Note:** `~/git/wine/` contains two separate repositories:
- `~/git/wine/this-wine-does-not-exist/` - Original implementation
- `~/git/wine/wine-flask/` - Current deployed version (Flask/FastAPI)

The deployed site uses `wine-flask/`. Always `cd` into it for git operations.

## Architecture

**Application:** FastAPI serving https://thiswinedoesnotexist.com

**Data Storage:**
- Wine descriptions: SQLite (5.3 MB) in MinIO bucket `wine-data/wine_data.db`
- Wine bottle images: MinIO bucket `wine-bottles/`
- Both stored in MinIO on clifford, backed up to Bremen NAS

**Deployment:**
- Single container on clifford via Coolify
- Database downloads from MinIO on startup
- No separate database container needed

**Migration Scripts:**
- `scripts/csv_to_sqlite.py` - Convert CSV exports to SQLite
- `scripts/upload_to_minio.py` - Upload database to MinIO
