# Basic SEO Epic

## Goal
Make thiswinedoesnotexist.com easier for search engines and social previews to understand without turning the project into a large generated-content catalog.

## Scope
- Add clear page titles, descriptions, canonical URLs, and social preview metadata.
- Add crawl discovery files: `robots.txt` and `sitemap.xml`.
- Add lightweight structured data for the site and generator.
- Add honest crawlable copy that explains the project, models, and generated output.
- Add a few stable support pages for the main search intents:
  - AI wine generator
  - fake wine name generator
  - AI wine label generator
  - wine tasting note generator
  - about the project

## Non-Goals
- Do not generate thousands of fake wine pages.
- Do not pretend the project is a real wine recommendation or shopping site.
- Do not add a complex CMS, database migration, or content pipeline.
- Do not build new product features beyond simple pages and metadata.

## Done Criteria
- Important pages render with unique titles, descriptions, canonical URLs, and Open Graph tags.
- `robots.txt` references a sitemap.
- `sitemap.xml` lists the homepage and stable support pages.
- The homepage has crawlable explanatory content below the generator.
- Basic local checks pass before deploy.
