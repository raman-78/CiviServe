# Documentation

Living documentation for **CiviServe — Multilingual Citizen Service Chatbot for
Government Schemes** (HackElite 2026).

## Index

| # | Topic | Doc |
| - | ----- | --- |
| 01 | Complete project folder structure | [01-project-structure.md](architecture/01-project-structure.md) |
| 02 | Frontend architecture | [02-frontend-architecture.md](architecture/02-frontend-architecture.md) |
| 03 | Backend architecture | [03-backend-architecture.md](architecture/03-backend-architecture.md) |
| 04 | API folder organization | [04-api-organization.md](architecture/04-api-organization.md) |
| 05 | Database folder organization | [05-database-organization.md](architecture/05-database-organization.md) |
| 06 | Shared models | [06-shared-models.md](architecture/06-shared-models.md) |
| 07 | Component hierarchy | [07-component-hierarchy.md](architecture/07-component-hierarchy.md) |
| 08 | Routing architecture | [08-routing-architecture.md](architecture/08-routing-architecture.md) |
| 09 | State management strategy | [09-state-management.md](architecture/09-state-management.md) |
| 10 | Environment variables | [10-environment-variables.md](architecture/10-environment-variables.md) |
| 11 | Configuration files | [11-configuration-files.md](architecture/11-configuration-files.md) |
| 12 | Dependency list | [12-dependencies.md](architecture/12-dependencies.md) |
| 13 | Error handling architecture | [13-error-handling.md](architecture/13-error-handling.md) |
| 14 | Logging architecture | [14-logging.md](architecture/14-logging.md) |
| 15 | Security architecture | [15-security.md](architecture/15-security.md) |
| 16 | Scalability considerations | [16-scalability.md](architecture/16-scalability.md) |
| 17 | Future extensibility | [17-extensibility.md](architecture/17-extensibility.md) |
| 18 | Development workflow | [18-development-workflow.md](architecture/18-development-workflow.md) |
| 19 | Git branching strategy | [19-git-branching.md](architecture/19-git-branching.md) |

## Database & AI knowledge (Prompt 2)

| Document | Covers |
| -------- | ------ |
| [Database overview + ERD](database/README.md) | ER diagram, conventions, document index |
| [01 — Schema & tables](database/01-schema-tables.md) | All tables: columns, PK/FK, constraints, indexes |
| [02 — Relationships & normalization](database/02-relationships-normalization.md) | FK graph, cardinality, normalization forms |
| [03 — Eligibility engine](database/03-eligibility-engine.md) | Extensible filter catalog + declarative rules |
| [04 — Documents & service centres](database/04-documents-centres.md) | Document lifecycle, CSC/e-Sevai geo data |
| [05 — Multilingual strategy](database/05-multilingual.md) | Languages, localized_texts, fallback, new-language path |
| [06 — Search & index strategy](database/06-search-indexes.md) | Indexes, keyword/semantic/fuzzy/voice/regional search |
| [07 — RAG knowledge base](database/07-rag-knowledge-base.md) | Sources→chunks→embeddings→retrieval→citations→sync |
| [08 — Migrations, data update & scalability](database/08-migrations-data-update-scalability.md) | Migration lifecycle, ETL refresh, scale tiers |

Decision records: [`decisions/README.md`](decisions/README.md)

## Reading order

For new contributors: 01 → 06 → 03 → 02 → 08/09 → 15. The rest are reference.
