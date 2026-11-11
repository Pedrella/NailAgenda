
from flask import Flask, render_template, request, redirect, url_for
from database import conectar
from datetime import datetime, timedelta


app = Flask(__name__)

@app.route("/")
def inicio():
    return render_template("index.html")



@app.route("/dashboard")
def dashboard():

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM clientes) AS total_clientes,
            (SELECT COUNT(*) FROM servicos) AS total_servicos,
            (SELECT COUNT(*) FROM agendamentos) AS total_agendamentos,
            (SELECT COUNT(*) FROM agendamentos
             WHERE status = 'Pendente') AS agendamentos_pendentes
    """)

    indicadores = cursor.fetchone()

    cursor.close()
    conexao.close()

    return render_template(
        "dashboard.html",
        indicadores=indicadores
    )





from datetime import datetime, timedelta

# CADASTRAR E LISTAR AGENDAMENTOS
@app.route("/agendamentos", methods=["GET", "POST"])
def agendamentos():

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    if request.method == "POST":

        cliente_id = request.form["cliente_id"]
        servico_id = request.form["servico_id"]
        data = request.form["data"]
        horario = request.form["horario"]

        cursor.execute(
            "SELECT duracao FROM servicos WHERE id = %s",
            (servico_id,)
        )
        servico = cursor.fetchone()

        if servico is None:
            cursor.close()
            conexao.close()
            return "Serviço não encontrado", 404

        inicio = datetime.strptime(horario, "%H:%M").time()
        inicio = datetime.combine(
            datetime.strptime(data, "%Y-%m-%d").date(),
            inicio
        )

        fim = inicio + timedelta(minutes=servico["duracao"])

        # Verificar conflito de horários
        cursor.execute("""
            SELECT a.horario, s.duracao
            FROM agendamentos a
            JOIN servicos s ON a.servico_id = s.id
            WHERE a.data = %s
            AND a.status != 'Cancelado'
        """, (data,))

        horarios_existentes = cursor.fetchall()

        conflito = False

        for agendamento in horarios_existentes:

            horario_existente = agendamento["horario"]

            if isinstance(horario_existente, timedelta):
                horario_existente = (
                 datetime.min + horario_existente
                ).time()

            inicio_existente = datetime.combine(
                inicio.date(),
                horario_existente
            )

            fim_existente = inicio_existente + timedelta(
                minutes=agendamento["duracao"]
            )

            if inicio < fim_existente and fim > inicio_existente:
                conflito = True
                break

        if conflito:
            cursor.close()
            conexao.close()
            return "Horário indisponível! Escolha outro horário.", 409

        cursor.execute("""
            INSERT INTO agendamentos
            (cliente_id, servico_id, `data`, horario, status)
            VALUES (%s, %s, %s, %s, 'Pendente')
        """, (cliente_id, servico_id, data, horario))

        conexao.commit()
        cursor.close()
        conexao.close()

        return redirect(url_for("agendamentos"))

    cursor.execute("SELECT * FROM clientes ORDER BY nome")
    lista_clientes = cursor.fetchall()

    cursor.execute("SELECT * FROM servicos ORDER BY nome")
    lista_servicos = cursor.fetchall()

    cursor.execute("""
        SELECT a.id, a.data, a.horario, a.status,
               c.nome AS cliente,
               s.nome AS servico,
               s.preco
        FROM agendamentos a
        JOIN clientes c ON a.cliente_id = c.id
        JOIN servicos s ON a.servico_id = s.id
        ORDER BY a.data, a.horario
    """)

    lista_agendamentos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        "agendamentos.html",
        clientes=lista_clientes,
        servicos=lista_servicos,
        agendamentos=lista_agendamentos
    )


# ALTERAR STATUS DO AGENDAMENTO

# ALTERAR STATUS DO AGENDAMENTO
@app.route("/agendamentos/status/<int:id>", methods=["POST"])
def alterar_status(id):

    status = request.form["status"]

    if status not in ["Pendente", "Confirmado", "Cancelado"]:
        return "Status inválido", 400

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute("""
        UPDATE agendamentos
        SET status = %s
        WHERE id = %s
    """, (status, id))

    conexao.commit()
    cursor.close()
    conexao.close()

    return redirect(url_for("agendamentos"))


# EDITAR AGENDAMENTO

@app.route("/agendamentos/editar/<int:id>", methods=["GET", "POST"])
def editar_agendamento(id):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    if request.method == "POST":

        cliente_id = request.form["cliente_id"]
        servico_id = request.form["servico_id"]
        data = request.form["data"]
        horario = request.form["horario"]

        cursor.execute(
            "SELECT duracao FROM servicos WHERE id = %s",
            (servico_id,)
        )
        servico = cursor.fetchone()

        if servico is None:
            cursor.close()
            conexao.close()
            return "Serviço não encontrado", 404

        inicio = datetime.combine(
            datetime.strptime(data, "%Y-%m-%d").date(),
            datetime.strptime(horario, "%H:%M").time()
        )

        fim = inicio + timedelta(minutes=servico["duracao"])

        cursor.execute("""
            SELECT a.horario, s.duracao
            FROM agendamentos a
            JOIN servicos s ON a.servico_id = s.id
            WHERE a.data = %s
            AND a.status != 'Cancelado'
            AND a.id != %s
        """, (data, id))

        existentes = cursor.fetchall()

        for existente in existentes:

            horario_existente = existente["horario"]

            if isinstance(horario_existente, timedelta):
                horario_existente = (
                    datetime.min + horario_existente
                ).time()

            inicio_existente = datetime.combine(
                inicio.date(),
                horario_existente
            )

            fim_existente = inicio_existente + timedelta(
                minutes=existente["duracao"]
            )

            if inicio < fim_existente and fim > inicio_existente:
                cursor.close()
                conexao.close()
                return "Horário indisponível! Escolha outro horário.", 409

        cursor.execute("""
            UPDATE agendamentos
            SET cliente_id = %s,
                servico_id = %s,
                `data` = %s,
                horario = %s
            WHERE id = %s
        """, (cliente_id, servico_id, data, horario, id))

        conexao.commit()
        cursor.close()
        conexao.close()

        return redirect(url_for("agendamentos"))

    cursor.execute(
        "SELECT * FROM agendamentos WHERE id = %s",
        (id,)
    )
    agendamento = cursor.fetchone()

    if agendamento is None:
        cursor.close()
        conexao.close()
        return "Agendamento não encontrado", 404

    if isinstance(agendamento["horario"], timedelta):
        agendamento["horario"] = (
            datetime.min + agendamento["horario"]
        ).time()

    cursor.execute("SELECT * FROM clientes ORDER BY nome")
    clientes = cursor.fetchall()

    cursor.execute("SELECT * FROM servicos ORDER BY nome")
    servicos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        "editar_agendamento.html",
        agendamento=agendamento,
        clientes=clientes,
        servicos=servicos
    )



# EXCLUIR AGENDAMENTO
@app.route("/agendamentos/excluir/<int:id>", methods=["POST"])
def excluir_agendamento(id):

    conexao = conectar()
    cursor = conexao.cursor()

    cursor.execute(
        "DELETE FROM agendamentos WHERE id = %s",
        (id,)
    )

    conexao.commit()

    cursor.close()
    conexao.close()

    return redirect(url_for("agendamentos"))



# =========================
# CLIENTES
# =========================

# CADASTRAR E LISTAR CLIENTES
@app.route("/clientes", methods=["GET", "POST"])
def clientes():

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    if request.method == "POST":

        nome = request.form["nome"]
        telefone = request.form["telefone"]
        email = request.form.get("email")

        cursor.execute("""
            INSERT INTO clientes (nome, telefone, email)
            VALUES (%s, %s, %s)
        """, (nome, telefone, email))

        conexao.commit()

    cursor.execute("SELECT * FROM clientes ORDER BY nome")
    lista_clientes = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        "clientes.html",
        clientes=lista_clientes
    )


# EDITAR CLIENTE
@app.route("/clientes/editar/<int:id>", methods=["GET", "POST"])
def editar_cliente(id):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    if request.method == "POST":

        nome = request.form["nome"]
        telefone = request.form["telefone"]
        email = request.form.get("email")

        cursor.execute("""
            UPDATE clientes
            SET nome = %s,
                telefone = %s,
                email = %s
            WHERE id = %s
        """, (nome, telefone, email, id))

        conexao.commit()

        cursor.close()
        conexao.close()

        return redirect(url_for("clientes"))

    cursor.execute(
        "SELECT * FROM clientes WHERE id = %s",
        (id,)
    )

    cliente = cursor.fetchone()

    cursor.close()
    conexao.close()

    if cliente is None:
        return "Cliente não encontrado", 404

    return render_template(
        "editar_cliente.html",
        cliente=cliente
    )


# EXCLUIR CLIENTE
@app.route("/clientes/excluir/<int:id>", methods=["POST"])
def excluir_cliente(id):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM agendamentos
        WHERE cliente_id = %s
    """, (id,))

    resultado = cursor.fetchone()

    if resultado["total"] > 0:
        cursor.close()
        conexao.close()
        return "Não é possível excluir: este cliente possui agendamentos cadastrados."

    cursor.execute(
        "DELETE FROM clientes WHERE id = %s",
        (id,)
    )

    conexao.commit()

    cursor.close()
    conexao.close()

    return redirect(url_for("clientes"))


