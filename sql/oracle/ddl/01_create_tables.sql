-- ================================================================
-- 01_create_tables.sql
-- Schema financeiro corporativo no Oracle 21c
-- Simula um sistema ERP bancário legado
-- ================================================================

-- ----------------------------------------------------------------
-- Clientes
-- ----------------------------------------------------------------
CREATE TABLE clientes (
    id_cliente      NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome            VARCHAR2(150)   NOT NULL,
    cpf             VARCHAR2(14)    NOT NULL UNIQUE,
    email           VARCHAR2(150)   NOT NULL UNIQUE,
    data_nascimento DATE            NOT NULL,
    genero          CHAR(1)         CHECK (genero IN ('M','F','O')),
    cidade          VARCHAR2(100),
    estado          CHAR(2),
    score_credito   NUMBER(4)       CHECK (score_credito BETWEEN 0 AND 1000),
    data_cadastro   TIMESTAMP       DEFAULT SYSTIMESTAMP,
    ativo           NUMBER(1)       DEFAULT 1 CHECK (ativo IN (0,1))
);

-- ----------------------------------------------------------------
-- Contas
-- ----------------------------------------------------------------
CREATE TABLE contas (
    id_conta        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_cliente      NUMBER          NOT NULL REFERENCES clientes(id_cliente),
    numero_conta    VARCHAR2(20)    NOT NULL UNIQUE,
    tipo_conta      VARCHAR2(20)    NOT NULL CHECK (tipo_conta IN ('corrente','poupanca','investimento','cartao')),
    saldo           NUMBER(15,2)    DEFAULT 0,
    limite          NUMBER(15,2)    DEFAULT 0,
    data_abertura   TIMESTAMP       DEFAULT SYSTIMESTAMP,
    ativa           NUMBER(1)       DEFAULT 1
);

-- ----------------------------------------------------------------
-- Categorias de transação
-- ----------------------------------------------------------------
CREATE TABLE categorias_transacao (
    id_categoria    NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome            VARCHAR2(50)    NOT NULL UNIQUE,
    tipo            VARCHAR2(20)    NOT NULL CHECK (tipo IN ('debito','credito'))
);

INSERT INTO categorias_transacao (nome, tipo) VALUES ('alimentacao',   'debito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('transporte',    'debito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('saude',         'debito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('educacao',      'debito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('lazer',         'debito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('compras',       'debito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('servicos',      'debito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('transferencia', 'debito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('saque',         'debito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('salario',       'credito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('pix_recebido',  'credito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('estorno',       'credito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('investimento',  'credito');
INSERT INTO categorias_transacao (nome, tipo) VALUES ('outros',        'debito');
COMMIT;

-- ----------------------------------------------------------------
-- Comerciantes
-- ----------------------------------------------------------------
CREATE TABLE comerciantes (
    id_comerciante  NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    nome            VARCHAR2(150)   NOT NULL,
    categoria       VARCHAR2(50),
    cidade          VARCHAR2(100),
    estado          CHAR(2),
    cnpj            VARCHAR2(18)    UNIQUE
);

-- ----------------------------------------------------------------
-- Transações
-- ----------------------------------------------------------------
CREATE TABLE transacoes (
    id_transacao        NUMBER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_conta            NUMBER          NOT NULL REFERENCES contas(id_conta),
    id_categoria        NUMBER          REFERENCES categorias_transacao(id_categoria),
    id_comerciante      NUMBER          REFERENCES comerciantes(id_comerciante),
    valor               NUMBER(12,2)    NOT NULL,
    tipo                VARCHAR2(20)    NOT NULL CHECK (tipo IN ('debito','credito','pix','ted','doc','boleto')),
    status              VARCHAR2(20)    NOT NULL CHECK (status IN ('aprovada','negada','cancelada','pendente','suspeita')),
    canal               VARCHAR2(20)    CHECK (canal IN ('app','web','pos','atm','agencia')),
    descricao           VARCHAR2(255),
    data_transacao      TIMESTAMP       DEFAULT SYSTIMESTAMP,
    data_processamento  TIMESTAMP,
    is_fraude           NUMBER(1)       DEFAULT 0,
    score_fraude        NUMBER(5,4),
    ip_origem           VARCHAR2(45),
    device_id           VARCHAR2(100)
);

-- ----------------------------------------------------------------
-- Índices
-- ----------------------------------------------------------------
CREATE INDEX idx_trans_conta  ON transacoes(id_conta);
CREATE INDEX idx_trans_data   ON transacoes(data_transacao);
CREATE INDEX idx_trans_status ON transacoes(status);
CREATE INDEX idx_trans_fraude ON transacoes(is_fraude);
CREATE INDEX idx_contas_cli   ON contas(id_cliente);

-- ----------------------------------------------------------------
-- View analítica
-- ----------------------------------------------------------------
CREATE OR REPLACE VIEW vw_transacoes_completa AS
SELECT
    t.id_transacao,
    t.data_transacao,
    t.valor,
    t.tipo,
    t.status,
    t.canal,
    t.is_fraude,
    t.score_fraude,
    c.numero_conta,
    c.tipo_conta,
    cl.nome         AS nome_cliente,
    cl.cidade       AS cidade_cliente,
    cl.estado       AS estado_cliente,
    cl.score_credito,
    cat.nome        AS categoria,
    com.nome        AS comerciante
FROM transacoes t
JOIN contas                 c   ON t.id_conta       = c.id_conta
JOIN clientes               cl  ON c.id_cliente     = cl.id_cliente
LEFT JOIN categorias_transacao cat ON t.id_categoria = cat.id_categoria
LEFT JOIN comerciantes      com ON t.id_comerciante  = com.id_comerciante;
