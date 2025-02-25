import sqlite3
from datetime import datetime

def criar_conexao():
    """Cria uma conexão com o banco de dados SQLite"""
    return sqlite3.connect('linkedin.db')

def criar_tabelas():
    """Cria as tabelas necessárias no banco de dados"""
    conn = criar_conexao()
    cursor = conn.cursor()
    
    # Tabela de candidatos
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS candidatos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT NOT NULL,
        titulo TEXT,
        empresa TEXT,
        localizacao TEXT,
        experiencia TEXT,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        data_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # Tabela de experiências
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS experiencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidato_id INTEGER,
        empresa TEXT,
        cargo TEXT,
        periodo TEXT,
        descricao TEXT,
        data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (candidato_id) REFERENCES candidatos (id)
    )
    ''')
    
    conn.commit()
    conn.close()