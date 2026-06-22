from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3

app = Flask(__name__)
DB_FILE = "banco.db"

def conectar_banco():
    """ Cria uma conexão com o banco de dados SQLite """
    return sqlite3.connect(DB_FILE)

def inicializar_banco():
    """ Cria as tabelas e insere os dados iniciais se não existirem """
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Tabela de Usuários para Autenticação
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL
        )
    ''')
    
    # Tabela de Histórico de Ponto e Pausas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_ponto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            evento TEXT NOT NULL,
            horario TEXT NOT NULL
        )
    ''')
    
    # Tabela de Relatório de Vendas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS relatorio_vendas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendedor TEXT NOT NULL,
            cliente TEXT NOT NULL,
            resultado TEXT NOT NULL,
            horario TEXT NOT NULL
        )
    ''')

    # Tabela de Mailing Dinâmico
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mailing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendedor TEXT NOT NULL,
            nome_cliente TEXT NOT NULL,
            telefone TEXT NOT NULL,
            status TEXT DEFAULT 'Pendente'
        )
    ''')
    
    # Inserir usuários padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", ("vendedor1", "senha123"))
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", ("vendedor2", "senha456"))
        print("👤 Usuários padrão criados no banco (vendedor1 / vendedor2)")

    # Inserir mailing de teste padrão se a tabela estiver vazia
    cursor.execute("SELECT COUNT(*) FROM mailing")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO mailing (vendedor, nome_cliente, telefone) VALUES (?, ?, ?)", ("vendedor1", "Arnaldo Ribeiro", "5511911112222"))
        cursor.execute("INSERT INTO mailing (vendedor, nome_cliente, telefone) VALUES (?, ?, ?)", ("vendedor1", "Beatriz Souza", "5521933334444"))
        cursor.execute("INSERT INTO mailing (vendedor, nome_cliente, telefone) VALUES (?, ?, ?)", ("vendedor1", "Cláudio Castro", "5531955556666"))
        print("📞 Lista de Mailing padrão carregada para o vendedor1.")
    
    conn.commit()
    conn.close()
    print("💾 Banco de dados inicializado com sucesso!")

# Executa a inicialização do banco para garantir a criação das tabelas na nuvem (Gunicorn)
inicializar_banco()

# === ROTA DE LOGIN ===
@app.route('/api/login', methods=['POST'])
def verificar_login():
    data = request.json
    usuario = data.get('usuario')
    senha = data.get('senha')
    
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (usuario, senha))
    usuario_encontrado = cursor.fetchone()
    conn.close()
    
    if usuario_encontrado:
        print(f"🔒 [LOGIN] Acesso permitido para: {usuario}")
        return jsonify({"status": "sucesso", "mensagem": "Acesso permitido!"}), 200
    
    print(f"🚨 [LOGIN FALHOU] Tentativa incorreta para: {usuario}")
    return jsonify({"status": "erro", "mensagem": "Usuário ou senha incorretos."}), 401

# === ROTA: BUSCAR MAILING DO VENDEDOR ===
@app.route('/api/mailing/<usuario>', methods=['GET'])
def obtener_mailing(usuario):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT nome_cliente, telefone FROM mailing WHERE vendedor = ? AND status = 'Pendente'", (usuario,))
    linhas = cursor.fetchall()
    conn.close()
    
    lista_contatos = [{"nome": r[0], "telefone": r[1]} for r in linhas]
    return jsonify(lista_contatos), 200

# === ROTA: REGISTRO DE PONTO E PAUSAS ===
@app.route('/api/ponto', methods=['POST'])
def registrar_ponto():
    data = request.json
    usuario = data.get('usuario')
    evento = data.get('evento')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO historico_ponto (usuario, evento, horario) VALUES (?, ?, ?)", (usuario, evento, timestamp))
    conn.commit()
    conn.close()
    
    print(f"📌 [SQLITE PONTO] {timestamp} - {usuario}: {evento}")
    return jsonify({"status": "sucesso", "mensagem": "Evento salvo no banco!"}), 200

# === ROTA: REGISTRO E FEEDBACK DE VENDAS ===
@app.route('/api/vendas', methods=['POST'])
def registrar_venda():
    data = request.json
    usuario = data.get('usuario')
    cliente = data.get('cliente')
    resultado = data.get('resultado')
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    conn = conectar_banco()
    cursor = conn.cursor()
    
    cursor.execute("INSERT INTO relatorio_vendas (vendedor, cliente, resultado, horario) VALUES (?, ?, ?, ?)", (usuario, cliente, resultado, timestamp))
    cursor.execute("UPDATE mailing SET status = ? WHERE nome_cliente = ? AND vendedor = ?", (resultado, cliente, usuario))
    
    conn.commit()
    conn.close()
    
    print(f"💰 [SQLITE VENDA] {timestamp} - {usuario} -> {cliente}: {resultado}")
    return jsonify({"status": "sucesso", "mensagem": "Venda salva e mailing updated!"}), 200

# === ROTA: EXTRAÇÃO DE RELATÓRIOS GERAIS ===
@app.route('/api/relatorio', methods=['GET'])
def extrair_relatorio():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    cursor.execute("SELECT usuario, evento, horario FROM historico_ponto ORDER BY id DESC")
    pontos = [{"usuario": r[0], "evento": r[1], "horario": r[2]} for r in cursor.fetchall()]
    
    cursor.execute("SELECT vendedor, cliente, resultado, horario FROM relatorio_vendas ORDER BY id DESC")
    vendas = [{"vendedor": r[0], "cliente": r[1], "resultado": r[2], "horario": r[3]} for r in cursor.fetchall()]
    
    conn.close()
    return jsonify({"ponto_e_pausas": pontos, "campanha_vendas": vendas}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)