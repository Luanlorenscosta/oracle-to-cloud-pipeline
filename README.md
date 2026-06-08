# 🏛️ Oracle to Cloud Pipeline — Portfólio de Migração de Dados

![Oracle](https://img.shields.io/badge/Oracle-21c_XE-red?logo=oracle)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue?logo=postgresql)
![Python](https://img.shields.io/badge/Python-3.11+-blue?logo=python)
![Docker](https://img.shields.io/badge/Docker-Compose-blue?logo=docker)
![Kafka](https://img.shields.io/badge/Apache_Kafka-7.5-black?logo=apachekafka)

> Portfólio demonstrando migração completa de banco Oracle 21c legado para ambiente cloud moderno, com pipeline ETL, Data Lake em Parquet e validação de integridade dos dados.

## 🎯 Visão Geral

Simula o cenário mais comum em grandes empresas brasileiras — migração de sistemas Oracle legados para arquitetura cloud moderna:

- **Oracle 21c XE** como banco fonte (legado corporativo)
- **30.000 transações financeiras** sintéticas migradas
- **Validação 5/5** — zero divergências origem vs destino
- **Data Lake Bronze** em Parquet particionado por data
- **PostgreSQL** como destino cloud

## 🛠️ Stack Tecnológica

| Componente | Tecnologia | Equivalente Azure |
|---|---|---|
| Banco Fonte | Oracle 21c XE (Docker) | Oracle on Azure VM |
| Extração | Python + oracledb | Azure Data Factory |
| Data Lake | Parquet local | ADLS Gen2 |
| Destino Cloud | PostgreSQL 15 (Docker) | Azure SQL Database |
| Streaming | Apache Kafka | Azure Event Hub |
| CI/CD | GitHub Actions | Azure DevOps |

## 🚀 Como Executar

### 1. Clone e instale dependências
```bash
git clone https://github.com/Luanlorenscosta/oracle-to-cloud-pipeline.git
cd oracle-to-cloud-pipeline
pip install oracledb psycopg2-binary pandas pyarrow faker loguru
```

### 2. Configure memória WSL (necessário para Oracle)
```bash
# Crie ~/.wslconfig com:
[wsl2]
memory=5GB
processors=4
```

### 3. Suba o ambiente Docker
```bash
docker-compose up -d
# Aguarde ~3 minutos para o Oracle inicializar
```

### 4. Crie as tabelas e gere os dados
```bash
docker cp sql/oracle/ddl/01_create_tables.sql oracle-source:/tmp/
docker exec oracle-source sqlplus financeiro/Financeiro123@XEPDB1 '@/tmp/01_create_tables.sql'
python sql/oracle/seed_data/generate_data.py
```

### 5. Execute o pipeline de migração
```bash
python pipelines/extract/01_extract_oracle.py
```

## 📊 Resultados da Migração

| Tabela | Oracle (origem) | PostgreSQL (destino) | Status |
|---|---|---|---|
| categorias_transacao | 14 | 14 | ✅ OK |
| clientes | 300 | 300 | ✅ OK |
| comerciantes | 80 | 80 | ✅ OK |
| contas | 613 | 613 | ✅ OK |
| transacoes | 30.000 | 30.000 | ✅ OK |
| **Total** | **31.007** | **31.007** | **✅ 5/5** |

## 🔍 Validação de Integridade

O pipeline compara automaticamente:
- Contagem de linhas por tabela
- Soma de valores financeiros
- Gera relatório JSON com resultado completo

## 👨‍💻 Autor

**Luan Lorens da Costa** — DBA Sênior | Oracle · PostgreSQL · SQL Server | Data Engineering

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Luan_Lorens-blue?logo=linkedin)](https://www.linkedin.com/in/luan-lorens-da-costa/)

**Certificações:** AZ-900 | DP-900 | DP-300 | OCP (em andamento)

---

> Veja também: [azure-dataeng-financeiro](https://github.com/Luanlorenscosta/azure-dataeng-financeiro) — portfólio Azure Data Engineering completo
