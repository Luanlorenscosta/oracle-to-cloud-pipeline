# ================================================================
# 01_extract_oracle.py
# Pipeline: Oracle 21c → Parquet (Bronze) → PostgreSQL (Cloud)
# Equivalente ao: Azure Data Factory + Databricks migration job
# O que faz:
#   - Extrai tabelas do Oracle 21c
#   - Grava em Parquet particionado (Data Lake Bronze)
#   - Carrega no PostgreSQL (destino cloud)
#   - Valida contagens e somas origem vs destino
# Uso: python pipelines/extract/01_extract_oracle.py
# ================================================================

import oracledb
import psycopg2
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from datetime import datetime
from loguru import logger
import json

# ----------------------------------------------------------------
# Configuração
# ----------------------------------------------------------------
ORACLE_CONFIG = {
    "host":     "localhost",
    "port":     1521,
    "service":  "XEPDB1",
    "user":     "financeiro",
    "password": "Financeiro123",
}

POSTGRES_CONFIG = {
    "host":     "localhost",
    "port":     5434,
    "database": "financeiro_cloud",
    "user":     "postgres",
    "password": "postgres123",
}

# Caminhos do Data Lake local
DATA_LAKE  = Path("data_lake")
BRONZE     = DATA_LAKE / "bronze"

# Tabelas para migrar (ordem importa por causa das FKs)
TABELAS = [
    "categorias_transacao",
    "clientes",
    "comerciantes",
    "contas",
    "transacoes",
]

# ----------------------------------------------------------------
# Conexões
# ----------------------------------------------------------------
def conectar_oracle():
    logger.info("Conectando ao Oracle 21c (fonte)...")
    dsn  = f"{ORACLE_CONFIG['host']}:{ORACLE_CONFIG['port']}/{ORACLE_CONFIG['service']}"
    conn = oracledb.connect(
        user=ORACLE_CONFIG["user"],
        password=ORACLE_CONFIG["password"],
        dsn=dsn,
    )
    logger.success("Oracle conectado!")
    return conn

def conectar_postgres():
    logger.info("Conectando ao PostgreSQL (destino cloud)...")
    conn = psycopg2.connect(**POSTGRES_CONFIG)
    conn.autocommit = False
    logger.success("PostgreSQL conectado!")
    return conn

# ----------------------------------------------------------------
# Extração do Oracle
# ----------------------------------------------------------------
def extrair_tabela_oracle(conn_oracle, tabela: str) -> pd.DataFrame:
    """
    Extrai uma tabela completa do Oracle.
    Em produção: usaríamos watermark para carga incremental.
    Equivalente ao: Oracle connector no Azure Data Factory.
    """
    logger.info(f"Extraindo {tabela} do Oracle...")
    df = pd.read_sql(f"SELECT * FROM {tabela}", conn_oracle)

    # Oracle retorna nomes de colunas em maiúsculo — normaliza para minúsculo
    df.columns = [col.lower() for col in df.columns]

    # Adiciona metadados de migração
    df["_origem"]              = "oracle_21c"
    df["_data_extracao"]       = datetime.now()
    df["_tabela_origem"]       = tabela.lower()

    logger.success(f"  ✓ {tabela}: {len(df):,} linhas extraídas")
    return df

# ----------------------------------------------------------------
# Gravação no Data Lake (Bronze)
# ----------------------------------------------------------------
def gravar_bronze(df: pd.DataFrame, tabela: str):
    """
    Grava o DataFrame em Parquet particionado na camada Bronze.
    Simula o ADLS Gen2 Bronze container.
    """
    agora    = datetime.now()
    particao = f"ano={agora.year}/mes={agora.month:02d}/dia={agora.day:02d}"
    destino  = BRONZE / tabela / particao
    destino.mkdir(parents=True, exist_ok=True)

    arquivo = destino / f"{tabela}.parquet"
    df.to_parquet(arquivo, index=False, engine="pyarrow")

    tamanho_mb = arquivo.stat().st_size / (1024 * 1024)
    logger.success(
        f"  ✓ Bronze {tabela}: {tamanho_mb:.2f} MB → {arquivo}"
    )
    return arquivo

