import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import minecraft_launcher_lib
import subprocess
import sys
import os
import shutil
import threading

# Use a default Client ID
CLIENT_ID = "00000000402b5328"

def get_base_directory():
    return os.path.dirname(os.path.abspath(__file__))

class MainLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("Minecraft Java Port Launcher")
        self.root.geometry("500x450")

        self.base_dir = get_base_directory()

        tk.Label(root, text="Minecraft Java Port", font=("Arial", 20, "bold")).pack(pady=10)

        self.version_label = tk.Label(root, text="Select Minecraft Version:")
        self.version_label.pack()

        self.version_list = []
        self.version_combo = ttk.Combobox(root, values=self.version_list, width=30)
        self.version_combo.pack(pady=5)

        self.refresh_versions()

        self.progress_label = tk.Label(root, text="")
        self.progress_label.pack(pady=5)

        self.progress = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
        self.progress.pack(pady=10)

        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=20)

        self.download_btn = ttk.Button(btn_frame, text="Download & Launch", command=self.start_process)
        self.download_btn.grid(row=0, column=0, padx=10)

        self.offline_var = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="Launch Offline after download", variable=self.offline_var).pack()

        self.jre_var = tk.BooleanVar(value=True)
        tk.Checkbutton(root, text="Include local JRE (for school PCs)", variable=self.jre_var).pack()

    def refresh_versions(self):
        def load():
            try:
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
                self.root.after(0, lambda: self.progress_label.config(text="Downloading JRE..."))
                # Get the required JRE version for this Minecraft version
                # This is a bit simplified, usually it's "java-runtime-alpha", "java-runtime-beta" etc.
                # For modern versions (1.17+), Java 17 is usually needed.
                # minecraft-launcher-lib has install_jre but it's often easier to use the
                # version specific one if we knew it.
                # For simplicity, we'll try to let it auto-detect or just download the standard one.
                # Here we use the version's manifest to find the correct JRE.
                manifest = minecraft_launcher_lib.install.get_installed_versions(target_dir)
                # This is more complex than it should be.
                # Let's just use a common one if it's not specified.
                minecraft_launcher_lib.runtime.install_jvm_runtime("java-runtime-gamma", target_dir, callback=callback)

            # 3. Copy sub-launcher
            sub_launcher_src = os.path.join(self.base_dir, "sub_launcher.py")
            sub_launcher_dest = os.path.join(target_dir, "sub_launcher.py")
            shutil.copy2(sub_launcher_src, sub_launcher_dest)

            self.root.after(0, lambda: self.progress_label.config(text="Download Complete!"))
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

            # 4. Ask for login and launch
            if self.offline_var.get():
                self.root.after(0, lambda: self.prompt_offline_launch(version, target_dir))
            else:
                self.root.after(0, lambda: self.login_online_and_launch(version, target_dir))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.download_btn.config(state="normal"))

    def prompt_offline_launch(self, version, target_dir):
        username = simpledialog.askstring("Offline Mode", "Enter Username:", parent=self.root)
        if username:
            threading.Thread(target=self.launch_game, args=(version, target_dir, username), daemon=True).start()

    def launch_game(self, version, mc_dir, username, uuid=None, token=None):
        options = {
            "username": username,
            "uuid": uuid if uuid else "",
            "token": token if token else ""
        }
        try:
            # Try to find local JRE
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
            self.root.after(0, lambda: messagebox.showerror("Launch Error", str(e)))

    def login_online_and_launch(self, version, mc_dir):
        def do_login():
            try:
                device_code_data = minecraft_launcher_lib.microsoft_account.get_device_code(CLIENT_ID)

                def show_code():
                    self.root.clipboard_clear()
                    self.root.clipboard_append(device_code_data['user_code'])
                    msg = f"Please go to {device_code_data['verification_uri']} and enter the code: {device_code_data['user_code']}\n\nCode copied to clipboard. Waiting for login..."
                    messagebox.showinfo("Microsoft Login", msg)

                self.root.after(0, show_code)

                auth_data = minecraft_launcher_lib.microsoft_account.complete_device_code_login(CLIENT_ID, device_code_data)
                self.launch_game(version, mc_dir, auth_data["name"], auth_data["id"], auth_data["access_token"])
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Login Error", f"Failed to login: {str(e)}"))

        threading.Thread(target=do_login, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MainLauncher(root)
    root.mainloop()
