import datetime
import hashlib
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk


DB_PATH = "sports.db"
TIME_SLOTS = [
    "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00",
    "14:00-15:00", "15:00-16:00", "16:00-17:00", "17:00-18:00",
    "19:00-20:00", "20:00-21:00",
]


def get_db_connection():
    return sqlite3.connect(DB_PATH)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    if cursor.fetchone():
        conn.close()
        return

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role INTEGER DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stadiums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            capacity INTEGER DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stadium_id INTEGER,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            status INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (stadium_id) REFERENCES stadiums(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS booking_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            user_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """
    )

    cursor.execute(
        "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
        ("admin", hash_password("admin123"), 1),
    )

    cursor.executemany(
        "INSERT INTO stadiums (name, description, capacity) VALUES (?, ?, ?)",
        [
            ("篮球馆A", "标准室内篮球场", 10),
            ("足球场B", "5人制人造草坪足球场", 20),
            ("羽毛球场C", "专业羽毛球训练馆", 8),
            ("游泳馆D", "标准恒温游泳池", 30),
        ],
    )

    conn.commit()
    conn.close()


def login(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, role FROM users WHERE username=? AND password=?",
        (username, hash_password(password)),
    )
    result = cursor.fetchone()
    conn.close()
    return result


def validate_booking_date(date_text):
    try:
        parsed = datetime.datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError:
        return False, "日期格式错误，请使用 YYYY-MM-DD"

    if parsed < datetime.date.today():
        return False, "不能预约过去的日期"

    return True, ""


def get_available_times(stadium_id, date):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT start_time, end_time FROM bookings WHERE stadium_id=? AND date=? AND status != 2",
        (stadium_id, date),
    )
    booked_times = cursor.fetchall()
    conn.close()

    booked_slots = {f"{start}-{end}" for start, end in booked_times}
    return [slot for slot in TIME_SLOTS if slot not in booked_slots]


def book_stadium(user_id, stadium_id, date, start_time, end_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO bookings (user_id, stadium_id, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
            (user_id, stadium_id, date, start_time, end_time),
        )
        booking_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO booking_history (booking_id, user_id, action) VALUES (?, ?, '创建预约')",
            (booking_id, user_id),
        )
        conn.commit()
        return booking_id
    except sqlite3.Error:
        conn.rollback()
        return None
    finally:
        conn.close()


def get_all_stadiums():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, capacity FROM stadiums")
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_stadium(name, description, capacity):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO stadiums (name, description, capacity) VALUES (?, ?, ?)",
            (name, description, capacity),
        )
        conn.commit()
    finally:
        conn.close()


def update_stadium(stadium_id, name, description, capacity):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE stadiums SET name=?, description=?, capacity=? WHERE id=?",
            (name, description, capacity, stadium_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_stadium(stadium_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM stadiums WHERE id=?", (stadium_id,))
        conn.commit()
    finally:
        conn.close()


class SportsManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("体育场预约管理系统")
        self.root.geometry("1200x750")

        self.current_user_id = None
        self.current_user_role = None
        self.current_username = None
        self.selected_booking_id = None

        self.setup_theme()
        self.create_main_interface()
        self.show_login()

    def setup_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Header.TLabel", font=("Segoe UI", 24, "bold"), foreground="#2c3e50")
        style.configure("SubHeader.TLabel", font=("Segoe UI", 16, "bold"), foreground="#3498db")

    def create_main_interface(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_frame = ttk.Frame(self.main_frame)
        title_frame.pack(fill="x", pady=(0, 20))
        ttk.Label(title_frame, text="体育场预约管理系统", style="Header.TLabel").pack(side="left")

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True)

        self.sidebar = ttk.Frame(self.content_frame, width=200)
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))

        self.main_content = ttk.Frame(self.content_frame)
        self.main_content.pack(side="right", fill="both", expand=True, padx=(0, 10))

        buttons = [
            ("主页", self.show_welcome),
            ("体育场", self.show_stadiums),
            ("预约", self.show_booking),
            ("我的预约", self.show_my_bookings),
        ]
        ttk.Label(self.sidebar, text="导航", style="SubHeader.TLabel").pack(pady=(15, 5))
        for text, command in buttons:
            ttk.Button(self.sidebar, text=text, command=command).pack(fill="x", pady=5, padx=10)

    def clear_main_content(self):
        for widget in self.main_content.winfo_children():
            widget.destroy()

    def show_login(self):
        self.clear_main_content()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill="both", expand=True, padx=50, pady=50)

        ttk.Label(frame, text="登录", style="Header.TLabel").pack(pady=(0, 20))
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()
        ttk.Label(frame, text="用户名").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.username_var).pack(fill="x", pady=(0, 15))
        ttk.Label(frame, text="密码").pack(anchor="w")
        ttk.Entry(frame, textvariable=self.password_var, show="*").pack(fill="x", pady=(0, 15))
        ttk.Button(frame, text="登录", command=self.on_login).pack()
        ttk.Button(frame, text="注册", command=self.show_register).pack(pady=8)

    def on_login(self):
        user = login(self.username_var.get().strip(), self.password_var.get())
        if not user:
            messagebox.showerror("登录失败", "用户名或密码错误")
            return
        self.current_user_id, self.current_user_role = user
        self.current_username = self.username_var.get().strip()
        self.show_welcome()

    def show_register(self):
        self.clear_main_content()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill="both", expand=True, padx=50, pady=50)
        ttk.Label(frame, text="用户注册", style="Header.TLabel").pack(pady=(0, 20))

        self.reg_username_var = tk.StringVar()
        self.reg_password_var = tk.StringVar()
        self.reg_confirm_var = tk.StringVar()

        for label, var, is_pwd in [
            ("用户名", self.reg_username_var, False),
            ("密码", self.reg_password_var, True),
            ("确认密码", self.reg_confirm_var, True),
        ]:
            ttk.Label(frame, text=label).pack(anchor="w")
            ttk.Entry(frame, textvariable=var, show="*" if is_pwd else "").pack(fill="x", pady=(0, 12))

        ttk.Button(frame, text="注册", command=self.register).pack()
        ttk.Button(frame, text="返回登录", command=self.show_login).pack(pady=8)

    def register(self):
        username = self.reg_username_var.get().strip()
        password = self.reg_password_var.get()
        confirm = self.reg_confirm_var.get()
        if not username or not password:
            messagebox.showerror("注册失败", "用户名和密码不能为空")
            return
        if password != confirm:
            messagebox.showerror("注册失败", "两次输入密码不一致")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, 0)",
                (username, hash_password(password)),
            )
            conn.commit()
            messagebox.showinfo("注册成功", "请登录")
            self.show_login()
        except sqlite3.IntegrityError:
            messagebox.showerror("注册失败", "用户名已存在")
        finally:
            conn.close()

    def show_welcome(self):
        self.clear_main_content()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill="both", expand=True, padx=50, pady=50)
        ttk.Label(frame, text="欢迎使用体育场预约管理系统", style="Header.TLabel").pack(pady=20)
        if self.current_username:
            ttk.Label(frame, text=f"你好，{self.current_username}", style="SubHeader.TLabel").pack(pady=10)

    def show_stadiums(self):
        self.clear_main_content()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill="both", expand=True, padx=50, pady=50)
        ttk.Label(frame, text="体育场列表", style="Header.TLabel").pack(pady=(0, 20))
        tree = ttk.Treeview(frame, columns=("name", "capacity", "description"), show="headings")
        tree.pack(fill="both", expand=True)
        tree.heading("name", text="体育场")
        tree.heading("capacity", text="容量")
        tree.heading("description", text="描述")
        for sid, name, desc, cap in get_all_stadiums():
            tree.insert("", "end", values=(name, cap, desc))

    def show_booking(self):
        self.clear_main_content()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill="both", expand=True, padx=50, pady=50)
        ttk.Label(frame, text="预约体育场", style="Header.TLabel").pack(pady=(0, 20))

        stadiums = get_all_stadiums()
        stadium_names = [s[1] for s in stadiums]

        self.stadium_var = tk.StringVar()
        self.date_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        self.time_var = tk.StringVar()

        ttk.Label(frame, text="选择体育场").pack(anchor="w")
        stadium_combobox = ttk.Combobox(frame, textvariable=self.stadium_var, values=stadium_names, state="readonly")
        stadium_combobox.pack(fill="x", pady=(0, 12))

        ttk.Label(frame, text="选择日期(YYYY-MM-DD)").pack(anchor="w")
        date_entry = ttk.Entry(frame, textvariable=self.date_var)
        date_entry.pack(fill="x", pady=(0, 8))

        ttk.Label(frame, text="选择时间段").pack(anchor="w")
        time_combobox = ttk.Combobox(frame, textvariable=self.time_var, state="readonly")
        time_combobox.pack(fill="x", pady=(0, 12))

        def refresh_slots(*_):
            stadium_name = self.stadium_var.get()
            stadium_id = next((s[0] for s in stadiums if s[1] == stadium_name), None)
            valid, msg = validate_booking_date(self.date_var.get().strip())
            if not stadium_id or not valid:
                time_combobox["values"] = []
                return
            time_combobox["values"] = get_available_times(stadium_id, self.date_var.get().strip())
            if msg:
                messagebox.showwarning("日期提醒", msg)

        stadium_combobox.bind("<<ComboboxSelected>>", refresh_slots)
        date_entry.bind("<FocusOut>", refresh_slots)

        ttk.Button(frame, text="刷新可用时段", command=refresh_slots).pack(pady=(0, 8))
        ttk.Button(frame, text="预约", command=self.make_booking).pack()

    def make_booking(self):
        if not self.current_user_id:
            messagebox.showerror("预约失败", "请先登录")
            return

        stadium_name = self.stadium_var.get().strip()
        date_text = self.date_var.get().strip()
        time_slot = self.time_var.get().strip()

        valid, msg = validate_booking_date(date_text)
        if not valid:
            messagebox.showerror("预约失败", msg)
            return
        if not stadium_name or not time_slot:
            messagebox.showerror("预约失败", "请完整选择体育场、日期和时间")
            return

        stadium_id = next((s[0] for s in get_all_stadiums() if s[1] == stadium_name), None)
        if not stadium_id:
            messagebox.showerror("预约失败", "体育场无效")
            return

        start, end = time_slot.split("-")
        booking_id = book_stadium(self.current_user_id, stadium_id, date_text, start, end)
        if booking_id:
            messagebox.showinfo("预约成功", f"预约ID: {booking_id}")
            self.show_my_bookings()
        else:
            messagebox.showerror("预约失败", "数据库写入失败")

    def show_my_bookings(self):
        if not self.current_user_id:
            messagebox.showerror("提示", "请先登录")
            self.show_login()
            return

        self.clear_main_content()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill="both", expand=True, padx=50, pady=50)
        ttk.Label(frame, text="我的预约", style="Header.TLabel").pack(pady=(0, 20))

        tree = ttk.Treeview(frame, columns=("id", "stadium", "date", "time", "status"), show="headings")
        tree.pack(fill="both", expand=True)
        tree.heading("id", text="ID")
        tree.heading("stadium", text="体育场")
        tree.heading("date", text="日期")
        tree.heading("time", text="时间段")
        tree.heading("status", text="状态")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.id, s.name, b.date, b.start_time, b.end_time, b.status
            FROM bookings b
            JOIN stadiums s ON b.stadium_id = s.id
            WHERE b.user_id = ?
            ORDER BY b.date, b.start_time
            """,
            (self.current_user_id,),
        )
        rows = cursor.fetchall()
        conn.close()

        mapping = {0: "待确认", 1: "已确认", 2: "已取消"}
        for bid, sname, date_text, start, end, status in rows:
            tree.insert("", "end", values=(bid, sname, date_text, f"{start}-{end}", mapping.get(status, "未知")))

        def on_select(_event):
            selected = tree.selection()
            self.selected_booking_id = int(tree.item(selected[0], "values")[0]) if selected else None

        tree.bind("<<TreeviewSelect>>", on_select)
        ttk.Button(frame, text="取消预约", command=self.cancel_booking).pack(pady=10)

    def cancel_booking(self):
        if not self.selected_booking_id:
            messagebox.showerror("取消失败", "请先选择一条预约")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT user_id, status FROM bookings WHERE id = ?",
            (self.selected_booking_id,),
        )
        row = cursor.fetchone()
        if not row:
            conn.close()
            messagebox.showerror("取消失败", "预约不存在")
            return

        user_id, status = row
        if user_id != self.current_user_id:
            conn.close()
            messagebox.showerror("取消失败", "只能取消自己的预约")
            return
        if status == 2:
            conn.close()
            messagebox.showwarning("提示", "该预约已取消")
            return

        cursor.execute("UPDATE bookings SET status = 2 WHERE id = ?", (self.selected_booking_id,))
        cursor.execute(
            "INSERT INTO booking_history (booking_id, user_id, action) VALUES (?, ?, '取消预约')",
            (self.selected_booking_id, self.current_user_id),
        )
        conn.commit()
        conn.close()

        messagebox.showinfo("取消成功", f"预约 {self.selected_booking_id} 已取消")
        self.selected_booking_id = None
        self.show_my_bookings()


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = SportsManagementApp(root)
    root.mainloop()
