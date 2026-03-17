import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import minecraft_launcher_lib
import subprocess
import sys
import os
import shutil
import threading
import ms_auth

# Use a default Client ID
CLIENT_ID = "00000000402b5328"

def get_base_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

class MainLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Java Port - Launcher")
        self.root.geometry("600x550")
        self.root.configure(bg="#2c3e50")

        self.base_dir = get_base_directory()

        # Styles
        self.style = ttk.Style()
        self.style.theme_use("clam")

        self.style.configure("Main.TFrame", background="#2c3e50")
        self.style.configure("Title.TLabel", background="#2c3e50", foreground="#ecf0f1", font=("Segoe UI", 24, "bold"))
        self.style.configure("Standard.TLabel", background="#2c3e50", foreground="#bdc3c7", font=("Segoe UI", 10))
        self.style.configure("Action.TButton", font=("Segoe UI", 11, "bold"), padding=10)

        main_frame = ttk.Frame(root, style="Main.TFrame", padding=30)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(main_frame, text="MINECRAFT JAVA PORT", style="Title.TLabel").pack(pady=(0, 20))

        ttk.Label(main_frame, text="Select Game Version:", style="Standard.TLabel").pack(anchor="w")
        self.version_list = []
        self.version_combo = ttk.Combobox(main_frame, values=self.version_list, width=40, font=("Segoe UI", 10))
        self.version_combo.pack(pady=(5, 20), ipady=3)

        self.refresh_versions()

        self.progress_label = ttk.Label(main_frame, text="Ready", style="Standard.TLabel")
        self.progress_label.pack(pady=5)

        self.progress = ttk.Progressbar(main_frame, orient="horizontal", length=500, mode="determinate")
        self.progress.pack(pady=10)

        options_frame = ttk.Frame(main_frame, style="Main.TFrame")
        options_frame.pack(pady=20, fill="x")

        self.offline_var = tk.BooleanVar(value=True)
        self.offline_check = tk.Checkbutton(options_frame, text="Launch Offline after download", variable=self.offline_var,
                                           bg="#2c3e50", fg="#bdc3c7", selectcolor="#34495e", activebackground="#2c3e50", activeforeground="#ecf0f1",
                                           font=("Segoe UI", 10))
        self.offline_check.pack(anchor="w")

        self.jre_var = tk.BooleanVar(value=True)
        self.jre_check = tk.Checkbutton(options_frame, text="Include local JRE (recommended for school PCs)", variable=self.jre_var,
                                       bg="#2c3e50", fg="#bdc3c7", selectcolor="#34495e", activebackground="#2c3e50", activeforeground="#ecf0f1",
                                       font=("Segoe UI", 10))
        self.jre_check.pack(anchor="w")

        btn_frame = ttk.Frame(main_frame, style="Main.TFrame")
        btn_frame.pack(pady=30)

        self.download_btn = ttk.Button(btn_frame, text="DOWNLOAD & START", style="Action.TButton", command=self.start_process)
        self.download_btn.pack(ipadx=20)

    def refresh_versions(self):
        def load():
            try:
                self.root.after(0, lambda: self.progress_label.config(text="Fetching versions..."))
                versions = minecraft_launcher_lib.utils.get_version_list()
                v_list = [v["id"] for v in versions if v["type"] == "release"]
                self.root.after(0, lambda: self.update_version_combo(v_list))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to fetch versions: {e}"))

        threading.Thread(target=load, daemon=True).start()

    def update_version_combo(self, v_list):
        self.version_list = v_list
        self.version_combo['values'] = self.version_list
        if self.version_list:
            self.version_combo.set(self.version_list[0])
        self.progress_label.config(text="Ready")

    def start_process(self):
        version = self.version_combo.get()
        if not version:
            messagebox.showwarning("Warning", "Please select a version.")
            return

        self.download_btn.config(state="disabled")
        threading.Thread(target=self.process, args=(version,), daemon=True).start()

    def process(self, version):
        try:
            target_dir = os.path.join(self.base_dir, version)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            # 1. Download Minecraft files
            callback = {
                "setStatus": lambda text: self.root.after(0, lambda: self.progress_label.config(text=text)),
                "setProgress": lambda value: self.root.after(0, lambda: self.progress.config(value=value)),
                "setMax": lambda value: self.root.after(0, lambda: self.progress.config(maximum=value))
            }

            self.root.after(0, lambda: self.progress_label.config(text=f"Downloading {version}..."))
            minecraft_launcher_lib.install.install_minecraft_version(version, target_dir, callback=callback)

            # 2. Download JRE if requested
            if self.jre_var.get():
                self.root.after(0, lambda: self.progress_label.config(text="Checking required JRE..."))
                try:
                    version_data = minecraft_launcher_lib.install.get_version_data(version, target_dir)
                    java_runtime_name = version_data.get("javaVersion", {}).get("component", "java-runtime-gamma")
                except:
                    java_runtime_name = "java-runtime-gamma"

                self.root.after(0, lambda: self.progress_label.config(text=f"Downloading JRE ({java_runtime_name})..."))
                minecraft_launcher_lib.runtime.install_jvm_runtime(java_runtime_name, target_dir, callback=callback)

            # Copy ms_auth.py
            ms_auth_src = os.path.join(self.base_dir, "ms_auth.py")
            if os.path.exists(ms_auth_src):
                shutil.copy2(ms_auth_src, os.path.join(target_dir, "ms_auth.py"))

            # 3. Copy sub-launcher
            sub_launcher_src = os.path.join(self.base_dir, "sub_launcher.exe")
            if os.path.exists(sub_launcher_src):
                sub_launcher_dest = os.path.join(target_dir, "sub_launcher.exe")
            else:
                sub_launcher_src = os.path.join(self.base_dir, "sub_launcher.py")
                sub_launcher_dest = os.path.join(target_dir, "sub_launcher.py")

            if os.path.exists(sub_launcher_src):
                shutil.copy2(sub_launcher_src, sub_launcher_dest)

            self.root.after(0, lambda: self.progress_label.config(text="Complete!"))
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

            if self.offline_var.get():
                self.root.after(0, lambda: self.prompt_offline_launch(version, target_dir))
            else:
                self.root.after(0, lambda: self.login_online_and_launch(version, target_dir))

        except Exception as e:
            err_msg = str(e) if str(e) else f"Unknown error ({type(e).__name__})"
            self.root.after(0, lambda: messagebox.showerror("Error", err_msg))
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

    def prompt_offline_launch(self, version, target_dir):
        username = simpledialog.askstring("Offline Mode", "Enter Username:", parent=self.root)
        if username:
            threading.Thread(target=self.launch_game, args=(version, target_dir, username, "0", "0", "offline"), daemon=True).start()

    def launch_game(self, version, mc_dir, username, uuid="0", token="0", user_type="msa"):
        options = {
            "username": username,
            "uuid": uuid,
            "token": token,
            "user_type": user_type
        }
        try:
            runtime_dir = os.path.join(mc_dir, "runtime")
            java_path = None
            if os.path.exists(runtime_dir):
                for root_dir, dirs, files in os.walk(runtime_dir):
                    for file in files:
                        if file == "java.exe" or file == "java":
                            java_path = os.path.join(root_dir, file)
                            break
                    if java_path: break

            if java_path:
                options["executablePath"] = java_path

            command = minecraft_launcher_lib.command.get_minecraft_command(version, mc_dir, options)
            subprocess.Popen(command)
        except Exception as e:
            err_msg = str(e) if str(e) else f"Launch failed ({type(e).__name__})"
            self.root.after(0, lambda: messagebox.showerror("Launch Error", err_msg))

    def login_online_and_launch(self, version, mc_dir):
        def do_login():
            session = ms_auth.load_session(mc_dir)
            if session:
                try:
                    auth_data = ms_auth.refresh_session(CLIENT_ID, session["refresh_token"])
                    ms_auth.save_session(mc_dir, auth_data)
                    self.launch_game(version, mc_dir, auth_data["name"], auth_data["id"], auth_data["access_token"])
                    return
                except:
                    pass

            try:
                device_code_data = ms_auth.get_device_code(CLIENT_ID)
                def show_code():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(device_code_data['user_code'])
                    msg = f"Please go to {device_code_data['verification_uri']} and enter the code: {device_code_data['user_code']}\n\nCode copied to clipboard. Waiting for login..."
                    messagebox.showinfo("Microsoft Login", msg)

                self.root.after(0, show_code)
                auth_data = ms_auth.complete_device_code_login(CLIENT_ID, device_code_data)
                ms_auth.save_session(mc_dir, auth_data)
                self.launch_game(version, mc_dir, auth_data["name"], auth_data["id"], auth_data["access_token"])
            except Exception as e:
                err_msg = str(e) if str(e) else f"Login failed ({type(e).__name__})"
                self.root.after(0, lambda: messagebox.showerror("Login Error", f"Failed to login: {err_msg}"))

        threading.Thread(target=do_login, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MainLauncher(root)
    root.mainloop()
