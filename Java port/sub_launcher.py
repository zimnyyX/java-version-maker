import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import minecraft_launcher_lib
import subprocess
import sys
import os
import threading
import ms_auth

# Use a default Client ID
CLIENT_ID = "00000000402b5328"

def get_minecraft_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

def get_version_id():
    mc_dir = get_minecraft_directory()
    versions_dir = os.path.join(mc_dir, "versions")
    if not os.path.exists(versions_dir):
        return None

    versions = os.listdir(versions_dir)
    if not versions:
        return None

    return versions[0]

def launch_game(username, uuid="0", token="0", user_type="msa"):
    mc_dir = get_minecraft_directory()
    version = get_version_id()

    if not version:
        messagebox.showerror("Error", "Could not find any Minecraft version in the 'versions' folder.")
        return

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
        sys.exit(0)
    except Exception as e:
        messagebox.showerror("Launch Error", str(e))

def login_offline():
    username = simpledialog.askstring("Offline Mode", "Enter Username:")
    if username:
        launch_game(username, user_type="offline")

def login_online():
    def do_login():
        mc_dir = get_minecraft_directory()
        session = ms_auth.load_session(mc_dir)
        if session:
            try:
                auth_data = ms_auth.refresh_session(CLIENT_ID, session["refresh_token"])
                ms_auth.save_session(mc_dir, auth_data)
                root.after(0, lambda: launch_game(auth_data["name"], auth_data["id"], auth_data["access_token"]))
                return
            except:
                pass

        try:
            device_code_data = ms_auth.get_device_code(CLIENT_ID)
            def show_code():
                root.clipboard_clear()
                root.clipboard_append(device_code_data['user_code'])
                msg = f"Please go to {device_code_data['verification_uri']} and enter the code: {device_code_data['user_code']}\n\nCode copied to clipboard. Waiting for login..."
                messagebox.showinfo("Microsoft Login", msg)

            root.after(0, show_code)
            try:
                auth_data = ms_auth.complete_device_code_login(CLIENT_ID, device_code_data)
                ms_auth.save_session(mc_dir, auth_data)
                root.after(0, lambda: launch_game(auth_data["name"], auth_data["id"], auth_data["access_token"]))
            except Exception as e:
                err_msg = str(e) if str(e) else f"Login failed ({type(e).__name__})"
                root.after(0, lambda: messagebox.showerror("Login Error", f"Failed to login: {err_msg}"))

        except Exception as e:
            err_msg = str(e) if str(e) else f"Auth setup failed ({type(e).__name__})"
            root.after(0, lambda: messagebox.showerror("Error", err_msg))

    threading.Thread(target=do_login, daemon=True).start()

def main():
    global root
    root = tk.Tk()
    root.title("Minecraft Sub-Launcher")
    root.geometry("450x300")
    root.configure(bg="#2c3e50")

    version = get_version_id()

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Main.TFrame", background="#2c3e50")
    style.configure("Title.TLabel", background="#2c3e50", foreground="#ecf0f1", font=("Segoe UI", 18, "bold"))
    style.configure("Version.TLabel", background="#2c3e50", foreground="#bdc3c7", font=("Segoe UI", 11))
    style.configure("Action.TButton", font=("Segoe UI", 10, "bold"), padding=8)

    main_frame = ttk.Frame(root, style="Main.TFrame", padding=20)
    main_frame.pack(fill="both", expand=True)

    ttk.Label(main_frame, text="MINECRAFT SUB-LAUNCHER", style="Title.TLabel").pack(pady=(0, 10))
    ttk.Label(main_frame, text=f"Bound Version: {version if version else 'NOT FOUND'}", style="Version.TLabel").pack(pady=5)

    if not version:
        tk.Label(main_frame, text="Error: No version files found!", fg="#e74c3c", bg="#2c3e50", font=("Segoe UI", 10, "bold")).pack(pady=10)

    btn_frame = ttk.Frame(main_frame, style="Main.TFrame")
    btn_frame.pack(pady=30)

    ttk.Button(btn_frame, text="LAUNCH OFFLINE", style="Action.TButton", command=login_offline, width=20).grid(row=0, column=0, padx=10)
    ttk.Button(btn_frame, text="LAUNCH ONLINE", style="Action.TButton", command=login_online, width=20).grid(row=0, column=1, padx=10)

    root.mainloop()

if __name__ == "__main__":
    main()
