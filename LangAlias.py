#!/usr/bin/env python3
import tkinter as tk
from tkinter import scrolledtext, filedialog
import os
import subprocess
import re
import sys
import threading

class LangAliasApp:
    def __init__(self, root):
        self.root = root
        root.title("LangAlias IDE (Tkinter)")
        root.geometry("1125x750")

        self.PROJECTS_BASE_DIR = "Projects"
        self.CODE_SAVE_FILE = "codigo.txt"
        self.PROJECT_DIRS = {
            "Java": os.path.join(self.PROJECTS_BASE_DIR, "JavaProject"),
            "C++": os.path.join(self.PROJECTS_BASE_DIR, "CppProject")
        }
        self.FILE_EXTENSIONS = {"Java": ".java", "C++": ".cpp"}
        self.ALIAS_FILES = {"Java": "alias_java.txt", "C++": "alias_cpp.txt"}

        self.COMPILE_COMMANDS = {
            "Java": lambda f: ["javac", f],
            "C++": lambda f: ["g++", f, "-o", os.path.splitext(f)[0]]
        }
        self.RUN_COMMANDS = {
            "Java": lambda f: ["java", os.path.splitext(f)[0]],
            "C++": lambda f: [os.path.join(".", os.path.splitext(f)[0])]
        }

        os.makedirs(self.PROJECTS_BASE_DIR, exist_ok=True)
        for d in self.PROJECT_DIRS.values():
            os.makedirs(d, exist_ok=True)

        self.lang_var = tk.StringVar(root, "Java")
        self.current_alias_file = tk.StringVar(root, self.ALIAS_FILES["Java"])
        self.auto_save_var = tk.BooleanVar(root, True)
        self.auto_run_var = tk.BooleanVar(root, False)
        self.auto_run_job = None
        self.AUTO_RUN_DELAY_MS = 1500
        control_frame = tk.Frame(root)
        control_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(control_frame, text="Linguagem:").pack(side='left', padx=5)
        for lang in ["Java", "C++"]:
            tk.Radiobutton(control_frame, text=lang, variable=self.lang_var,
                           value=lang, command=self.update_alias_file_label).pack(side='left', padx=5)

        tk.Checkbutton(control_frame, text="💾 Auto Save", variable=self.auto_save_var).pack(side='left', padx=10)
        tk.Checkbutton(control_frame, text="▶️ Auto Run", variable=self.auto_run_var).pack(side='left', padx=5)

        tk.Button(control_frame, text="▶️ Executar Código (Run)", command=self.start_threaded_task).pack(side='left', padx=15, fill='x', expand=True)
        tk.Button(control_frame, text="🔄 Converter Aliases (Reverse)", command=self.handle_convert).pack(side='left', padx=15, fill='x', expand=True)
        tk.Button(control_frame, text="⚙️ Gerenciar Aliases", command=self.manage_aliases).pack(side='left', padx=15, fill='x', expand=True)

        tk.Frame(root, height=1, bg='gray').pack(fill='x', padx=10)

        main_frame = tk.Frame(root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Label(main_frame, text="Código de Entrada / Saída da Compilação e Execução").pack(fill='x')

        self.code_input = scrolledtext.ScrolledText(main_frame, wrap="word", height=20, font=("Consolas", 12))
        self.code_input.pack(fill='both', expand=True, pady=(5, 10))

        tk.Label(main_frame, text="Output / Logs").pack(fill='x')

        self.output_console = scrolledtext.ScrolledText(main_frame, wrap="word", height=10, font=("Consolas", 10), bg="#000000", fg="#FFFFFF", insertbackground="#FFFFFF")
        self.output_console.pack(fill='x')
        self._load_saved_code()
        self.code_input.bind("<KeyRelease>", self._on_key_release)

        self.log("Sistema LangAlias IDE iniciado. Selecione a linguagem e comece a programar.")


    def log(self, message):
        self.output_console.insert(tk.END, message + "\n")
        self.output_console.see(tk.END)
        self.root.update_idletasks()

    def update_alias_file_label(self):
        lang = self.lang_var.get()
        self.current_alias_file.set(self.ALIAS_FILES[lang])

    def start_threaded_task(self):
        code = self.code_input.get("1.0", tk.END).strip()
        if not code:
            self.log("ERRO: O campo de código está vazio.")
            return

        thread = threading.Thread(target=self.handle_run, args=(code,))
        thread.daemon = True
        thread.start()
        self.log("\n--- Thread iniciada para Execução de Código ---")

    def _load_saved_code(self):
        if os.path.exists(self.CODE_SAVE_FILE):
            try:
                with open(self.CODE_SAVE_FILE, "r", encoding="utf-8") as f:
                    content = f.read()
                self.code_input.insert("1.0", content)
                self.log(f"Código carregado de {self.CODE_SAVE_FILE}.")
            except Exception as e:
                self.log(f"ERRO ao carregar {self.CODE_SAVE_FILE}: {e}")

    def _auto_save(self):
        if self.auto_save_var.get():
            code = self.code_input.get("1.0", tk.END).strip()
            if code:
                try:
                    with open(self.CODE_SAVE_FILE, "w", encoding="utf-8") as f:
                        f.write(code)
                except Exception as e:
                    self.log(f"ERRO ao salvar código automaticamente: {e}")

    def _on_key_release(self, event=None):
        self._auto_save()

        if self.auto_run_var.get():
            if self.auto_run_job:
                self.root.after_cancel(self.auto_run_job)

            self.auto_run_job = self.root.after(self.AUTO_RUN_DELAY_MS, self.start_threaded_task)

    def load_aliases(self, file_name):
        a = {}
        alias_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)
        if os.path.exists(alias_path):
            with open(alias_path, "r", encoding="utf-8") as f:
                for l in f:
                    if not l.strip().startswith("[") and "=" in l and not l.strip().startswith("#"):
                        k, v = l.strip().split("=", 1)
                        a[k.strip()] = v.strip()
        return a

    def apply_aliases_to_original(self, code, aliases):
            pattern = r'("[^"\\]*(?:\\.[^"\\]*)*")|(\b\w+\b)'
            def replace_func(match):
                if match.group(1):
                    return match.group(1)
                word = match.group(2)
                return aliases.get(word, word)
            return re.sub(pattern, replace_func, code)

    def apply_aliases_to_alias_code(self, code, aliases):
        aliases_reverso = {v: k for k, v in aliases.items()}
        sorted_values = sorted(aliases_reverso.keys(), key=len, reverse=True)

        converted_code = code
        for value_original in sorted_values:
            key_alias = aliases_reverso[value_original]
            escaped_value = re.escape(value_original)

            if re.match(r'^\w+$', value_original):
                converted_code = re.sub(r'\b' + escaped_value + r'\b', key_alias, converted_code)
            else:
                converted_code = re.sub(escaped_value, key_alias, converted_code)

        return converted_code

    def clear_project(self, lang, folder):
        for f in os.listdir(folder):
            if f.endswith(self.FILE_EXTENSIONS[lang]) or \
               (lang == "Java" and f.endswith(".class")) or \
               (lang == "C++" and f.startswith("Main") and not f.endswith(self.FILE_EXTENSIONS[lang])):
                os.remove(os.path.join(folder, f))

    def handle_run(self, code):
        lang = self.lang_var.get()
        alias_file = self.ALIAS_FILES[lang]

        aliases = self.load_aliases(alias_file)
        code_to_compile = self.apply_aliases_to_original(code, aliases)

        output_file_name = "Main" + self.FILE_EXTENSIONS[lang]
        current_dir = self.PROJECT_DIRS[lang]

        try:
            os.makedirs(current_dir, exist_ok=True)
            self.clear_project(lang, current_dir)

            filePath = os.path.join(current_dir, output_file_name)
            with open(filePath, "w", encoding="utf-8") as f:
                f.write(code_to_compile)

            self.log(f"Arquivo temporário ({output_file_name}) gerado em: {current_dir}")

            self.log("Iniciando COMPILAÇÃO...")
            compile_proc = subprocess.run(
                self.COMPILE_COMMANDS[lang](output_file_name),
                capture_output=True, text=True, cwd=current_dir, timeout=10
            )

            if compile_proc.returncode != 0:
                self.log("ERRO DE COMPILAÇÃO:")
                self.log(compile_proc.stderr)
                return

            self.log("Compilação bem-sucedida. Iniciando EXECUÇÃO...")
            exec_proc = subprocess.run(
                self.RUN_COMMANDS[lang](output_file_name),
                capture_output=True, text=True, cwd=current_dir, timeout=10
            )

            output = exec_proc.stdout + exec_proc.stderr
            self.log("RESULTADO DA EXECUÇÃO:")
            self.log(output)

        except FileNotFoundError:
            self.log(f"ERRO: Compilador/Runtime de {lang} não encontrado. Verifique seu PATH.")
        except subprocess.TimeoutExpired:
            self.log("ERRO: Execução do código excedeu o limite de tempo (10 segundos).")
        except Exception as e:
            self.log(f"ERRO INESPERADO durante a execução: {e}")

    def handle_convert(self):
        lang = self.lang_var.get()
        alias_file = self.ALIAS_FILES[lang]
        code_original = self.code_input.get("1.0", tk.END).strip()

        if not code_original:
            self.log("ERRO: O campo de código está vazio para conversão.")
            return

        self.log(f"Iniciando conversão de código {lang} para aliases...")

        try:
            aliases_map = self.load_aliases(alias_file)
            converted_code = self.apply_aliases_to_alias_code(code_original, aliases_map)

            self.code_input.delete("1.0", tk.END)
            self.code_input.insert("1.0", converted_code)

            self.log("SUCESSO: Código convertido para aliases e inserido no editor de código.")

        except Exception as e:
            self.log(f"ERRO ao converter código: {e}")

    def manage_aliases(self):
        alias_window = tk.Toplevel(self.root)
        alias_window.title("Gerenciar Arquivos de Alias")
        alias_window.geometry("600x500")

        tk.Label(alias_window, text="Edite os aliases abaixo (ALIAS = valor original do código):", font=("Arial", 10, "bold")).pack(pady=5)

        alias_control_frame = tk.Frame(alias_window)
        alias_control_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(alias_control_frame, text="Arquivo Atual:").pack(side='left')

        alias_file_options = self.ALIAS_FILES.values()

        self.alias_filename_var = tk.StringVar(alias_window, self.ALIAS_FILES[self.lang_var.get()])
        tk.OptionMenu(alias_control_frame, self.alias_filename_var, *alias_file_options, command=self._load_alias_file_to_editor).pack(side='left', padx=10)

        tk.Button(alias_control_frame, text="Salvar", command=lambda: self._save_alias_file(self.alias_filename_var.get())).pack(side='right', padx=5)

        self.alias_editor = scrolledtext.ScrolledText(alias_window, wrap="word", height=20, font=("Consolas", 10))
        self.alias_editor.pack(fill='both', expand=True, padx=10, pady=(0, 10))

        self._load_alias_file_to_editor(self.alias_filename_var.get())

    def _load_alias_file_to_editor(self, filename):
        alias_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

        self.alias_editor.delete("1.0", tk.END)
        if os.path.exists(alias_path):
            with open(alias_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.alias_editor.insert("1.0", content)

    def _save_alias_file(self, filename):
        content = self.alias_editor.get("1.0", tk.END).strip()
        alias_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)

        try:
            with open(alias_path, "w", encoding="utf-8") as f:
                f.write(content)
            self.log(f"SUCESSO: Arquivo de alias '{filename}' salvo.")
        except Exception as e:
            self.log(f"ERRO ao salvar o arquivo de alias '{filename}': {e}")

# --- Inicialização da Aplicação ---
if __name__ == "__main__":
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    root = tk.Tk()
    app = LangAliasApp(root)
    root.mainloop()
