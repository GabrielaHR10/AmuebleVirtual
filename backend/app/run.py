"""Arranca el servidor en 127.0.0.1:8000 y abre el navegador."""

import os
import socket
import sys
import threading
import webbrowser

import uvicorn

from app.config import HOST, PORT

URL = f"http://localhost:{PORT}"


def port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def main() -> None:
    if port_in_use(HOST, PORT):
        print(
            f"\nEl puerto {PORT} ya está ocupado.\n"
            f"Puede que el Estudio Virtual ya esté abierto: entra a {URL}\n"
            "Si no, cierra la otra ventana/programa que usa ese puerto y vuelve a intentar.\n",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"\nEstudio Virtual — abriendo {URL}\nPara cerrar, cierra esta ventana (o Ctrl+C).\n")
    if os.getenv("NO_BROWSER") != "1":  # NO_BROWSER=1 en CI y pruebas
        threading.Timer(1.5, lambda: webbrowser.open(URL)).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
