# ================================================================
# generate_data.py
# Gera dados financeiros sintéticos no Oracle 21c
# Uso: python sql/oracle/seed_data/generate_data.py
# ================================================================

import oracledb
import random
from faker import Faker
from datetime import datetime, timedelta
from loguru import logger

fake = Faker("pt_BR")
random.seed(42)

# ----------------------------------------------------------------
# Configuração de conexão Oracle
# ----------------------------------------------------------------
DB_CONFIG = {
    "host":     "localhost",
    "port":     1521,
    "service":  "XEPDB1",
    "user":     "financeiro",
    "password": "Financeiro123",
}

QTD_CLIENTES     = 300
QTD_COMERCIANTES = 80
QTD_TRANSACOES   = 30_000

ESTADOS_BR   = ["SP","RJ","MG","BA","RS","PR","PE","CE","GO","SC"]
TIPOS        = ["debito","credito","pix","ted","doc","boleto"]
STATUS       = ["aprovada","aprovada","aprovada","negada","cancelada","suspeita"]
CANAIS       = ["app","app","web","pos","atm","agencia"]

# ----------------------------------------------------------------
# Conexão
# ----------------------------------------------------------------
def conectar():
    logger.info("Conectando ao Oracle 21c...")
    dsn = f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['service']}"
    conn = oracledb.connect(
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        dsn=dsn,
    )
    logger.success("Conectado ao Oracle!")
    return conn

# ----------------------------------------------------------------
# Geração de dados
# ----------------------------------------------------------------
def gerar_clientes(cursor, qtd):
    logger.info(f"Gerando {qtd} clientes...")
    cpfs_usados   = set()
    emails_usados = set()
    inseridos     = 0

    for _ in range(qtd):
        cpf   = fake.cpf()
        email = fake.email()
        if cpf in cpfs_usados or email in emails_usados:
            continue
        cpfs_usados.add(cpf)
        emails_usados.add(email)

        cursor.execute("""
            INSERT INTO clientes
                (nome, cpf, email, data_nascimento, genero, cidade, estado, score_credito)
            VALUES (:1,:2,:3,:4,:5,:6,:7,:8)
        """, (
            fake.name(),
            cpf,
            email,
            fake.date_of_birth(minimum_age=18, maximum_age=75),
            random.choice(["M","F","O"]),
            fake.city(),
            random.choice(ESTADOS_BR),
            random.randint(300, 1000),
        ))
        inseridos += 1

    logger.success(f"{inseridos} clientes inseridos.")
    return inseridos


def gerar_contas(cursor):
    logger.info("Gerando contas bancárias...")
    cursor.execute("SELECT id_cliente FROM clientes")
    clientes  = [r[0] for r in cursor.fetchall()]
    numeros   = set()
    inseridos = 0

    for id_cliente in clientes:
        for _ in range(random.randint(1, 3)):
            numero = fake.numerify("####-#####-#")
            if numero in numeros:
                continue
            numeros.add(numero)
            tipo   = random.choice(["corrente","poupanca","investimento","cartao"])
            saldo  = round(random.uniform(-500, 50000), 2)
            limite = round(random.uniform(1000, 20000), 2) if tipo == "cartao" else 0

            cursor.execute("""
                INSERT INTO contas (id_cliente, numero_conta, tipo_conta, saldo, limite)
                VALUES (:1,:2,:3,:4,:5)
            """, (id_cliente, numero, tipo, saldo, limite))
            inseridos += 1

    logger.success(f"{inseridos} contas inseridas.")


def gerar_comerciantes(cursor, qtd):
    logger.info(f"Gerando {qtd} comerciantes...")
    categorias = ["alimentacao","transporte","saude","educacao",
                  "lazer","compras","servicos","outros"]
    cnpjs = set()

    for _ in range(qtd):
        cnpj = fake.cnpj()
        if cnpj in cnpjs:
            continue
        cnpjs.add(cnpj)

        cursor.execute("""
            INSERT INTO comerciantes (nome, categoria, cidade, estado, cnpj)
            VALUES (:1,:2,:3,:4,:5)
        """, (
            fake.company(),
            random.choice(categorias),
            fake.city(),
            random.choice(ESTADOS_BR),
            cnpj,
        ))

    logger.success(f"{qtd} comerciantes inseridos.")


