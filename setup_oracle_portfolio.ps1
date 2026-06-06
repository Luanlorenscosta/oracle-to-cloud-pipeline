# ================================================================
# setup_oracle_portfolio.ps1
# Cria estrutura do projeto oracle-to-cloud-pipeline
# ================================================================

Write-Host "Criando estrutura do projeto..." -ForegroundColor Cyan

# Diretorios
$dirs = @(
    "infra/docker",
    "sql/oracle/ddl",
    "sql/oracle/seed_data",
    "sql/oracle/procedures",
    "sql/postgresql/ddl",
    "pipelines/extract",
    "pipelines/transform",
    "pipelines/load",
    "pipelines/validation",
    "streaming/cdc",
    "tests",
    "docs",
    ".github/workflows"
)

$dirs | ForEach-Object {
    New-Item -ItemType Directory -Path $_ -Force | Out-Null
}

# Arquivos
$files = @(
    "README.md",
    ".gitignore",
    "requirements.txt",
    ".env.example",
    "docker-compose.yml",
    "sql/oracle/ddl/01_create_tables.sql",
    "sql/oracle/seed_data/generate_data.py",
    "sql/oracle/procedures/pkg_financeiro.sql",
    "sql/postgresql/ddl/01_create_tables.sql",
    "pipelines/extract/01_extract_oracle.py",
    "pipelines/transform/02_transform_data.py",
    "pipelines/load/03_load_parquet.py",
    "pipelines/load/04_load_postgresql.py",
    "pipelines/validation/05_validate_migration.py",
    "streaming/cdc/oracle_cdc_producer.py",
    "streaming/cdc/oracle_cdc_consumer.py",
    "tests/test_extraction.py",
    "tests/test_transformation.py",
    "tests/test_validation.py",
    "tests/conftest.py",
    "docs/architecture.md",
    "docs/migration_guide.md",
    ".github/workflows/run_tests.yml"
)

$files | ForEach-Object {
    New-Item -ItemType File -Path $_ -Force | Out-Null
}

Write-Host "Estrutura criada com sucesso!" -ForegroundColor Green
