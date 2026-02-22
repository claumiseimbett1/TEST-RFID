import socket

# Protocolo: TCP/IP. Cliente que se conecta al equipo y muestra los datos recibidos.
# Equipo que envía los datos (tu PC debe estar en la misma red, ej. 192.168.0.x)
HOST = "192.168.0.178"
PORT = 4001

def main():
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        conn.connect((HOST, PORT))
        conn.settimeout(1.0)
        print(f"Conectado a {HOST}:{PORT}. Mostrando datos (Ctrl+C para salir):\n")
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    print("[Conexión cerrada por el equipo]")
                    break
                try:
                    texto = data.decode("utf-8", errors="replace").strip()
                    if texto:
                        print(texto, flush=True)
                except Exception:
                    print(data.hex(), flush=True)
            except socket.timeout:
                continue
    except socket.error as e:
        print("Error de conexión:", e)
        print("Comprueba que el equipo esté encendido y en 192.168.0.178:4001")
    except KeyboardInterrupt:
        print("\nCerrando...")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