# ----------------------------------------------------------------
# DDL PostgreSQL — cria tabelas no destino
# ----------------------------------------------------------------
def criar_tabelas_postgres(conn_pg):
    """
    Cria as tabelas no PostgreSQL destino.
    Equivalente ao: schema migration no Azure SQL Database.
    """
    logger.info("Criando tabelas no PostgreSQL (destino)...")
    cursor = conn_pg.cursor()

    ddl_statements = [
        """
        CREATE TABLE IF NOT EXISTS categorias_transacao (
            id_categoria    SERIAL PRIMARY KEY,
            nome            VARCHAR(50)  NOT NULL UNIQUE,
            tipo            VARCHAR(20)  NOT NULL,
            _origem         VARCHAR(50),
            _data_extracao  TIMESTAMP,
            _tabela_origem  VARCHAR(50)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS clientes (
            id_cliente      SERIAL PRIMARY KEY,
            nome            VARCHAR(150) NOT NULL,
            cpf             VARCHAR(14)  NOT NULL UNIQUE,
            email           VARCHAR(150) NOT NULL UNIQUE,
            data_nascimento DATE,
            genero          CHAR(1),
            cidade          VARCHAR(100),
            estado          CHAR(2),
            score_credito   INTEGER,
            data_cadastro   TIMESTAMP,
            ativo           INTEGER,
            _origem         VARCHAR(50),
            _data_extracao  TIMESTAMP,
            _tabela_origem  VARCHAR(50)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS comerciantes (
            id_comerciante  SERIAL PRIMARY KEY,
            nome            VARCHAR(150) NOT NULL,
            categoria       VARCHAR(50),
            cidade          VARCHAR(100),
            estado          CHAR(2),
            cnpj            VARCHAR(18)  UNIQUE,
            _origem         VARCHAR(50),
            _data_extracao  TIMESTAMP,
            _tabela_origem  VARCHAR(50)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS contas (
            id_conta        SERIAL PRIMARY KEY,
            id_cliente      INTEGER,
            numero_conta    VARCHAR(20)  NOT NULL UNIQUE,
            tipo_conta      VARCHAR(20),
            saldo           NUMERIC(15,2),
            limite          NUMERIC(15,2),
            data_abertura   TIMESTAMP,
            ativa           INTEGER,
            _origem         VARCHAR(50),
            _data_extracao  TIMESTAMP,
            _tabela_origem  VARCHAR(50)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS transacoes (
            id_transacao        BIGSERIAL PRIMARY KEY,
            id_conta            INTEGER,
            id_categoria        INTEGER,
            id_comerciante      INTEGER,
            valor               NUMERIC(12,2),
            tipo                VARCHAR(20),
            status              VARCHAR(20),
            canal               VARCHAR(20),
            descricao           VARCHAR(255),
            data_transacao      TIMESTAMP,
            data_processamento  TIMESTAMP,
            is_fraude           INTEGER,
            score_fraude        NUMERIC(5,4),
            ip_origem           VARCHAR(45),
            device_id           VARCHAR(100),
            _origem             VARCHAR(50),
            _data_extracao      TIMESTAMP,
            _tabela_origem      VARCHAR(50)
        )
        """,
    ]

    for ddl in ddl_statements:
        cursor.execute(ddl)

    conn_pg.commit()
    logger.success("Tabelas criadas no PostgreSQL!")
    cursor.close()

