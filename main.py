import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import sqlite3
import hashlib


# --- 数据库相关函数 ---
def get_db_connection():
    """获取数据库连接"""
    return sqlite3.connect('sports.db')


def hash_password(password):
    """简单哈希密码（实际应用中应使用更安全的方法如bcrypt）"""
    return hashlib.sha256(password.encode()).hexdigest()


def init_db():
    """初始化数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
    if cursor.fetchone():
        conn.close()
        return

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stadiums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            capacity INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
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
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS booking_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            user_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", ("admin", hash_password("admin123"), 1))

    example_stadiums = [
        ("篮球馆A", "标准室内篮球场", 10),
        ("足球场B", "5人制人造草坪足球场", 20),
        ("羽毛球场C", "专业羽毛球训练馆", 8),
        ("游泳馆D", "标准恒温游泳池", 30),
    ]
    cursor.executemany("INSERT INTO stadiums (name, description, capacity) VALUES (?, ?, ?)", example_stadiums)

    conn.commit()
    conn.close()


def login(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    hashed_password = hash_password(password)
    cursor.execute("SELECT id, role FROM users WHERE username=? AND password=?", (username, hashed_password))
    result = cursor.fetchone()
    conn.close()
    return result


def get_available_times(stadium_id, date):
    all_times = [
        "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00",
        "14:00-15:00", "15:00-16:00", "16:00-17:00", "17:00-18:00",
        "19:00-20:00", "20:00-21:00"
    ]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT start_time, end_time FROM bookings WHERE stadium_id=? AND date=? AND status != 2", (stadium_id, date))
    booked_times = cursor.fetchall()
    conn.close()

    booked_slots = [f"{b[0]}-{b[1]}" for b in booked_times]
    return [t for t in all_times if t not in booked_slots]


def book_stadium(user_id, stadium_id, date, start_time, end_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO bookings (user_id, stadium_id, date, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
            (user_id, stadium_id, date, start_time, end_time),
        )
        booking_id = cursor.lastrowid
        cursor.execute("INSERT INTO booking_history (booking_id, user_id, action) VALUES (?, ?, '创建预约')", (booking_id, user_id))
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
    stadiums = cursor.fetchall()
    conn.close()
    return stadiums


def add_stadium(name, description, capacity):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO stadiums (name, description, capacity) VALUES (?, ?, ?)", (name, description, capacity))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
    finally:
        conn.close()


def update_stadium(stadium_id, name, description, capacity):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE stadiums SET name=?, description=?, capacity=? WHERE id=?", (name, description, capacity, stadium_id))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
    finally:
        conn.close()


def delete_stadium(stadium_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM stadiums WHERE id=?", (stadium_id,))
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
    finally:
        conn.close()


class ModernButton(ttk.Button):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, style='Primary.TButton', **kwargs)


class ModernEntry(ttk.Entry):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, style='Modern.TEntry', **kwargs)


class SportsManagementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("体育场预约管理系统")
        self.root.geometry("1200x750")
        self.root.minsize(1000, 650)
        self.root.configure(bg='#f5f5f5')

        self.current_user_id = None
        self.current_user_role = None
        self.current_username = None
        self.selected_booking_id = None

        self.setup_theme()
        self.create_main_interface()
        self.show_login()

    def setup_theme(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TFrame', background='#f5f5f5')
        style.configure('TLabel', background='#f5f5f5', foreground='#333333')
        style.configure('TButton', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 24, 'bold'), foreground='#2c3e50')
        style.configure('SubHeader.TLabel', font=('Segoe UI', 16, 'bold'), foreground='#3498db')
        style.configure('Primary.TButton', background='#4a90e2', foreground='white', font=('Segoe UI', 10, 'bold'), borderwidth=0)
        style.map('Primary.TButton', background=[('active', '#3a7bc8'), ('pressed', '#2a6496')], foreground=[('active', 'white')])
        style.configure('Modern.TEntry', fieldbackground='white', bordercolor='#cccccc', lightcolor='#cccccc', darkcolor='#cccccc', relief='flat')
        style.configure('Modern.TLabel', background='#f5f5f5', foreground='#333333', font=('Segoe UI', 10))

    def create_main_interface(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        self.title_frame = ttk.Frame(self.main_frame)
        self.title_frame.pack(fill='x', pady=(0, 20))
        ttk.Label(self.title_frame, text="体育场预约管理系统", style='Header.TLabel').pack(side='left')

        self.create_menu()

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill='both', expand=True)

        self.sidebar = ttk.Frame(self.content_frame, width=200)
        self.sidebar.pack(side='left', fill='y', padx=(0, 10))

        self.main_content = ttk.Frame(self.content_frame)
        self.main_content.pack(side='right', fill='both', expand=True, padx=(0, 10))

        self.create_sidebar()

    def create_menu(self):
        self.menu_bar = tk.Menu(self.root)
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="退出", command=self.root.quit)
        self.menu_bar.add_cascade(label="文件", menu=file_menu)

        user_menu = tk.Menu(self.menu_bar, tearoff=0)
        user_menu.add_command(label="登录", command=self.show_login)
        user_menu.add_command(label="注册", command=self.show_register)
        user_menu.add_separator()
        user_menu.add_command(label="注销", command=self.logout)
        self.menu_bar.add_cascade(label="用户", menu=user_menu)

        booking_menu = tk.Menu(self.menu_bar, tearoff=0)
        booking_menu.add_command(label="新建预约", command=self.show_booking)
        booking_menu.add_command(label="我的预约", command=self.show_my_bookings)
        self.menu_bar.add_cascade(label="预约", menu=booking_menu)

        self.root.config(menu=self.menu_bar)

    def create_sidebar(self):
        ttk.Label(self.sidebar, text="导航", style='SubHeader.TLabel').pack(pady=(15, 5))
        for text, command in [
            ("主页", self.show_welcome),
            ("体育场", self.show_stadiums),
            ("预约", self.show_booking),
            ("我的预约", self.show_my_bookings),
        ]:
            ModernButton(self.sidebar, text=text, command=command).pack(fill='x', pady=5, padx=10)

    def show_login(self):
        for widget in self.main_content.winfo_children():
            widget.destroy()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill='both', expand=True, padx=50, pady=50)
        ttk.Label(frame, text="登录", style='Header.TLabel').pack(pady=(0, 20))

        ttk.Label(frame, text="用户名:", style='Modern.TLabel').pack(anchor='w', pady=(0, 5))
        self.username_var = tk.StringVar()
        ModernEntry(frame, textvariable=self.username_var).pack(fill='x', pady=(0, 20))

        ttk.Label(frame, text="密码:", style='Modern.TLabel').pack(anchor='w', pady=(0, 5))
        self.password_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.password_var, show='*').pack(fill='x', pady=(0, 20))

        ModernButton(frame, text="登录", command=self.login).pack(pady=10)
        ttk.Button(frame, text="去注册", command=self.show_register).pack(pady=10)

    def login(self):
        user = login(self.username_var.get(), self.password_var.get())
        if user:
            self.current_user_id, self.current_user_role = user
            self.current_username = self.username_var.get()
            self.show_welcome()
        else:
            messagebox.showerror("登录失败", "用户名或密码错误！")

    def show_register(self):
        for widget in self.main_content.winfo_children():
            widget.destroy()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill='both', expand=True, padx=50, pady=50)
        ttk.Label(frame, text="用户注册", style='Header.TLabel').pack(pady=(0, 20))

        self.reg_username_var = tk.StringVar()
        self.reg_password_var = tk.StringVar()
        self.reg_confirm_var = tk.StringVar()

        ttk.Label(frame, text="用户名:", style='Modern.TLabel').pack(anchor='w', pady=(0, 5))
        ModernEntry(frame, textvariable=self.reg_username_var).pack(fill='x', pady=(0, 20))
        ttk.Label(frame, text="密码:", style='Modern.TLabel').pack(anchor='w', pady=(0, 5))
        ttk.Entry(frame, textvariable=self.reg_password_var, show='*').pack(fill='x', pady=(0, 20))
        ttk.Label(frame, text="确认密码:", style='Modern.TLabel').pack(anchor='w', pady=(0, 5))
        ttk.Entry(frame, textvariable=self.reg_confirm_var, show='*').pack(fill='x', pady=(0, 20))

        ModernButton(frame, text="注册", command=self.register).pack(pady=10)
        ttk.Button(frame, text="返回登录", command=self.show_login).pack(pady=10)

    def register(self):
        username = self.reg_username_var.get().strip()
        password = self.reg_password_var.get()
        confirm = self.reg_confirm_var.get()
        if not username or not password:
            messagebox.showerror("注册失败", "用户名和密码不能为空！")
            return
        if password != confirm:
            messagebox.showerror("注册失败", "两次输入的密码不一致！")
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, hash_password(password), 0))
            conn.commit()
            messagebox.showinfo("注册成功", "注册成功！请登录。")
            self.show_login()
        except sqlite3.IntegrityError:
            messagebox.showerror("注册失败", "用户名已存在")
        finally:
            conn.close()

    def logout(self):
        self.current_user_id = None
        self.current_user_role = None
        self.current_username = None
        self.selected_booking_id = None
        self.show_login()

    def show_welcome(self):
        for widget in self.main_content.winfo_children():
            widget.destroy()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill='both', expand=True, padx=50, pady=50)
        ttk.Label(frame, text="欢迎使用体育场预约管理系统", style='Header.TLabel').pack(pady=20)
        if self.current_username:
            ttk.Label(frame, text=f"你好，{self.current_username}！", style='SubHeader.TLabel').pack(pady=10)

    def _validate_date(self, value):
        try:
            datetime.datetime.strptime(value, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def show_booking(self):
        if not self.current_user_id:
            messagebox.showerror("未登录", "请先登录后再预约")
            self.show_login()
            return

        for widget in self.main_content.winfo_children():
            widget.destroy()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill='both', expand=True, padx=50, pady=50)
        ttk.Label(frame, text="预约体育场", style='Header.TLabel').pack(pady=(0, 20))

        stadiums = get_all_stadiums()
        stadium_names = [s[1] for s in stadiums]

        ttk.Label(frame, text="选择体育场:", style='Modern.TLabel').pack(anchor='w', pady=(0, 5))
        self.stadium_var = tk.StringVar()
        stadium_combobox = ttk.Combobox(frame, textvariable=self.stadium_var, values=stadium_names, state='readonly')
        stadium_combobox.pack(fill='x', pady=(0, 20))

        ttk.Label(frame, text="选择日期(YYYY-MM-DD):", style='Modern.TLabel').pack(anchor='w', pady=(0, 5))
        self.date_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        date_entry = ModernEntry(frame, textvariable=self.date_var)
        date_entry.pack(fill='x', pady=(0, 20))

        ttk.Label(frame, text="选择时间段:", style='Modern.TLabel').pack(anchor='w', pady=(0, 5))
        self.time_var = tk.StringVar()
        time_combobox = ttk.Combobox(frame, textvariable=self.time_var, state='readonly')
        time_combobox.pack(fill='x', pady=(0, 20))

        def update_time_slots(_event=None):
            stadium_name = self.stadium_var.get()
            date_value = self.date_var.get().strip()
            if not stadium_name or not self._validate_date(date_value):
                time_combobox['values'] = []
                self.time_var.set('')
                return
            stadium_id = next((s[0] for s in stadiums if s[1] == stadium_name), None)
            if stadium_id:
                time_combobox['values'] = get_available_times(stadium_id, date_value)
                self.time_var.set('')

        stadium_combobox.bind('<<ComboboxSelected>>', update_time_slots)
        date_entry.bind('<FocusOut>', update_time_slots)
        date_entry.bind('<Return>', update_time_slots)

        ModernButton(frame, text="预约", command=self.make_booking).pack(pady=10)

    def make_booking(self):
        if not self.current_user_id:
            messagebox.showerror("预约失败", "请先登录")
            return

        stadium_name = self.stadium_var.get().strip()
        date = self.date_var.get().strip()
        time_slot = self.time_var.get().strip()

        if not stadium_name or not date or not time_slot:
            messagebox.showerror("预约失败", "请填写所有字段")
            return
        if not self._validate_date(date):
            messagebox.showerror("预约失败", "日期格式错误，请输入 YYYY-MM-DD")
            return

        stadiums = get_all_stadiums()
        stadium_id = next((s[0] for s in stadiums if s[1] == stadium_name), None)
        if not stadium_id:
            messagebox.showerror("预约失败", "无效的体育场")
            return

        start_time, end_time = time_slot.split('-')
        booking_id = book_stadium(self.current_user_id, stadium_id, date, start_time, end_time)
        if booking_id:
            messagebox.showinfo("预约成功", f"预约已创建，ID: {booking_id}")
            self.show_my_bookings()
        else:
            messagebox.showerror("预约失败", "无法创建预约")

    def show_my_bookings(self):
        if not self.current_user_id:
            messagebox.showerror("未登录", "请先登录")
            self.show_login()
            return

        self.selected_booking_id = None
        for widget in self.main_content.winfo_children():
            widget.destroy()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill='both', expand=True, padx=50, pady=50)
        ttk.Label(frame, text="我的预约", style='Header.TLabel').pack(pady=(0, 20))

        columns = ('id', 'stadium', 'date', 'time', 'status')
        tree = ttk.Treeview(frame, columns=columns, show='headings')
        tree.pack(fill='both', expand=True)
        tree.heading('id', text='ID')
        tree.heading('stadium', text='体育场')
        tree.heading('date', text='日期')
        tree.heading('time', text='时间段')
        tree.heading('status', text='状态')
        tree.column('id', width=80, anchor='center')

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
        bookings = cursor.fetchall()
        conn.close()

        for booking in bookings:
            status_text = {0: "待确认", 1: "已确认", 2: "已取消"}[booking[5]]
            tree.insert('', 'end', values=(booking[0], booking[1], booking[2], f"{booking[3]}-{booking[4]}", status_text))

        def on_select(_event):
            selected_item = tree.selection()
            if selected_item:
                self.selected_booking_id = int(tree.item(selected_item[0], 'values')[0])

        tree.bind('<<TreeviewSelect>>', on_select)
        ModernButton(frame, text="取消预约", command=self.cancel_booking).pack(pady=10)

    def cancel_booking(self):
        if not self.selected_booking_id:
            messagebox.showerror("取消失败", "请选择要取消的预约")
            return
        if not self.current_user_id:
            messagebox.showerror("取消失败", "请先登录")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE bookings SET status = 2 WHERE id = ? AND user_id = ? AND status != 2",
            (self.selected_booking_id, self.current_user_id),
        )
        changed = cursor.rowcount
        if changed:
            cursor.execute("INSERT INTO booking_history (booking_id, user_id, action) VALUES (?, ?, '取消预约')", (self.selected_booking_id, self.current_user_id))
            conn.commit()
            messagebox.showinfo("取消成功", "预约已取消")
        else:
            messagebox.showerror("取消失败", "该预约不存在或已取消")
        conn.close()
        self.show_my_bookings()

    def show_stadiums(self):
        for widget in self.main_content.winfo_children():
            widget.destroy()
        frame = ttk.Frame(self.main_content)
        frame.pack(fill='both', expand=True, padx=50, pady=50)
        ttk.Label(frame, text="体育场列表", style='Header.TLabel').pack(pady=(0, 20))

        tree = ttk.Treeview(frame, columns=('name', 'capacity', 'description'), show='headings')
        tree.pack(fill='both', expand=True)
        tree.heading('name', text='体育场')
        tree.heading('capacity', text='容量')
        tree.heading('description', text='描述')
        for stadium in get_all_stadiums():
            tree.insert('', 'end', values=(stadium[1], stadium[3], stadium[2]))


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = SportsManagementApp(root)
    root.mainloop()
