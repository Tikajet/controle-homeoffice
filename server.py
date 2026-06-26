from flask import Flask, request, jsonify
from datetime import datetime
import sqlite3

app = Flask(__name__)
DB_FILE = "banco.db"

def conectar_banco():
    return sqlite3.connect(DB_FILE)

def inicializar_banco():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, senha TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico_ponto (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT NOT NULL, evento TEXT NOT NULL, horario TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS relatorio_vendas (id INTEGER PRIMARY KEY AUTOINCREMENT, vendedor TEXT NOT NULL, cliente TEXT NOT NULL, resultado TEXT NOT NULL, horario TEXT NOT NULL)''')
    
    # === TABELA DE MAILING (AGORA COM SUPORTE A COBRANÇAS E VENDAS) ===
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mailing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendedor TEXT NOT NULL,
            nome_cliente TEXT NOT NULL,
            telefone TEXT NOT NULL,
            status TEXT DEFAULT 'Pendente',
            tipo_campanha TEXT DEFAULT 'Vendas', 
            valor_divida REAL DEFAULT 0.0,
            dias_atraso INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS scripts (id INTEGER PRIMARY KEY AUTOINCREMENT, setor TEXT UNIQUE NOT NULL, conteudo TEXT NOT NULL)''')
    
    # Carga Inicial de Usuários
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", ("vendedor1", "senha123"))
        cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (?, ?)", ("vendedor2", "senha456"))

    # === CARGA INICIAL DE MAILING (MISTO: VENDAS E COBRANÇAS) ===
    cursor.execute("SELECT COUNT(*) FROM mailing")
    if cursor.fetchone()[0] == 0:
        # Clientes de Vendas
        cursor.execute("INSERT INTO mailing (vendedor, nome_cliente, telefone, tipo_campanha) VALUES (?, ?, ?, ?)", ("vendedor1", "Arnaldo Ribeiro", "5511911112222", "Vendas"))
        cursor.execute("INSERT INTO mailing (vendedor, nome_cliente, telefone, tipo_campanha) VALUES (?, ?, ?, ?)", ("vendedor1", "Beatriz Souza", "5521933334444", "Vendas"))
        
        # Clientes de Cobrança (Com valor e dias de atraso)
        cursor.execute("INSERT INTO mailing (vendedor, nome_cliente, telefone, tipo_campanha, valor_divida, dias_atraso) VALUES (?, ?, ?, ?, ?, ?)", ("vendedor1", "Cláudio Castro", "5531955556666", "Cobrança", 149.90, 15))
        cursor.execute("INSERT INTO mailing (vendedor, nome_cliente, telefone, tipo_campanha, valor_divida, dias_atraso) VALUES (?, ?, ?, ?, ?, ?)", ("vendedor1", "Daniela Marques", "5541988887777", "Cobrança", 299.80, 45))

    # Carga Inicial de Scripts
    cursor.execute("SELECT COUNT(*) FROM scripts")
    if cursor.fetchone()[0] == 0:
        scripts_iniciais = [
            ("Vendas", "=== SCRIPT DE VENDAS ===\n\nOlá, tudo bem? Aqui é da MetroNet...\n[Apresente o plano de Fibra]"),
            ("Financeiro - Cobrança", "=== SCRIPT DE COBRANÇA ===\n\nOlá, [Nome]. Aqui é do setor financeiro...\n[Fale sobre o atraso de forma cordial]"),
            ("Suporte Técnico", "=== SCRIPT DE SUPORTE ===\n\nOlá, [Nome]. Vamos reiniciar o equipamento...")
        ]
        cursor.executemany("INSERT INTO scripts (setor, conteudo) VALUES (?, ?)", scripts_iniciais)
    
    conn.commit()
    conn.close()

inicializar_banco()

# Rotas (Login, Ponto, Scripts mantidas iguais...)
@app.route('/api/login', methods=['POST'])
def verificar_login():
    data = request.json
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE usuario = ? AND senha = ?", (data.get('usuario'), data.get('senha')))
    user = cursor.fetchone()
    conn.close()
    return jsonify({"status": "sucesso"}) if user else (jsonify({"status": "erro"}), 401)

# === NOVA ROTA: BUSCAR MAILING POR TIPO DE CAMPANHA ===
@app.route('/api/mailing/<usuario>/<tipo_campanha>', methods=['GET'])
def obtener_mailing_filtrado(usuario, tipo_campanha):
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT nome_cliente, telefone, valor_divida, dias_atraso FROM mailing WHERE vendedor = ? AND status = 'Pendente' AND tipo_campanha = ?", (usuario, tipo_campanha))
    linhas = cursor.fetchall()
    conn.close()
    
    lista_contatos = [{"nome": r[0], "telefone": r[1], "valor": r[2], "atraso": r[3]} for r in linhas]
    return jsonify(lista_contatos), 200

@app.route('/api/scripts', methods=['GET'])
def obter_scripts():
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("SELECT setor, conteudo FROM scripts")
    linhas = cursor.fetchall()
    conn.close()
    return jsonify({linha[0]: linha[1] for linha in linhas}), 200

@app.route('/api/vendas', methods=['POST'])
def registrar_venda():
    data = request.json
    conn = conectar_banco()
    cursor = conn.cursor()
    cursor.execute("UPDATE mailing SET status = ? WHERE nome_cliente = ? AND vendedor = ?", (data.get('resultado'), data.get('cliente'), data.get('usuario')))
    conn.commit()
    conn.close()
    return jsonify({"status": "sucesso"}), 200

@app.route('/api/ponto', methods=['POST'])
def registrar_ponto():
    return jsonify({"status": "sucesso"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)