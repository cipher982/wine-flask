# Wine-Flask
Hosting repo for https://github.com/cipher982/this-wine-does-not-exist

The linked repository above contains all the code and notebooks for building the dataset of wines, training the various models, and producing the results. This repository is built around providing a web server built around Python that allows the work to be presented on a wider scale.

### Link
www.thiswinedoesnotexist.com

### Architecture

**Application:** FastAPI web server serving AI-generated wine content

**Data Storage:**
- **Wine Descriptions:** SQLite database (5.3 MB, 9,483 records) stored in MinIO bucket `wine-data/wine_data.db`
- **Wine Bottle Images:** MinIO bucket `wine-bottles/` (AI-generated labels)

**Deployment:**
- Hosted on clifford VPS via Coolify
- Database downloads from MinIO on container startup
- Single container architecture (no separate database service)

**Development:**
```bash
docker compose -f docker-compose.local.yml up
```

### Sample Page

<img src="https://raw.githubusercontent.com/cipher982/this-wine-does-not-exist/master/images/page_sample.png" alt="sample-wine-page" width="700"/>

### Historical Notes

The `notebooks/` directory contains legacy migration scripts from the original Firestore → PostgreSQL → SQLite migration path. These are preserved for reference but are no longer used in production.