# =========================
# SERVIÇOS
# =========================

# CADASTRAR E LISTAR SERVIÇOS
@app.route("/servicos", methods=["GET", "POST"])
def servicos():

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    if request.method == "POST":

        nome = request.form["nome"]
        descricao = request.form.get("descricao")
        preco = request.form["preco"]
        duracao = request.form["duracao"]

        cursor.execute("""
            INSERT INTO servicos (nome, descricao, preco, duracao)
            VALUES (%s, %s, %s, %s)
        """, (nome, descricao, preco, duracao))

        conexao.commit()

    cursor.execute("SELECT * FROM servicos ORDER BY nome")
    lista_servicos = cursor.fetchall()

    cursor.close()
    conexao.close()

    return render_template(
        "servicos.html",
        servicos=lista_servicos
    )


# EDITAR SERVIÇO
@app.route("/servicos/editar/<int:id>", methods=["GET", "POST"])
def editar_servico(id):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    if request.method == "POST":

        nome = request.form["nome"]
        descricao = request.form.get("descricao")
        preco = request.form["preco"]
        duracao = request.form["duracao"]

        cursor.execute("""
            UPDATE servicos
            SET nome = %s,
                descricao = %s,
                preco = %s,
                duracao = %s
            WHERE id = %s
        """, (nome, descricao, preco, duracao, id))

        conexao.commit()

        cursor.close()
        conexao.close()

        return redirect(url_for("servicos"))

    cursor.execute(
        "SELECT * FROM servicos WHERE id = %s",
        (id,)
    )

    servico = cursor.fetchone()

    cursor.close()
    conexao.close()

    if servico is None:
        return "Serviço não encontrado", 404

    return render_template(
        "editar_servico.html",
        servico=servico
    )


# EXCLUIR SERVIÇO
@app.route("/servicos/excluir/<int:id>", methods=["POST"])
def excluir_servico(id):

    conexao = conectar()
    cursor = conexao.cursor(dictionary=True)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM agendamentos
        WHERE servico_id = %s
    """, (id,))

    resultado = cursor.fetchone()

    if resultado["total"] > 0:
        cursor.close()
        conexao.close()
        return "Não é possível excluir: este serviço possui agendamentos cadastrados."

    cursor.execute(
        "DELETE FROM servicos WHERE id = %s",
        (id,)
    )

    conexao.commit()

    cursor.close()
    conexao.close()

    return redirect(url_for("servicos"))


if __name__ == "__main__":
    app.run(debug=True)