#!/usr/bin/env python3
import tkinter as tk
from tkinter import scrolledtext, filedialog
import os
import subprocess
import re
import threading
import webbrowser
import http.server
import socketserver

class LangAliasApp:
    def __init__(self, root):
        self.root = root
        root.title("LangAlias IDE (Tkinter) - HTML/CSS/JS")
        root.geometry("1000x750")
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.PROJECTS_BASE_DIR = os.path.join(self.BASE_DIR, "Projects")
        self.CODE_SAVE_FILE = os.path.join(self.BASE_DIR, "codigo.txt")

        self.PROJECT_DIRS = {
            "HTML": os.path.join(self.PROJECTS_BASE_DIR, "HtmlProject"),
            "CSS": os.path.join(self.PROJECTS_BASE_DIR, "CssProject"),
            "JS": os.path.join(self.PROJECTS_BASE_DIR, "JsProject")
        }
        self.FILE_EXTENSIONS = {"HTML": ".html", "CSS": ".css", "JS": ".js"}
        self.ALIAS_FILES = {"HTML": "alias_html.txt", "CSS": "alias_css.txt", "JS": "alias_js.txt"}

        os.makedirs(self.PROJECTS_BASE_DIR, exist_ok=True)
        for d in self.PROJECT_DIRS.values():
            os.makedirs(d, exist_ok=True)

        self.lang_var = tk.StringVar(root, "HTML")
        self.current_alias_file = tk.StringVar(root, self.ALIAS_FILES["HTML"])
        self.auto_save_var = tk.BooleanVar(root, True)
        self.auto_run_var = tk.BooleanVar(root, False)
        self.auto_run_job = None
        self.AUTO_RUN_DELAY_MS = 1500
        self.setup_layout()
        self._load_saved_code()
        self.code_input.bind("<KeyRelease>", self._on_key_release)
        self.log("Sistema LangAlias IDE iniciado. Selecione a linguagem e comece a programar.")

        self.port = 8000
        self.server_thread = None

    def setup_layout(self):
        control_frame = tk.Frame(self.root)
        control_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(control_frame, text="Linguagem:").pack(side='left', padx=5)
        for lang in ["HTML", "CSS", "JS"]:
            tk.Radiobutton(control_frame, text=lang, variable=self.lang_var,
                           value=lang, command=self.update_alias_file_label).pack(side='left', padx=5)

        tk.Checkbutton(control_frame, text="💾 Auto Save", variable=self.auto_save_var).pack(side='left', padx=10)
        tk.Checkbutton(control_frame, text="▶️ Auto Run", variable=self.auto_run_var).pack(side='left', padx=5)

        tk.Button(control_frame, text="🔄 Aplicar Aliases", command=self.handle_convert).pack(side='left', padx=15, fill='x', expand=True)
        tk.Button(control_frame, text="⚙️ Gerenciar Aliases", command=self.manage_aliases).pack(side='left', padx=15, fill='x', expand=True)
        tk.Button(control_frame, text="🌐 Abrir Localhost", command=self.open_localhost).pack(side='left', padx=15, fill='x', expand=True)

        tk.Frame(self.root, height=1, bg='gray').pack(fill='x', padx=10)

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Label(main_frame, text="Código de Entrada / Saída").pack(fill='x')
        self.code_input = scrolledtext.ScrolledText(main_frame, wrap="word", height=20, font=("Consolas", 12))
        self.code_input.pack(fill='both', expand=True, pady=(5,10))

        tk.Label(main_frame, text="Output / Logs").pack(fill='x')
        self.output_console = scrolledtext.ScrolledText(main_frame, wrap="word", height=10, font=("Consolas", 10),
                                                        bg="#000000", fg="#FFFFFF", insertbackground="#FFFFFF")
        self.output_console.pack(fill='x')

    def log(self, message):
        self.output_console.insert(tk.END, message + "\n")
        self.output_console.see(tk.END)
        self.root.update_idletasks()

    def update_alias_file_label(self):
        lang = self.lang_var.get()
        self.current_alias_file.set(self.ALIAS_FILES[lang])

    def _load_saved_code(self):
        if os.path.exists(self.CODE_SAVE_FILE):
            with open(self.CODE_SAVE_FILE, "r", encoding="utf-8") as f:
                content = f.read()
            self.code_input.insert("1.0", content)
            self.log(f"Código carregado de {self.CODE_SAVE_FILE}.")

    def _auto_save(self):
        if self.auto_save_var.get():
            with open(self.CODE_SAVE_FILE, "w", encoding="utf-8") as f:
                f.write(self.code_input.get("1.0", tk.END))

    def _on_key_release(self, event=None):
        self._auto_save()
        if self.auto_run_var.get():
            if self.auto_run_job:
                self.root.after_cancel(self.auto_run_job)
            self.auto_run_job = self.root.after(self.AUTO_RUN_DELAY_MS, self.handle_convert)

    def load_aliases(self, file_name):
        aliases = {}
        path = os.path.join(self.BASE_DIR, file_name)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                for l in f:
                    if "=" in l and not l.strip().startswith("#"):
                        k,v = l.strip().split("=",1)
                        aliases[k.strip()] = v.strip()
        return aliases

    def apply_aliases_to_code(self, code, aliases):
        for k, v in aliases.items():
            if re.match(r"^\w+$", k):
                code = re.sub(r"\b"+re.escape(k)+r"\b", v, code)
            else:
                code = code.replace(k, v)
        return code

    def handle_convert(self):
        lang = self.lang_var.get()
        aliases = self.load_aliases(self.ALIAS_FILES[lang])
        code = self.code_input.get("1.0", tk.END)
        converted = self.apply_aliases_to_code(code, aliases)
        self.code_input.delete("1.0", tk.END)
        self.code_input.insert("1.0", converted)
        self.write_project_file(lang)

    def write_project_file(self, lang):
        folder = self.PROJECT_DIRS[lang]
        os.makedirs(folder, exist_ok=True)
        ext = self.FILE_EXTENSIONS[lang]
        filename = "index" + ext
        file_path = os.path.join(folder, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.code_input.get("1.0", tk.END))
        self.log(f"Arquivo salvo em {file_path}")

    def manage_aliases(self):
        alias_window = tk.Toplevel(self.root)
        alias_window.title("Gerenciar Arquivos de Alias")
        alias_window.geometry("600x500")

        tk.Label(alias_window, text="Edite os aliases (ALIAS = valor real):", font=("Arial",10,"bold")).pack(pady=5)
        alias_control_frame = tk.Frame(alias_window)
        alias_control_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(alias_control_frame, text="Arquivo Atual:").pack(side='left')
        self.alias_filename_var = tk.StringVar(alias_window, self.ALIAS_FILES[self.lang_var.get()])
        tk.OptionMenu(alias_control_frame, self.alias_filename_var, *self.ALIAS_FILES.values(),
                      command=self._load_alias_file_to_editor).pack(side='left', padx=10)
        tk.Button(alias_control_frame, text="Salvar", command=lambda:self._save_alias_file(self.alias_filename_var.get())).pack(side='right', padx=5)

        self.alias_editor = scrolledtext.ScrolledText(alias_window, wrap="word", height=20, font=("Consolas",10))
        self.alias_editor.pack(fill='both', expand=True, padx=10, pady=(0,10))

        self._load_alias_file_to_editor(self.alias_filename_var.get())

    def _load_alias_file_to_editor(self, filename):
        path = os.path.join(self.BASE_DIR, filename)
        self.alias_editor.delete("1.0", tk.END)
        if os.path.exists(path):
            with open(path,"r",encoding="utf-8") as f:
                self.alias_editor.insert("1.0", f.read())

    def _save_alias_file(self, filename):
        content = self.alias_editor.get("1.0", tk.END).strip()
        path = os.path.join(self.BASE_DIR, filename)
        with open(path,"w",encoding="utf-8") as f:
            f.write(content)
        self.log(f"Arquivo de alias '{filename}' salvo.")

    def start_server(self):
        if self.server_thread:
            self.log("Servidor já rodando.")
            return

        os.chdir(self.PROJECTS_BASE_DIR)
        handler = http.server.SimpleHTTPRequestHandler
        self.httpd = socketserver.TCPServer(("localhost", 8000), handler)

        def serve():
            self.log("Servidor localhost iniciado em http://localhost:8000/")
            self.httpd.serve_forever()

        self.server_thread = threading.Thread(target=serve, daemon=True)
        self.server_thread.start()

    def open_localhost(self):
        if not self.server_thread:
            self.start_server()
        lang = self.lang_var.get()
        filename = "index" + self.FILE_EXTENSIONS[lang]
        path = os.path.join(self.PROJECT_DIRS[lang], filename)
        if os.path.exists(path):
            webbrowser.open(f"http://localhost:8000/{os.path.basename(self.PROJECT_DIRS[lang])}/{filename}")
        else:
            self.log("Arquivo ainda não existe. Clique em Aplicar Aliases primeiro.")

if __name__=="__main__":
    root = tk.Tk()
    app = LangAliasApp(root)
    root.mainloop()
