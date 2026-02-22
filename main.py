import calendar
import datetime
import hashlib
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk


# --- 数据库相关函数 ---
def get_db_connection():
    return sqlite3.connect('sports.db')


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
        '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role INTEGER DEFAULT 0
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS stadiums (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            capacity INTEGER DEFAULT 0
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            stadium_id INTEGER,
            date TEXT,
            start_time TEXT,
            end_time TEXT,
            status INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (stadium_id) REFERENCES stadiums(id)
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS booking_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            user_id INTEGER,
            action TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        '''
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
    user = cursor.fetchone()
    conn.close()
    return user


def get_available_times(stadium_id, date):
    all_times = [
        "08:00-09:00", "09:00-10:00", "10:00-11:00", "11:00-12:00",
        "14:00-15:00", "15:00-16:00", "16:00-17:00", "17:00-18:00",
        "19:00-20:00", "20:00-21:00",
    ]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT start_time, end_time FROM bookings WHERE stadium_id=? AND date=? AND status != 2",
        (stadium_id, date),
    )
    booked = {f"{start}-{end}" for start, end in cursor.fetchall()}
    conn.close()
    return [slot for slot in all_times if slot not in booked]


def book_stadium(user_id, stadium_id, date, start_time, end_time):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO bookings (user_id, stadium_id, date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, 1)
            """,
            (user_id, stadium_id, date, start_time, end_time),
        )
        booking_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO booking_history (booking_id, user_id, action) VALUES (?, ?, '创建预约(自动确认)')",
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
    cursor.execute("SELECT id, name, description, capacity FROM stadiums ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return rows


def add_stadium(name, description, capacity):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO stadiums (name, description, capacity) VALUES (?, ?, ?)",
        (name, description, capacity),
    )
    conn.commit()
    conn.close()


def delete_stadium(stadium_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stadiums WHERE id=?", (stadium_id,))
    conn.commit()
    conn.close()


class ModernButton(ttk.Button):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, style='Primary.TButton', **kwargs)


class ModernEntry(ttk.Entry):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, style='Modern.TEntry', **kwargs)


class DatePickerDialog(tk.Toplevel):
    def __init__(self, parent, date_var):
        super().__init__(parent)
        self.title("选择日期")
        self.geometry("320x300")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.date_var = date_var
        current = self._parse_date(date_var.get()) or datetime.date.today()
        self.year = current.year
        self.month = current.month

        header = ttk.Frame(self)
        header.pack(fill='x', padx=10, pady=8)
        ttk.Button(header, text='◀', command=self.prev_month).pack(side='left')
        self.title_label = ttk.Label(header, text='')
        self.title_label.pack(side='left', expand=True)
        ttk.Button(header, text='▶', command=self.next_month).pack(side='right')

        self.days_frame = ttk.Frame(self)
        self.days_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.render_calendar()

    @staticmethod
    def _parse_date(date_text):
        try:
            return datetime.datetime.strptime(date_text, "%Y-%m-%d").date()
        except ValueError:
            return None

    def prev_month(self):
        if self.month == 1:
            self.month = 12
            self.year -= 1
        else:
            self.month -= 1
        self.render_calendar()

    def next_month(self):
        if self.month == 12:
            self.month = 1
            self.year += 1
        else:
            self.month += 1
        self.render_calendar()

    def select_day(self, day):
        selected = datetime.date(self.year, self.month, day)
        if selected < datetime.date.today():
            messagebox.showwarning("无效日期", "不能选择过去日期")
            return
        self.date_var.set(selected.strftime("%Y-%m-%d"))
        self.destroy()

    def render_calendar(self):
        for w in self.days_frame.winfo_children():
            w.destroy()

        self.title_label.config(text=f"{self.year}-{self.month:02d}")

        week_names = ["一", "二", "三", "四", "五", "六", "日"]
        for idx, name in enumerate(week_names):
            ttk.Label(self.days_frame, text=name, width=4, anchor='center').grid(row=0, column=idx)

        month_grid = calendar.monthcalendar(self.year, self.month)
        for row_idx, week in enumerate(month_grid, start=1):
            for col_idx, day in enumerate(week):
                if day == 0:
                    ttk.Label(self.days_frame, text='').grid(row=row_idx, column=col_idx)
                    continue
                ttk.Button(
                    self.days_frame,
                    text=str(day),
                    width=4,
                    command=lambda d=day: self.select_day(d),
                ).grid(row=row_idx, column=col_idx, padx=1, pady=1)


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
        style.theme_use('clam')
        style.configure('TFrame', background='#f5f5f5')
        style.configure('TLabel', background='#f5f5f5', foreground='#333333')
        style.configure('Header.TLabel', font=('Segoe UI', 24, 'bold'), foreground='#2c3e50')
        style.configure('SubHeader.TLabel', font=('Segoe UI', 16, 'bold'), foreground='#3498db')
        style.configure('Primary.TButton', background='#4a90e2', foreground='white')
        style.configure('Modern.TEntry', fieldbackground='white')
        style.configure('Modern.TLabel', background='#f5f5f5', foreground='#333333')

    def create_main_interface(self):
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill='both', expand=True, padx=20, pady=20)
        ttk.Label(self.main_frame, text="体育场预约管理系统", style='Header.TLabel').pack(anchor='w', pady=(0, 20))

        self.create_menu()

        self.content = ttk.Frame(self.main_frame)
        self.content.pack(fill='both', expand=True)

    def create_menu(self):
        self.menu_bar = tk.Menu(self.root)
        user_menu = tk.Menu(self.menu_bar, tearoff=0)
        user_menu.add_command(label="登录", command=self.show_login)
        user_menu.add_command(label="注册", command=self.show_register)
        user_menu.add_command(label="注销", command=self.logout)
        self.menu_bar.add_cascade(label="用户", menu=user_menu)

        booking_menu = tk.Menu(self.menu_bar, tearoff=0)
        booking_menu.add_command(label="新建预约", command=self.show_booking)
        booking_menu.add_command(label="我的预约", command=self.show_my_bookings)
        self.menu_bar.add_cascade(label="预约", menu=booking_menu)

        admin_menu = tk.Menu(self.menu_bar, tearoff=0)
        admin_menu.add_command(label="体育场管理", command=self.show_stadium_management)
        self.menu_bar.add_cascade(label="管理", menu=admin_menu)

        self.root.config(menu=self.menu_bar)

    def _clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    def _validate_date(self, value):
        try:
            day = datetime.datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return False
        return day >= datetime.date.today()

    def _ensure_login(self):
        if self.current_user_id:
            return True
        messagebox.showerror("未登录", "请先登录")
        self.show_login()
        return False

    def _ensure_admin(self):
        if not self._ensure_login():
            return False
        if self.current_user_role != 1:
            messagebox.showerror("无权限", "仅管理员可使用管理功能")
            return False
        return True

    def show_login(self):
        self._clear_content()
        frame = ttk.Frame(self.content)
        frame.pack(fill='both', expand=True, padx=80, pady=80)

        ttk.Label(frame, text="登录", style='SubHeader.TLabel').pack(anchor='w', pady=(0, 15))
        self.username_var = tk.StringVar()
        self.password_var = tk.StringVar()

        ttk.Label(frame, text="用户名", style='Modern.TLabel').pack(anchor='w')
        ModernEntry(frame, textvariable=self.username_var).pack(fill='x', pady=(0, 10))
        ttk.Label(frame, text="密码", style='Modern.TLabel').pack(anchor='w')
        ttk.Entry(frame, textvariable=self.password_var, show='*').pack(fill='x', pady=(0, 15))

        ModernButton(frame, text="登录", command=self.login_action).pack(anchor='w')

    def login_action(self):
        user = login(self.username_var.get().strip(), self.password_var.get())
        if not user:
            messagebox.showerror("登录失败", "用户名或密码错误")
            return
        self.current_user_id, self.current_user_role = user
        self.current_username = self.username_var.get().strip()
        self.show_welcome()

    def show_register(self):
        self._clear_content()
        frame = ttk.Frame(self.content)
        frame.pack(fill='both', expand=True, padx=80, pady=80)

        self.reg_username = tk.StringVar()
        self.reg_pwd = tk.StringVar()
        self.reg_confirm = tk.StringVar()

        ttk.Label(frame, text="注册", style='SubHeader.TLabel').pack(anchor='w', pady=(0, 15))
        for label, var, masked in [
            ("用户名", self.reg_username, False),
            ("密码", self.reg_pwd, True),
            ("确认密码", self.reg_confirm, True),
        ]:
            ttk.Label(frame, text=label, style='Modern.TLabel').pack(anchor='w')
            ttk.Entry(frame, textvariable=var, show='*' if masked else '').pack(fill='x', pady=(0, 10))

        ModernButton(frame, text="注册", command=self.register_action).pack(anchor='w')

    def register_action(self):
        username = self.reg_username.get().strip()
        pwd = self.reg_pwd.get()
        if not username or not pwd:
            messagebox.showerror("注册失败", "用户名和密码不能为空")
            return
        if pwd != self.reg_confirm.get():
            messagebox.showerror("注册失败", "两次密码不一致")
            return

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, 0)",
                (username, hash_password(pwd)),
            )
            conn.commit()
            messagebox.showinfo("注册成功", "请登录")
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
        self._clear_content()
        frame = ttk.Frame(self.content)
        frame.pack(fill='both', expand=True, padx=80, pady=80)
        ttk.Label(frame, text=f"欢迎，{self.current_username or '游客'}", style='SubHeader.TLabel').pack(anchor='w')
        ModernButton(frame, text="新建预约", command=self.show_booking).pack(anchor='w', pady=(15, 8))
        ModernButton(frame, text="我的预约", command=self.show_my_bookings).pack(anchor='w', pady=8)
        ModernButton(frame, text="体育场管理", command=self.show_stadium_management).pack(anchor='w', pady=8)

    def show_booking(self):
        if not self._ensure_login():
            return

        self._clear_content()
        frame = ttk.Frame(self.content)
        frame.pack(fill='both', expand=True, padx=80, pady=50)

        stadiums = get_all_stadiums()
        stadium_names = [s[1] for s in stadiums]

        self.stadium_var = tk.StringVar()
        self.date_var = tk.StringVar(value=datetime.date.today().strftime("%Y-%m-%d"))
        self.time_var = tk.StringVar()

        ttk.Label(frame, text="预约体育场", style='SubHeader.TLabel').pack(anchor='w', pady=(0, 15))
        ttk.Label(frame, text="体育场", style='Modern.TLabel').pack(anchor='w')
        stadium_box = ttk.Combobox(frame, textvariable=self.stadium_var, values=stadium_names, state='readonly')
        stadium_box.pack(fill='x', pady=(0, 10))

        ttk.Label(frame, text="预约日期", style='Modern.TLabel').pack(anchor='w')
        date_wrap = ttk.Frame(frame)
        date_wrap.pack(fill='x', pady=(0, 10))
        ttk.Entry(date_wrap, textvariable=self.date_var, state='readonly').pack(side='left', fill='x', expand=True)
        ttk.Button(date_wrap, text='📅 选择日期', command=self.open_date_picker).pack(side='left', padx=(8, 0))

        ttk.Label(frame, text="时间段", style='Modern.TLabel').pack(anchor='w')
        time_box = ttk.Combobox(frame, textvariable=self.time_var, state='readonly')
        time_box.pack(fill='x', pady=(0, 15))

        def refresh_slots(_event=None):
            stadium_name = self.stadium_var.get()
            if not stadium_name or not self._validate_date(self.date_var.get()):
                time_box['values'] = []
                self.time_var.set('')
                return
            stadium_id = next((s[0] for s in stadiums if s[1] == stadium_name), None)
            time_box['values'] = get_available_times(stadium_id, self.date_var.get()) if stadium_id else []
            if self.time_var.get() not in time_box['values']:
                self.time_var.set('')

        self.refresh_time_slots = refresh_slots
        stadium_box.bind('<<ComboboxSelected>>', refresh_slots)
        ModernButton(frame, text="刷新可选时间", command=refresh_slots).pack(anchor='w', pady=(0, 8))
        ModernButton(frame, text="提交预约", command=self.make_booking).pack(anchor='w')

    def open_date_picker(self):
        dialog = DatePickerDialog(self.root, self.date_var)
        self.root.wait_window(dialog)
        if hasattr(self, 'refresh_time_slots'):
            self.refresh_time_slots()

    def make_booking(self):
        stadium_name = self.stadium_var.get().strip()
        date = self.date_var.get().strip()
        slot = self.time_var.get().strip()

        if not stadium_name or not date or not slot:
            messagebox.showerror("预约失败", "请完整填写信息")
            return
        if not self._validate_date(date):
            messagebox.showerror("预约失败", "请选择有效日期")
            return

        stadium_id = next((s[0] for s in get_all_stadiums() if s[1] == stadium_name), None)
        if not stadium_id:
            messagebox.showerror("预约失败", "体育场不存在")
            return

        start_time, end_time = slot.split('-')
        booking_id = book_stadium(self.current_user_id, stadium_id, date, start_time, end_time)
        if booking_id:
            messagebox.showinfo("预约成功", f"预约成功（已自动确认），ID: {booking_id}")
            self.show_my_bookings()
        else:
            messagebox.showerror("预约失败", "创建失败")

    def show_my_bookings(self):
        if not self._ensure_login():
            return

        self.selected_booking_id = None
        self._clear_content()
        frame = ttk.Frame(self.content)
        frame.pack(fill='both', expand=True, padx=50, pady=50)
        ttk.Label(frame, text="我的预约", style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))

        tree = ttk.Treeview(frame, columns=('id', 'stadium', 'date', 'time', 'status'), show='headings')
        tree.pack(fill='both', expand=True)
        for c, title, width in [
            ('id', 'ID', 70), ('stadium', '体育场', 200), ('date', '日期', 120),
            ('time', '时间段', 150), ('status', '状态', 100),
        ]:
            tree.heading(c, text=title)
            tree.column(c, width=width, anchor='center')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT b.id, s.name, b.date, b.start_time, b.end_time, b.status
            FROM bookings b JOIN stadiums s ON b.stadium_id=s.id
            WHERE b.user_id=? ORDER BY b.date DESC, b.start_time DESC
            """,
            (self.current_user_id,),
        )
        for b in cursor.fetchall():
            status = {0: '待确认', 1: '已确认', 2: '已取消'}.get(b[5], '未知')
            tree.insert('', 'end', values=(b[0], b[1], b[2], f"{b[3]}-{b[4]}", status))
        conn.close()

        tree.bind('<<TreeviewSelect>>', lambda _e: self._select_booking(tree))
        ModernButton(frame, text="取消预约", command=self.cancel_booking).pack(anchor='w', pady=10)

    def _select_booking(self, tree):
        selected = tree.selection()
        if selected:
            self.selected_booking_id = int(tree.item(selected[0], 'values')[0])

    def cancel_booking(self):
        if not self.selected_booking_id:
            messagebox.showerror("取消失败", "请选择预约")
            return
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE bookings SET status=2 WHERE id=? AND user_id=? AND status!=2",
            (self.selected_booking_id, self.current_user_id),
        )
        if cursor.rowcount:
            cursor.execute(
                "INSERT INTO booking_history (booking_id, user_id, action) VALUES (?, ?, '取消预约')",
                (self.selected_booking_id, self.current_user_id),
            )
            conn.commit()
            messagebox.showinfo("成功", "预约已取消")
        else:
            messagebox.showerror("失败", "预约不存在或已取消")
        conn.close()
        self.show_my_bookings()

    def show_stadium_management(self):
        if not self._ensure_admin():
            return

        self._clear_content()
        frame = ttk.Frame(self.content)
        frame.pack(fill='both', expand=True, padx=50, pady=50)
        ttk.Label(frame, text="体育场管理（管理员）", style='SubHeader.TLabel').pack(anchor='w', pady=(0, 10))

        self.stadium_tree = ttk.Treeview(frame, columns=('id', 'name', 'capacity', 'description'), show='headings')
        self.stadium_tree.pack(fill='both', expand=True)
        for c, title, width in [
            ('id', 'ID', 60), ('name', '体育场', 200), ('capacity', '容量', 100), ('description', '描述', 400)
        ]:
            self.stadium_tree.heading(c, text=title)
            self.stadium_tree.column(c, width=width, anchor='center')

        self.populate_stadiums()
        btns = ttk.Frame(frame)
        btns.pack(pady=10)
        ModernButton(btns, text='添加体育场', command=self.add_stadium_dialog).pack(side='left', padx=5)
        ModernButton(btns, text='删除体育场', command=self.delete_stadium_action).pack(side='left', padx=5)

    def populate_stadiums(self):
        for i in self.stadium_tree.get_children():
            self.stadium_tree.delete(i)
        for s in get_all_stadiums():
            self.stadium_tree.insert('', 'end', values=(s[0], s[1], s[3], s[2]))

    def add_stadium_dialog(self):
        if not self._ensure_admin():
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("添加体育场")
        dialog.geometry("380x260")
        dialog.transient(self.root)
        dialog.grab_set()

        name_var = tk.StringVar()
        cap_var = tk.StringVar()
        desc_var = tk.StringVar()

        for label, var in [("体育场名称", name_var), ("容量", cap_var), ("描述", desc_var)]:
            ttk.Label(dialog, text=label).pack(anchor='w', padx=12, pady=(10, 2))
            ttk.Entry(dialog, textvariable=var).pack(fill='x', padx=12)

        def submit():
            try:
                add_stadium(name_var.get().strip(), desc_var.get().strip(), int(cap_var.get()))
            except ValueError:
                messagebox.showerror("添加失败", "容量必须是数字")
                return
            except sqlite3.Error:
                messagebox.showerror("添加失败", "数据库写入失败")
                return
            dialog.destroy()
            self.populate_stadiums()
            messagebox.showinfo("成功", "体育场已添加")

        ModernButton(dialog, text='保存', command=submit).pack(pady=12)

    def delete_stadium_action(self):
        if not self._ensure_admin():
            return
        selected = self.stadium_tree.selection()
        if not selected:
            messagebox.showerror("删除失败", "请先选择体育场")
            return
        values = self.stadium_tree.item(selected[0], 'values')
        stadium_id, stadium_name = int(values[0]), values[1]
        if not messagebox.askyesno("确认", f"确定删除 {stadium_name} 吗？"):
            return
        delete_stadium(stadium_id)
        self.populate_stadiums()
        messagebox.showinfo("成功", "体育场已删除")


if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    app = SportsManagementApp(root)
    root.mainloop()
