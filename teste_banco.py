from database import conectar

try:
    conexao = conectar()

    print("Conexão com MySQL realizada com sucesso!")

    conexao.close()

except Exception as erro:
    print("Erro ao conectar:", erro)