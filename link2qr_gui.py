#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
代理链接 → 二维码生成器  v2.0
支持：TUIC / VLESS / VMess / Trojan / SS / Hysteria2
改进：右键菜单、全局快捷键、点击放大、批量保存、Toast 通知、拖拽粘贴
"""

import sys, threading, urllib.parse, re, os, datetime

# ── 自动安装依赖 ──────────────────────────────────────
def _pip(pkg):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

for _p in ["qrcode[pil]", "pillow"]:
    try:
        import qrcode; from PIL import Image, ImageTk; break
    except ImportError:
        _pip(_p)

import qrcode
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog

# ══════════════════════════════════════════════════════
#  主题常量
# ══════════════════════════════════════════════════════
BG      = "#0c0f1a"       # 深蓝黑背景
BG2     = "#141828"       # 卡片背景
BG3     = "#1e2438"       # 输入框/代码块背景
BG4     = "#1a1f30"
FG      = "#f0f4ff"       # 主文字：纯白偏蓝，高对比
FG2     = "#c8d0f0"       # 次要文字：亮灰蓝，4K 清晰可读
FG3     = "#909bbf"       # 提示文字：中亮度，不再暗淡
ACC     = "#6c5ce7"       # 主色：深紫
ACC_HV  = "#8878ff"       # 悬停色
ACC2    = "#00e5c4"       # 青绿强调，超高对比
RED     = "#ff5370"       # 错误红，更鲜明
GRN     = "#69ff47"       # 成功绿，亮度更高
YEL     = "#ffcc00"       # 警告黄，纯正
ORG     = "#ff9500"       # 橙色
BORDER  = "#2a3050"
TOAST_BG = "#0e2010"

# ── 4K 大字体配置 ──────────────────────────────────────
FONT        = ("Segoe UI", 15)
FONT_B      = ("Segoe UI", 15, "bold")
FONT_MONO   = ("Consolas", 14)
FONT_MONO_B = ("Consolas", 14, "bold")
FONT_BIG    = ("Segoe UI", 21, "bold")
FONT_SM     = ("Segoe UI", 13)       # "小字"也要清晰可读
FONT_HINT   = ("Segoe UI", 13)       # 提示专用

QR_CARD_SIZE = 340   # 卡片内二维码尺寸
QR_ZOOM_SIZE = 680   # 放大预览尺寸

SCHEME_COLOR = {
    "TUIC":      "#a78bfa",
    "VLESS":     "#5eead4",
    "VMESS":     "#fb923c",
    "TROJAN":    "#fbbf24",
    "SS":        "#f472b6",
    "HYSTERIA2": "#4ade80",
    "HY2":       "#4ade80",
    "HYSTERIA":  "#4ade80",
    "SSR":       "#f472b6",
}

KNOWN_SCHEMES = ("tuic://","vless://","vmess://","trojan://",
                 "ss://","ssr://","hysteria://","hysteria2://","hy2://")

# ══════════════════════════════════════════════════════
#  链接修复 / 诊断
# ══════════════════════════════════════════════════════

def normalize_link(raw: str):
    """返回 (修复后链接, [修复说明列表])"""
    link  = raw.strip()
    fixes = []
    scheme = link.split("://")[0].lower() if "://" in link else ""
    if scheme == "tuic":
        link, fixes = _fix_tuic(link)
    return link, fixes


def _fix_tuic(link: str):
    fixes = []

    # 1. 修复 userinfo 中的 %3A（uuid%3Apassword → uuid:password）
    m = re.match(r'^(tuic://)([^@\[]+)(@.*)$', link, re.IGNORECASE)
    if m:
        prefix, userinfo, rest = m.group(1), m.group(2), m.group(3)
        decoded = urllib.parse.unquote(userinfo)
        if ":" in decoded:
            uuid, password = decoded.split(":", 1)
            if decoded != userinfo:
                fixes.append("修复 %3A：uuid:password 已正确分离")
        else:
            uuid, password = decoded, ""
        link = prefix + f"{uuid}:{password}" + rest

    # 2. 修复 insecure / allowInsecure 参数互补
    try:
        parsed = urllib.parse.urlparse(link)
        params = dict(urllib.parse.parse_qsl(parsed.query, keep_blank_values=True))
        changed = False
        if params.get("insecure") == "1" and params.get("allowInsecure") != "1":
            params["allowInsecure"] = "1"
            fixes.append("补充 allowInsecure=1（源自 insecure=1）")
            changed = True
        if params.get("allowInsecure") == "1" and params.get("insecure") != "1":
            params["insecure"] = "1"
            changed = True
        if changed:
            link = urllib.parse.urlunparse(parsed._replace(
                query=urllib.parse.urlencode(params)))
    except Exception:
        pass

    return link, fixes


def diagnose_link(link: str):
    """返回诊断信息列表"""
    info   = []
    scheme = link.split("://")[0].lower() if "://" in link else "unknown"

    if "[" in link and "]" in link:
        info.append("📌 IPv6 地址")

    if scheme == "tuic":
        m = re.match(r'^tuic://([^@]+)@', link)
        if m:
            ui = urllib.parse.unquote(m.group(1))
            if ":" in ui:
                uuid, pw = ui.split(":", 1)
                info.append(f"UUID    : {uuid}")
                info.append(f"密码    : {'●' * min(6, len(pw))}  ({len(pw)} 字符)")
            else:
                info.append(f"❌ 未找到密码  userinfo={ui[:40]}")
        try:
            parsed = urllib.parse.urlparse(link)
            pdict  = dict(urllib.parse.parse_qsl(parsed.query))
            info.append(f"服务器  : {parsed.hostname}:{parsed.port}")
            info.append(f"拥塞控制: {pdict.get('congestion_control','未设置')}")
            info.append(f"ALPN    : {pdict.get('alpn','未设置')}")
            info.append(f"跳过验证: allowInsecure={pdict.get('allowInsecure','0')}")
        except Exception:
            pass
    elif scheme in ("vless", "vmess", "trojan"):
        try:
            parsed = urllib.parse.urlparse(link)
            pdict  = dict(urllib.parse.parse_qsl(parsed.query))
            info.append(f"服务器  : {parsed.hostname}:{parsed.port}")
            tag = urllib.parse.unquote(parsed.fragment or "")
            if tag:
                info.append(f"备注    : {tag}")
            if pdict.get("security"):
                info.append(f"安全    : {pdict['security']}")
            if pdict.get("type"):
                info.append(f"传输    : {pdict['type']}")
        except Exception:
            pass

    info.append(f"链接长度: {len(link)} 字符")
    return info


# ══════════════════════════════════════════════════════
#  QR 生成工具函数
# ══════════════════════════════════════════════════════

def make_qr_pil(text: str, box_size=10, border=3):
    """返回 (PIL Image, version)"""
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=box_size, border=border)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#111111", back_color="#ffffff")
    return img, qr.version


# ══════════════════════════════════════════════════════
#  Toast 通知（右下角浮动，自动消失）
# ══════════════════════════════════════════════════════

class Toast:
    _instance = None

    @classmethod
    def show(cls, root, msg: str, duration=2000, color=GRN):
        if cls._instance:
            try: cls._instance.destroy()
            except Exception: pass
        cls._instance = cls._make(root, msg, color)
        root.after(duration, cls._dismiss)

    @classmethod
    def _dismiss(cls):
        if cls._instance:
            try: cls._instance.destroy()
            except Exception: pass
            cls._instance = None

    @staticmethod
    def _make(root, msg, color):
        w = tk.Toplevel(root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.configure(bg=TOAST_BG)
        # 半透明（Windows）
        try: w.attributes("-alpha", 0.92)
        except Exception: pass

        tk.Label(w, text=f"  {msg}  ", bg=TOAST_BG, fg=color,
                 font=FONT_B, pady=10, padx=4).pack()

        # 位置：右下角
        root.update_idletasks()
        rw = root.winfo_width();  rx = root.winfo_x()
        rh = root.winfo_height(); ry = root.winfo_y()
        tw = 460; th = 58
        x = rx + rw - tw - 28
        y = ry + rh - th - 64
        w.geometry(f"{tw}x{th}+{x}+{y}")
        return w


# ══════════════════════════════════════════════════════
#  右键菜单辅助
# ══════════════════════════════════════════════════════

def attach_text_context_menu(widget, root):
    """为文本框绑定右键菜单（剪切/复制/粘贴/全选/清空）"""
    menu = tk.Menu(root, tearoff=0, bg=BG3, fg=FG, activebackground=ACC,
                   activeforeground="white", bd=0, font=FONT,
                   relief="flat")

    def cut():
        try:
            widget.event_generate("<<Cut>>")
        except Exception: pass

    def copy():
        try:
            widget.event_generate("<<Copy>>")
        except Exception: pass

    def paste():
        try:
            widget.event_generate("<<Paste>>")
        except Exception: pass

    def select_all():
        try:
            widget.tag_add("sel", "1.0", "end")
            widget.mark_set("insert", "end")
        except Exception: pass

    def clear_all():
        try:
            widget.delete("1.0", "end")
        except Exception: pass

    def paste_and_gen():
        try:
            widget.delete("1.0", "end")
            widget.event_generate("<<Paste>>")
            root.after(80, root._auto_gen)
        except Exception: pass

    menu.add_command(label="  剪切        Ctrl+X", command=cut)
    menu.add_command(label="  复制        Ctrl+C", command=copy)
    menu.add_command(label="  粘贴        Ctrl+V", command=paste)
    menu.add_separator()
    menu.add_command(label="  粘贴并生成  Ctrl+G", command=paste_and_gen)
    menu.add_separator()
    menu.add_command(label="  全选        Ctrl+A", command=select_all)
    menu.add_command(label="  清空全部",           command=clear_all)

    def show(event):
        try: menu.tk_popup(event.x_root, event.y_root)
        finally: menu.grab_release()

    widget.bind("<Button-3>", show)
    widget.bind("<Control-a>", lambda e: select_all())


def attach_canvas_context_menu(canvas, card, root):
    """为二维码画布绑定右键菜单"""
    menu = tk.Menu(root, tearoff=0, bg=BG3, fg=FG, activebackground=ACC,
                   activeforeground="white", bd=0, font=FONT, relief="flat")

    menu.add_command(label="  🔍 放大查看",
                     command=card._zoom)
    menu.add_separator()
    menu.add_command(label="  💾 保存 PNG（高清）",
                     command=card._save)
    menu.add_separator()
    menu.add_command(label="  📋 复制修复后链接",
                     command=card._copy_fixed)
    menu.add_command(label="  📋 复制原始链接",
                     command=card._copy_orig)

    def show(event):
        try: menu.tk_popup(event.x_root, event.y_root)
        finally: menu.grab_release()

    canvas.bind("<Button-3>", show)
    canvas.bind("<Button-1>", lambda e: card._zoom())   # 左键单击也放大


# ══════════════════════════════════════════════════════
#  二维码放大窗口
# ══════════════════════════════════════════════════════

class ZoomWindow(tk.Toplevel):
    def __init__(self, root, card):
        super().__init__(root)
        scheme = card.fixed.split("://")[0].upper() if "://" in card.fixed else "LINK"
        tag    = urllib.parse.unquote(
            urllib.parse.urlparse(card.fixed).fragment or "").strip()
        self.title(f"二维码放大  —  {scheme}  {tag}")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        # 生成高清 QR
        pil, ver = make_qr_pil(card.fixed, box_size=14, border=4)
        pil = pil.resize((QR_ZOOM_SIZE, QR_ZOOM_SIZE), Image.NEAREST)
        self._img = ImageTk.PhotoImage(pil)

        # 画布
        cv = tk.Canvas(self, bg="#ffffff", width=QR_ZOOM_SIZE,
                       height=QR_ZOOM_SIZE, bd=0, highlightthickness=0)
        cv.pack(padx=20, pady=(20, 8))
        cv.create_image(0, 0, anchor="nw", image=self._img)

        # 信息栏
        info_frame = tk.Frame(self, bg=BG2)
        info_frame.pack(fill="x", padx=20, pady=(0, 6))
        scheme_color = SCHEME_COLOR.get(scheme, FG2)
        tk.Label(info_frame, text=f"  {scheme}",
                 bg=BG2, fg=scheme_color, font=FONT_B, pady=6).pack(side="left")
        tk.Label(info_frame,
                 text=f"QR版本 {ver}  ·  {len(card.fixed)} 字符",
                 bg=BG2, fg=FG2, font=FONT_SM).pack(side="left", padx=8)

        # 按钮行
        br = tk.Frame(self, bg=BG)
        br.pack(pady=(0, 16))
        for text, color, cmd in [
            ("💾 保存高清PNG", ACC,  card._save),
            ("📋 复制修复链接", BG3, card._copy_fixed),
            ("✕  关闭",        BG3, self.destroy),
        ]:
            tk.Button(br, text=text, bg=color, fg=FG if color==BG3 else "white",
                      font=FONT_B, relief="flat", bd=0, cursor="hand2",
                      padx=14, pady=8, activebackground=ACC_HV,
                      activeforeground="white",
                      command=cmd).pack(side="left", padx=4)

        self.bind("<Escape>", lambda e: self.destroy())

        # 居中显示
        self.update_idletasks()
        rw = root.winfo_width(); rx = root.winfo_x()
        rh = root.winfo_height(); ry = root.winfo_y()
        ww = self.winfo_width();  wh = self.winfo_height()
        self.geometry(f"+{rx+(rw-ww)//2}+{ry+(rh-wh)//2}")


# ══════════════════════════════════════════════════════
#  卡片组件
# ══════════════════════════════════════════════════════

class QRCard(tk.Frame):
    def __init__(self, master, idx, original, fixed, fixes, diag, root_app, **kw):
        super().__init__(master, bg=BG2, bd=0,
                         highlightthickness=1, highlightbackground=BORDER, **kw)
        self.original = original
        self.fixed    = fixed
        self.root_app = root_app
        self._pil     = None
        self._tkimg   = None
        self._build(idx, fixes, diag)

    # ── 构建 UI ───────────────────────────────────────
    def _build(self, idx, fixes, diag):
        scheme = self.fixed.split("://")[0].upper() if "://" in self.fixed else "LINK"
        sc     = SCHEME_COLOR.get(scheme, FG2)

        # 标题行
        hdr = tk.Frame(self, bg=BG3)
        hdr.pack(fill="x")

        # 协议标签（彩色小块）
        tk.Label(hdr, text=f"  {scheme}  ", bg=sc, fg=BG,
                 font=FONT_B, pady=2).pack(side="left", padx=(12, 8), pady=10)

        # 备注名
        try:
            tag = urllib.parse.unquote(
                urllib.parse.urlparse(self.fixed).fragment or "").strip()
        except Exception:
            tag = ""
        if tag:
            tk.Label(hdr, text=tag, bg=BG3, fg=FG,
                     font=FONT_B).pack(side="left")
        tk.Label(hdr, text=f"  #{idx+1}", bg=BG3, fg=FG3,
                 font=FONT_SM).pack(side="left")

        # 右侧按钮
        for label, color, fg_c, cmd in [
            ("🔍 放大",     BG3,  ACC2,   self._zoom),
            ("💾 保存PNG",  ACC,  "white", self._save),
            ("📋 修复链接", BG3,  ACC2,   self._copy_fixed),
            ("📋 原始链接", BG3,  FG2,    self._copy_orig),
        ]:
            tk.Button(hdr, text=label, bg=color, fg=fg_c,
                      font=FONT_SM, relief="flat", bd=0,
                      padx=12, pady=2, cursor="hand2",
                      activebackground=ACC_HV, activeforeground="white",
                      command=cmd).pack(side="right", padx=3, pady=8)

        # 主体（左：QR  右：信息）
        body = tk.Frame(self, bg=BG2)
        body.pack(fill="x", padx=12, pady=10)

        # 左：二维码
        lf = tk.Frame(body, bg=BG2)
        lf.pack(side="left", anchor="n")

        qr_wrap = tk.Frame(lf, bg=BORDER, padx=2, pady=2)
        qr_wrap.pack()
        self.canvas = tk.Canvas(qr_wrap, bg="#ffffff",
                                width=QR_CARD_SIZE, height=QR_CARD_SIZE,
                                bd=0, highlightthickness=0,
                                cursor="hand2")
        self.canvas.pack()

        # 绑定右键 / 左键
        attach_canvas_context_menu(self.canvas, self, self.root_app)

        tk.Label(lf, text="单击放大  ·  右键菜单",
                 bg=BG2, fg=FG2, font=FONT_HINT).pack(pady=(6, 0))

        self.ver_var = tk.StringVar(value="生成中…")
        tk.Label(lf, textvariable=self.ver_var,
                 bg=BG2, fg=ACC2, font=FONT_SM,
                 justify="center").pack(pady=(3, 0))

        # 右：信息面板
        rf = tk.Frame(body, bg=BG2)
        rf.pack(side="left", anchor="n", padx=(14, 0), fill="x", expand=True)

        # 修复说明
        if fixes:
            self._row_head(rf, "🔧 已自动修复", YEL)
            for f in fixes:
                self._info_row(rf, f"✔  {f}", YEL)
            self._sep(rf)
        else:
            self._row_head(rf, "✅ 链接格式正常，无需修复", GRN)
            self._sep(rf)

        # 解析详情
        self._row_head(rf, "🔍 解析详情", FG2)
        for d in diag:
            c = RED if "❌" in d else YEL if "⚠️" in d else FG2
            self._info_row(rf, d, c)
        self._sep(rf)

        # 修复后链接预览（可选择复制）
        self._row_head(rf, "扫码内容（修复后链接）", ACC2)
        self._link_box(rf, self.fixed)

        # 如果原始 != 修复后，也显示原始
        if self.fixed != self.original:
            self._row_head(rf, "原始链接", FG3)
            self._link_box(rf, self.original, color=FG3)

        # 异步生成 QR
        threading.Thread(target=self._gen, daemon=True).start()

    def _row_head(self, parent, text, color):
        tk.Label(parent, text=text, bg=BG2, fg=color,
                 font=FONT_MONO_B).pack(anchor="w", pady=(8, 3))

    def _info_row(self, parent, text, color):
        tk.Label(parent, text=f"  {text}", bg=BG2, fg=color,
                 font=FONT_MONO, anchor="w", justify="left",
                 wraplength=560).pack(fill="x")

    def _sep(self, parent):
        tk.Frame(parent, bg=BORDER, height=2).pack(fill="x", pady=8)

    def _link_box(self, parent, text, color=None):
        """显示可选中（能右键复制）的链接文本框"""
        color = color or ACC2
        e = tk.Text(parent, height=2, bg=BG3, fg=color,
                    font=FONT_MONO, relief="flat", bd=0,
                    wrap="word", padx=10, pady=8,
                    selectbackground=ACC, insertwidth=0)
        e.insert("1.0", text)
        e.configure(state="disabled")   # 只读但可选中
        e.pack(fill="x", pady=(0, 2))

        # 右键菜单（只有复制和全选）
        ctx = tk.Menu(self.root_app, tearoff=0, bg=BG3, fg=FG,
                      activebackground=ACC, activeforeground="white",
                      bd=0, font=FONT, relief="flat")
        ctx.add_command(label="  复制全部",
                        command=lambda: (
                            self.root_app.clipboard_clear(),
                            self.root_app.clipboard_append(text),
                            Toast.show(self.root_app, "✔ 已复制到剪贴板")))

        def show_ctx(ev):
            try: ctx.tk_popup(ev.x_root, ev.y_root)
            finally: ctx.grab_release()

        e.bind("<Button-3>", show_ctx)

    # ── QR 生成 ───────────────────────────────────────
    def _gen(self):
        try:
            pil, ver = make_qr_pil(self.fixed, box_size=10, border=3)
            self._pil = pil
            sized = pil.resize((QR_CARD_SIZE, QR_CARD_SIZE), Image.NEAREST)
            photo = ImageTk.PhotoImage(sized)
            self._tkimg = photo
            self.canvas.after(0, lambda: self._draw(photo, ver))
        except Exception as e:
            self.canvas.after(0, lambda: self._err(str(e)))

    def _draw(self, photo, ver):
        self.canvas.create_image(0, 0, anchor="nw", image=photo)
        self.ver_var.set(f"QR版本 {ver}  ·  可被 Hiddify 识别")

    def _err(self, msg):
        self.canvas.configure(bg=BG2)
        self.canvas.create_text(QR_CARD_SIZE // 2, QR_CARD_SIZE // 2,
                                text=f"生成失败\n{msg}",
                                fill=RED, font=("Segoe UI", 10),
                                justify="center")

    # ── 操作 ──────────────────────────────────────────
    def _zoom(self):
        ZoomWindow(self.root_app, self)

    def _save(self, path=None):
        if not self._pil:
            Toast.show(self.root_app, "⏳ 二维码尚未生成，稍候再试", color=YEL)
            return None
        if path is None:
            scheme = self.fixed.split("://")[0].lower()
            try:
                tag = urllib.parse.unquote(
                    urllib.parse.urlparse(self.fixed).fragment or "").strip()
                default_name = f"qr_{scheme}_{tag[:20]}.png" if tag else f"qr_{scheme}.png"
            except Exception:
                default_name = f"qr_{scheme}.png"
            path = filedialog.asksaveasfilename(
                defaultextension=".png",
                filetypes=[("PNG 图片", "*.png")],
                initialfile=default_name,
                title="保存二维码（高清）")
        if path:
            pil, _ = make_qr_pil(self.fixed, box_size=14, border=4)
            pil.save(path)
            Toast.show(self.root_app, f"✔ 已保存：{os.path.basename(path)}")
        return path

    def _copy_fixed(self):
        self.root_app.clipboard_clear()
        self.root_app.clipboard_append(self.fixed)
        Toast.show(self.root_app, "✔ 修复后链接已复制")

    def _copy_orig(self):
        self.root_app.clipboard_clear()
        self.root_app.clipboard_append(self.original)
        Toast.show(self.root_app, "✔ 原始链接已复制")


# ══════════════════════════════════════════════════════
#  主窗口
# ══════════════════════════════════════════════════════

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("代理链接 → 二维码  v2.0  |  TUIC / VLESS / VMess / Trojan / SS")
        self.geometry("1280x1120")
        self.minsize(900, 700)
        self.configure(bg=BG)
        self._cards: list[QRCard] = []
        self._build()
        self._bind_shortcuts()

    # ── 快捷键 ────────────────────────────────────────
    def _bind_shortcuts(self):
        self.bind("<Control-Return>", lambda e: self._generate())
        self.bind("<Control-g>",      lambda e: self._generate())
        self.bind("<Control-l>",      lambda e: self._from_clip())
        self.bind("<Control-d>",      lambda e: self._clear())
        self.bind("<F5>",             lambda e: self._generate())
        self.bind("<Control-s>",      lambda e: self._save_all())
        self.bind("<Escape>",         lambda e: self.inp.focus_set())

    # ── 构建 UI ───────────────────────────────────────
    def _build(self):
        # ── 顶栏 ──
        top = tk.Frame(self, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(top, text="🔗  代理链接  →  二维码",
                 bg=BG, fg=FG, font=FONT_BIG).pack(side="left")
        tk.Label(top, text="TUIC / VLESS / VMess / Trojan / SS / Hysteria2",
                 bg=BG, fg=FG2, font=FONT_SM).pack(side="left", padx=14)
        # 快捷键提示
        tk.Label(top,
                 text="Ctrl+G 生成  ·  Ctrl+L 剪贴板  ·  Ctrl+S 批量保存  ·  Ctrl+D 清空",
                 bg=BG, fg=FG3, font=FONT_HINT).pack(side="right")

        # ── 输入区 ──
        inp_outer = tk.Frame(self, bg=BORDER, padx=1, pady=1)
        inp_outer.pack(fill="x", padx=16, pady=(2, 0))
        inp_inner = tk.Frame(inp_outer, bg=BG2)
        inp_inner.pack(fill="x")

        inp_top = tk.Frame(inp_inner, bg=BG2)
        inp_top.pack(fill="x", padx=10, pady=(9, 3))
        tk.Label(inp_top,
                 text="粘贴分享链接（每行一条，支持多条）",
                 bg=BG2, fg=FG2, font=FONT_SM).pack(side="left")
        tk.Label(inp_top,
                 text="右键可剪切 / 粘贴 / 全选",
                 bg=BG2, fg=ACC2, font=FONT_SM).pack(side="right")

        self.inp = scrolledtext.ScrolledText(
            inp_inner, height=6, bg=BG3, fg=FG,
            insertbackground=FG, font=FONT_MONO,
            relief="flat", bd=0, wrap="word",
            selectbackground=ACC, undo=True)
        self.inp.pack(fill="x", padx=10, pady=(0, 8))

        # 绑定右键菜单和快捷粘贴
        attach_text_context_menu(self.inp, self)
        self.inp.bind("<Control-v>", lambda e: self.after(80, self._auto_gen))
        self.inp.bind("<Control-g>", lambda e: self._generate())
        self.inp.focus_set()

        # ── 按钮行 ──
        br = tk.Frame(self, bg=BG)
        br.pack(fill="x", padx=16, pady=8)

        btn_defs = [
            ("▶  生成二维码   F5",       ACC,  "white", self._generate),
            ("📋 从剪贴板读取  Ctrl+L",  BG3,  ACC2,   self._from_clip),
            ("💾 批量保存全部  Ctrl+S",  BG3,  YEL,    self._save_all),
            ("🗑  清空   Ctrl+D",        BG3,  FG2,    self._clear),
        ]
        for text, bg, fg, cmd in btn_defs:
            tk.Button(br, text=text, bg=bg, fg=fg, font=FONT_B,
                      relief="flat", bd=0, cursor="hand2",
                      activebackground=ACC_HV, activeforeground="white",
                      command=cmd).pack(side="left", ipadx=14, ipady=9, padx=(0, 10))

        self.st = tk.StringVar(value="粘贴链接后按 Ctrl+G 或点击「生成二维码」")
        self._st_label = tk.Label(br, textvariable=self.st, bg=BG,
                                  fg=ACC2, font=FONT_SM)
        self._st_label.pack(side="right", padx=4)

        # ── 分隔线 ──
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=16, pady=2)

        # ── 滚动结果区 ──
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=16, pady=(4, 14))

        self.cv = tk.Canvas(outer, bg=BG, bd=0, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=self.cv.yview)
        self.cv.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.cv.pack(side="left", fill="both", expand=True)

        self.res = tk.Frame(self.cv, bg=BG)
        self._win_id = self.cv.create_window((0, 0), window=self.res, anchor="nw")

        self.res.bind("<Configure>",
                      lambda e: self.cv.configure(
                          scrollregion=self.cv.bbox("all")))
        self.cv.bind("<Configure>",
                     lambda e: self.cv.itemconfig(self._win_id, width=e.width))
        # 鼠标滚轮
        self.cv.bind_all("<MouseWheel>",
                         lambda e: self.cv.yview_scroll(
                             -1 * (e.delta // 120), "units"))

        self._show_empty()

    def _show_empty(self):
        for w in self.res.winfo_children():
            w.destroy()
        tk.Label(self.res,
                 text="↑  在上方粘贴代理链接，然后按  Ctrl+G  生成二维码\n\n"
                      "自动修复：  TUIC  uuid%3Apassword  →  uuid:password\n"
                      "            insecure=1  →  补充 allowInsecure=1\n\n"
                      "支持协议：  TUIC  ·  VLESS  ·  VMess  ·  Trojan  ·  SS  ·  Hysteria2\n\n"
                      "快捷键：  Ctrl+G 生成  ·  Ctrl+L 剪贴板  ·  Ctrl+S 批量保存\n"
                      "          右键输入框 → 剪切 / 复制 / 粘贴 / 全选\n"
                      "          单击二维码 → 放大预览  ·  右键二维码 → 保存 / 复制链接",
                 bg=BG, fg=FG3, font=FONT_HINT,
                 justify="center").pack(expand=True, pady=40)

    # ── 核心逻辑 ──────────────────────────────────────
    def _from_clip(self):
        try:
            text = self.clipboard_get().strip()
        except Exception:
            Toast.show(self, "⚠ 无法读取剪贴板", color=YEL)
            return
        if not text:
            Toast.show(self, "⚠ 剪贴板为空", color=YEL)
            return
        self.inp.delete("1.0", "end")
        self.inp.insert("1.0", text)
        self._generate()

    def _auto_gen(self):
        """Ctrl+V 粘贴后自动触发：仅当内容是合法链接才生成"""
        content = self.inp.get("1.0", "end").strip()
        if any(content.lower().startswith(s) for s in KNOWN_SCHEMES):
            self._generate()

    def _generate(self):
        raw = self.inp.get("1.0", "end").strip()
        if not raw:
            Toast.show(self, "⚠ 请先粘贴链接", color=YEL)
            return

        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        if not lines:
            Toast.show(self, "⚠ 未检测到有效链接", color=YEL)
            return

        # 清空旧结果
        for w in self.res.winfo_children():
            w.destroy()
        self._cards.clear()

        total_fixes = 0
        for i, raw_link in enumerate(lines):
            fixed, fixes = normalize_link(raw_link)
            diag         = diagnose_link(fixed)
            total_fixes += len(fixes)
            card = QRCard(self.res, i, raw_link, fixed, fixes, diag, self)
            card.pack(fill="x", pady=6)
            self._cards.append(card)

        n = len(lines)
        msg = f"✅ {n} 个二维码"
        if total_fixes:
            msg += f"  （修复 {total_fixes} 处）"
        msg += "  —  单击二维码可放大"
        self.st.set(msg)
        self.cv.yview_moveto(0)

    def _save_all(self):
        """批量保存所有二维码到文件夹"""
        if not self._cards:
            Toast.show(self, "⚠ 尚无二维码，请先生成", color=YEL)
            return
        folder = filedialog.askdirectory(title="选择保存文件夹（所有二维码将保存到此）")
        if not folder:
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        saved = 0
        for i, card in enumerate(self._cards):
            if card._pil is None:
                continue
            scheme = card.fixed.split("://")[0].lower()
            try:
                tag = urllib.parse.unquote(
                    urllib.parse.urlparse(card.fixed).fragment or "").strip()
                safe_tag = re.sub(r'[\\/:*?"<>|]', '_', tag)[:30]
                fname = f"{i+1:02d}_{scheme}_{safe_tag}.png" if safe_tag \
                        else f"{i+1:02d}_{scheme}_{ts}.png"
            except Exception:
                fname = f"{i+1:02d}_{scheme}_{ts}.png"
            path = os.path.join(folder, fname)
            pil, _ = make_qr_pil(card.fixed, box_size=14, border=4)
            pil.save(path)
            saved += 1
        Toast.show(self, f"✔ 已保存 {saved} 个二维码到文件夹",
                   duration=3000, color=GRN)

    def _clear(self):
        self.inp.delete("1.0", "end")
        self._cards.clear()
        self._show_empty()
        self.st.set("已清空")
        self.inp.focus_set()


# ══════════════════════════════════════════════════════
#  启动
# ══════════════════════════════════════════════════════

if __name__ == "__main__":
    app = App()
    # 让 Windows 任务栏图标正常显示
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    app.mainloop()
