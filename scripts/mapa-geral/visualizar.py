#!/usr/bin/env python3
# Servidor local do visualizar.html (ferramenta de desenvolvimento): serve a raiz do repositório, como
# `python3 -m http.server`, e grava as anotações feitas no visualizador em scripts/mapa-geral/anotacoes.json
# (POST desse caminho; escrita atômica). Só escuta em 127.0.0.1.
# Uso (de qualquer pasta):  python3 scripts/mapa-geral/visualizar.py [porta]   (padrão 8001)
# e abra http://localhost:8001/scripts/mapa-geral/visualizar.html
import functools, http.server, json, os, sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, "..", ".."))
ANOTACOES = os.path.join(AQUI, "anotacoes.json")
CAMINHO = "/scripts/mapa-geral/anotacoes.json"
TIPOS = {"mesmo_estado", "estados_diferentes", "problema"}


class Manipulador(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        if self.path.split("?")[0] == CAMINHO:
            self.send_header("X-Grava-Anotacoes", "1")
        super().end_headers()

    def do_HEAD(self):
        if self.path.split("?")[0] == CAMINHO and not os.path.exists(ANOTACOES):
            self.send_response(204)
            self.end_headers()
            return
        super().do_HEAD()

    def do_POST(self):
        if self.path.split("?")[0] != CAMINHO:
            self.send_error(404)
            return
        try:
            corpo = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            notas = corpo["anotacoes"]
            assert isinstance(notas, list) and all(n.get("tipo") in TIPOS and "ano" in n and "mapa" in n for n in notas)
        except Exception as e:
            self.send_error(400, "anotações inválidas: %s" % e)
            return
        tmp = ANOTACOES + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(corpo, f, ensure_ascii=False, indent=1)
            f.write("\n")
        os.replace(tmp, ANOTACOES)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')


if __name__ == "__main__":
    porta = int(sys.argv[1]) if len(sys.argv) > 1 else 8001
    servidor = http.server.ThreadingHTTPServer(("127.0.0.1", porta), functools.partial(Manipulador, directory=RAIZ))
    print("http://localhost:%d/scripts/mapa-geral/visualizar.html  (anotações em %s)" % (porta, ANOTACOES))
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