# ----------------------------------------------------------------
# Carregamento no PostgreSQL
# ----------------------------------------------------------------
def carregar_postgres(conn_pg, df: pd.DataFrame, tabela: str):
    """
    Carrega o DataFrame no PostgreSQL usando COPY para performance.
    Equivalente ao: Sink connector no Azure Data Factory.
    """
    import io
    cursor = conn_pg.cursor()

    # Limpa a tabela antes de carregar (full load)
    cursor.execute(f"TRUNCATE TABLE {tabela} RESTART IDENTITY CASCADE")

    # Usa StringIO para COPY eficiente
    # Converte colunas numericas inteiras
    for col in df.columns:
        if col.startswith("id_") or col in ["is_fraude", "ativo", "ativa"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    buffer = io.StringIO()
    df.to_csv(buffer, index=False, header=False, na_rep="\\N")
    buffer.seek(0)

    colunas = ", ".join(df.columns)
    cursor.copy_expert(
        f"COPY {tabela} ({colunas}) FROM STDIN WITH CSV NULL '\\N'",
        buffer
    )

    conn_pg.commit()
    logger.success(f"  ✓ PostgreSQL {tabela}: {len(df):,} linhas carregadas")
    cursor.close()

# ----------------------------------------------------------------
# Validação — coração do pipeline de migração
# ----------------------------------------------------------------
def validar_migracao(conn_oracle, conn_pg, tabela: str) -> dict:
    """
    Valida se os dados foram migrados corretamente.
    Compara contagens e somas entre Oracle (origem) e PostgreSQL (destino).
    
    Essa é a parte que diferencia um engenheiro sênior:
    nunca confiar cegamente na migração — sempre validar!
    
    Equivalente ao: Data Quality checks no Azure Databricks.
    """
    cursor_ora = conn_oracle.cursor()
    cursor_pg  = conn_pg.cursor()

    # Contagem
    cursor_ora.execute(f"SELECT COUNT(*) FROM {tabela}")
    count_oracle = cursor_ora.fetchone()[0]

    cursor_pg.execute(f"SELECT COUNT(*) FROM {tabela}")
    count_pg = cursor_pg.fetchone()[0]

    resultado = {
        "tabela":        tabela,
        "count_oracle":  count_oracle,
        "count_postgres": count_pg,
        "count_ok":      count_oracle == count_pg,
        "timestamp":     datetime.now().isoformat(),
    }

    # Para transacoes, valida soma dos valores
    if tabela == "transacoes":
        cursor_ora.execute("SELECT ROUND(SUM(valor), 2) FROM transacoes")
        soma_oracle = float(cursor_ora.fetchone()[0] or 0)

        cursor_pg.execute("SELECT ROUND(SUM(valor)::numeric, 2) FROM transacoes")
        soma_pg = float(cursor_pg.fetchone()[0] or 0)

        resultado["soma_oracle"]   = soma_oracle
        resultado["soma_postgres"] = soma_pg
        resultado["soma_ok"]       = abs(soma_oracle - soma_pg) < 0.01

    status = "✅ OK" if resultado["count_ok"] else "❌ DIVERGENTE"
    logger.info(
        f"  {status} {tabela}: "
        f"Oracle={count_oracle:,} | PostgreSQL={count_pg:,}"
    )

    cursor_ora.close()
    cursor_pg.close()
    return resultado

# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("PIPELINE DE MIGRAÇÃO: Oracle 21c → Cloud")
    logger.info("Equivalente: Azure Data Factory Migration Job")
    logger.info("=" * 60)

    conn_oracle = conectar_oracle()
    conn_pg     = conectar_postgres()

    # Cria tabelas no destino
    criar_tabelas_postgres(conn_pg)

    resultados_extracao   = []
    resultados_validacao  = []

    for tabela in TABELAS:
        logger.info(f"\n{'─'*50}")
        logger.info(f"Processando: {tabela.upper()}")
        logger.info(f"{'─'*50}")

        # 1. Extrai do Oracle
        df = extrair_tabela_oracle(conn_oracle, tabela)

        # 2. Grava no Data Lake Bronze (Parquet)
        arquivo = gravar_bronze(df, tabela)

        # 3. Carrega no PostgreSQL
        carregar_postgres(conn_pg, df, tabela)

        # 4. Valida migração
        validacao = validar_migracao(conn_oracle, conn_pg, tabela)
        resultados_validacao.append(validacao)

        resultados_extracao.append({
            "tabela":  tabela,
            "linhas":  len(df),
            "arquivo": str(arquivo),
            "status":  "sucesso",
        })

    # Salva relatório de migração
    DATA_LAKE.mkdir(exist_ok=True)
    relatorio = {
        "pipeline":          "oracle_to_cloud_migration",
        "data_execucao":     datetime.now().isoformat(),
        "origem":            "Oracle 21c XE — XEPDB1.financeiro",
        "destino_datalake":  str(BRONZE),
        "destino_cloud":     "PostgreSQL 15 — financeiro_cloud",
        "tabelas":           resultados_extracao,
        "validacao":         resultados_validacao,
        "total_tabelas":     len(TABELAS),
        "validacoes_ok":     sum(1 for v in resultados_validacao if v["count_ok"]),
    }

    arquivo_relatorio = DATA_LAKE / f"relatorio_migracao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(arquivo_relatorio, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False, default=str)

    # Resumo final
    logger.info("\n" + "=" * 60)
    logger.info("RESUMO DA MIGRAÇÃO")
    logger.info("=" * 60)
    total_linhas = sum(r["linhas"] for r in resultados_extracao)
    validacoes_ok = relatorio["validacoes_ok"]
    logger.success(f"Tabelas migradas:  {len(TABELAS)}")
    logger.success(f"Total de linhas:   {total_linhas:,}")
    logger.success(f"Validações OK:     {validacoes_ok}/{len(TABELAS)}")
    logger.success(f"Relatório salvo:   {arquivo_relatorio}")

    if validacoes_ok == len(TABELAS):
        logger.success("MIGRAÇÃO CONCLUÍDA COM SUCESSO! ✅")
    else:
        logger.warning("MIGRAÇÃO COM DIVERGÊNCIAS! Verifique o relatório.")

    conn_oracle.close()
    conn_pg.close()

if __name__ == "__main__":
    main()
