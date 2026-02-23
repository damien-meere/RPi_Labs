
import socket
import sys

# --- Configuration ---
HOST = "192.168.0.48"   # <-- Replace with your Raspberry Pi's IP or hostname
PORT = 8080            # <-- Must match the server port

def main():
    # Create a TCP client socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcpCliSock:
        try:
            print(f"Connecting to {HOST}:{PORT} ...")
            tcpCliSock.connect((HOST, PORT))
            print("Connected. Type 'on', 'off', or 'bye' to exit.")
        except Exception as e:
            print(f"Failed to connect: {e}")
            sys.exit(1)

        try:
            while True:
                # Get command from the user (Python 3 returns str)
                cmd = input("Input command: ").strip()

                if not cmd:
                    # Ignore empty lines
                    continue

                # Send bytes over the socket (encode to UTF-8)
                tcpCliSock.send((cmd + "\n").encode("utf-8"))

                # If we plan to close after 'bye', optionally break after reading server reply
                if cmd.lower() == "bye":
                    # Read final response (if any) then exit loop
                    try:
                        data = tcpCliSock.recv(1024)
                        if data:
                            print("Server:", data.decode("utf-8", errors="replace").strip())
                    except Exception:
                        pass
                    break

                # Receive response from server (bytes) and decode to str
                data = tcpCliSock.recv(1024)
                if not data:
                    print("Server closed the connection.")
                    break

                reply = data.decode("utf-8", errors="replace").strip()
                print("Server:", reply)

        except KeyboardInterrupt:
            print("\n[Interrupted] Closing client.")
        except Exception as e:
            print(f"[Error] {e}")
        finally:
            # Socket is auto-closed by the context manager
            pass

if __name__ == "__main__":
    main()