def gerar_transacoes(cursor, qtd):
    logger.info(f"Gerando {qtd} transações...")

    cursor.execute("SELECT id_conta FROM contas")
    contas = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT id_categoria FROM categorias_transacao")
    categorias = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT id_comerciante FROM comerciantes")
    comerciantes = [r[0] for r in cursor.fetchall()]

    data_inicio = datetime.now() - timedelta(days=365)
    batch       = []
    BATCH_SIZE  = 500

    for i in range(qtd):
        data_transacao = data_inicio + timedelta(
            seconds=random.randint(0, 365 * 24 * 3600)
        )
        is_fraude    = 1 if random.random() < 0.02 else 0
        score_fraude = round(random.uniform(0.7, 1.0), 4) if is_fraude \
                       else round(random.uniform(0.0, 0.3), 4)
        valor  = round(random.uniform(500, 15000), 2) if is_fraude \
                 else round(random.uniform(1, 3000), 2)
        status = "suspeita" if is_fraude else random.choice(STATUS)

        batch.append((
            random.choice(contas),
            random.choice(categorias),
            random.choice(comerciantes) if random.random() > 0.2 else None,
            valor,
            random.choice(TIPOS),
            status,
            random.choice(CANAIS),
            fake.sentence(nb_words=4)[:255],
            data_transacao,
            data_transacao + timedelta(seconds=random.randint(1, 300)),
            is_fraude,
            score_fraude,
            fake.ipv4(),
            fake.uuid4()[:100],
        ))

        if len(batch) >= BATCH_SIZE:
            cursor.executemany("""
                INSERT INTO transacoes
                    (id_conta, id_categoria, id_comerciante, valor, tipo,
                     status, canal, descricao, data_transacao, data_processamento,
                     is_fraude, score_fraude, ip_origem, device_id)
                VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13,:14)
            """, batch)
            batch = []
            logger.info(f"  {i+1}/{qtd} transações inseridas...")

    if batch:
        cursor.executemany("""
            INSERT INTO transacoes
                (id_conta, id_categoria, id_comerciante, valor, tipo,
                 status, canal, descricao, data_transacao, data_processamento,
                 is_fraude, score_fraude, ip_origem, device_id)
            VALUES (:1,:2,:3,:4,:5,:6,:7,:8,:9,:10,:11,:12,:13,:14)
        """, batch)

    logger.success(f"{qtd} transações inseridas.")

# ----------------------------------------------------------------
# Main
# ----------------------------------------------------------------
def main():
    logger.info("=" * 55)
    logger.info("GERADOR DE DADOS — ORACLE 21c")
    logger.info("=" * 55)

    conn   = conectar()
    cursor = conn.cursor()

    try:
        gerar_clientes(cursor, QTD_CLIENTES)
        conn.commit()

        gerar_contas(cursor)
        conn.commit()

        gerar_comerciantes(cursor, QTD_COMERCIANTES)
        conn.commit()

        gerar_transacoes(cursor, QTD_TRANSACOES)
        conn.commit()

        # Resumo
        for tabela in ["clientes","contas","comerciantes","transacoes"]:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            total = cursor.fetchone()[0]
            logger.success(f"{tabela:<20} {total:>8,} registros")

        cursor.execute("SELECT COUNT(*) FROM transacoes WHERE is_fraude = 1")
        logger.success(f"{'fraudes':<20} {cursor.fetchone()[0]:>8,} registros")

        logger.success("Dados gerados com sucesso!")

    except Exception as e:
        conn.rollback()
        logger.error(f"Erro: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
