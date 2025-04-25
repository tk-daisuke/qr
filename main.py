import tkinter as tk
from tkinter import simpledialog, messagebox, ttk, StringVar, BooleanVar
from PIL import Image, ImageTk
import qrcode
import io
import json
import os
import base64
from io import BytesIO
# .venv\Scripts\activate

# Data Matrixサポートの確認
try:
    from pylibdmtx import pylibdmtx
    DATAMATRIX_AVAILABLE = True
except ImportError:
    DATAMATRIX_AVAILABLE = False

# 注: Aztecコードのサポートには追加のライブラリが必要です
# 現在の実装ではQRコードとData Matrixコードに焦点を当てています

class QROverlayTool:
    """
    画面上にQRコードを表示する透過型オーバーレイツール
    機能:
    - 複数のQRコードを登録・保存
    - 他のアプリケーション上にコードをオーバーレイ表示
    - タイトルバーをドラッグしてウィンドウを移動
    - 常に最前面モードの切り替え
    - 最小限のUIのみ表示
    """
    
    def __init__(self, root):
        """アプリケーションをルートウィンドウで初期化する"""
        # メインアプリケーションウィンドウ
        self.root = root
        self.root.title("QRコードオーバーレイツール")
        self.root.geometry("250x250")
        
        # 標準ウィンドウ装飾を削除
        self.root.overrideredirect(True)
        
        # ウィンドウを半透明にする
        self.root.attributes("-alpha", 0.9)
        
        # QRコードの保存
        self.qr_codes = []
        self.current_qr_index = 0
        
        # ドラッグ変数
        self.drag_x = 0
        self.drag_y = 0
        self.dragging = False
        
        # UI表示フラグ
        self.ui_visible = True
        
        # 常に最前面に表示する変数
        self.always_on_top = BooleanVar(value=True)
        self.root.attributes("-topmost", self.always_on_top.get())
        
        # 保存されたQRコードをロード
        self.load_qr_codes()
        
        # UIを作成
        self.create_ui()
        
        # イベントをバインド
        self.bind_events()
        
        # 初期QR表示
        self.update_qr_display()
    
    def create_ui(self):
        """全てのUI要素を作成"""
        # 半透明の背景を持つメインフレーム
        self.main_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # カスタムタイトルバー
        self.title_bar = tk.Frame(self.main_frame, bg="#2c3e50", height=25)
        self.title_bar.pack(fill=tk.X, side=tk.TOP)
        
        # タイトルラベル
        self.title_label = tk.Label(self.title_bar, text="QRコードオーバーレイツール", 
                                    bg="#2c3e50", fg="white", padx=5)
        self.title_label.pack(side=tk.LEFT)
        
        # タイトルバーの最小化と閉じるボタン
        self.min_button = tk.Button(self.title_bar, text="_", bg="#2c3e50", fg="white",
                                  font=("Arial", 8), bd=0, padx=5, command=self.minimize)
        self.min_button.pack(side=tk.RIGHT)
        
        self.close_button = tk.Button(self.title_bar, text="×", bg="#2c3e50", fg="white",
                                    font=("Arial", 8), bd=0, padx=5, command=self.exit_app)
        self.close_button.pack(side=tk.RIGHT)
        
        # コントロールバー
        self.control_frame = tk.Frame(self.main_frame, bg="#ecf0f1", height=30)
        self.control_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # UIのトグルボタン
        self.ui_toggle_button = tk.Button(self.control_frame, text="UI切替", bg="#3498db", fg="white",
                                        font=("Arial", 8), bd=0, padx=5, command=self.toggle_ui)
        self.ui_toggle_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        # QRコード追加ボタン
        self.add_button = tk.Button(self.control_frame, text="QR追加", bg="#2ecc71", fg="white",
                                  font=("Arial", 8), bd=0, padx=5, command=self.show_qr_form)
        self.add_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        # QRコード前後ボタン
        self.prev_button = tk.Button(self.control_frame, text="←", bg="#9b59b6", fg="white",
                                   font=("Arial", 8), bd=0, padx=5, command=self.prev_qr)
        self.prev_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.next_button = tk.Button(self.control_frame, text="→", bg="#9b59b6", fg="white",
                                   font=("Arial", 8), bd=0, padx=5, command=self.next_qr)
        self.next_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 常に最前面に表示するチェックボックス
        self.topmost_check = tk.Checkbutton(self.control_frame, text="最前面", 
                                          variable=self.always_on_top, bg="#ecf0f1",
                                          command=self.toggle_topmost)
        self.topmost_check.pack(side=tk.LEFT, padx=2, pady=2)
        
        # QR登録フォーム（デフォルトでは非表示）
        self.qr_form_frame = tk.Frame(self.main_frame, bg="#ecf0f1", padx=10, pady=10)
        
        # QRコード表示エリア
        self.qr_display = tk.Label(self.main_frame, bg="#ffffff")
        self.qr_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def bind_events(self):
        """ドラッグのためのイベントをバインド"""
        self.title_bar.bind("<ButtonPress-1>", self.start_drag)
        self.title_bar.bind("<ButtonRelease-1>", self.stop_drag)
        self.title_bar.bind("<B1-Motion>", self.on_drag)
        
    def start_drag(self, event):
        """タイトルバーでドラッグを開始"""
        self.drag_x = event.x
        self.drag_y = event.y
        self.dragging = True
        
    def stop_drag(self, event):
        """タイトルバーでドラッグを停止"""
        self.dragging = False
        
    def on_drag(self, event):
        """タイトルバーでドラッグ中の処理"""
        if self.dragging:
            x = self.root.winfo_x() + event.x - self.drag_x
            y = self.root.winfo_y() + event.y - self.drag_y
            self.root.geometry(f"+{x}+{y}")
    
    def toggle_ui(self):
        """UIの表示/非表示を切り替え"""
        if self.ui_visible:
            self.control_frame.pack_forget()
            self.ui_visible = False
        else:
            self.control_frame.pack(fill=tk.X, side=tk.BOTTOM)
            self.ui_visible = True
    
    def toggle_topmost(self):
        """常に最前面に表示する属性を切り替え"""
        self.root.attributes("-topmost", self.always_on_top.get())
    
    def minimize(self):
        """アプリを最小化"""
        self.root.attributes("-alpha", 0)
        self.root.iconify()
        
    def exit_app(self):
        """アプリを終了"""
        self.save_qr_codes()
        self.root.destroy()
        
    def show_qr_form(self):
        """QRコード登録フォームを表示"""
        # メインフレームから他のものを一時的に削除
        self.qr_display.pack_forget()
        
        # フォームを表示
        self.qr_form_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # フォームの子要素を削除（再作成のため）
        for widget in self.qr_form_frame.winfo_children():
            widget.destroy()
        
        # フォームの要素を作成
        tk.Label(self.qr_form_frame, text="データ:", bg="#ecf0f1").grid(row=0, column=0, sticky="w", pady=5)
        data_entry = tk.Entry(self.qr_form_frame, width=25)
        data_entry.grid(row=0, column=1, pady=5)
        data_entry.focus()
        
        tk.Label(self.qr_form_frame, text="タイプ:", bg="#ecf0f1").grid(row=1, column=0, sticky="w", pady=5)
        
        code_type = StringVar(value="qrcode")
        
        types = ["qrcode"]
        if DATAMATRIX_AVAILABLE:
            types.append("datamatrix")
        
        type_dropdown = ttk.Combobox(self.qr_form_frame, textvariable=code_type, values=types)
        type_dropdown.grid(row=1, column=1, pady=5)
        
        # 保存ボタン
        save_button = tk.Button(self.qr_form_frame, text="保存", bg="#2ecc71", fg="white",
                              command=lambda: self.add_qr(data_entry.get(), code_type.get()))
        save_button.grid(row=2, column=0, pady=10)
        
        # キャンセルボタン
        cancel_button = tk.Button(self.qr_form_frame, text="キャンセル", bg="#e74c3c", fg="white",
                                command=self.cancel_qr_form)
        cancel_button.grid(row=2, column=1, pady=10)
    
    def cancel_qr_form(self):
        """QRコード登録フォームをキャンセル"""
        self.qr_form_frame.pack_forget()
        self.qr_display.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.update_qr_display()
    
    def add_qr(self, data, code_type):
        """新しいQRコードを追加"""
        if not data:
            messagebox.showerror("エラー", "データを入力してください")
            return
        
        try:
            # QRコードを生成
            if code_type == "qrcode":
                img = self.generate_qr_code(data)
            elif code_type == "datamatrix" and DATAMATRIX_AVAILABLE:
                img = self.generate_datamatrix(data)
            else:
                messagebox.showerror("エラー", "サポートされていないコードタイプです")
                return
            
            # 画像をBase64に変換
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # QRコードを保存
            self.qr_codes.append({
                "data": data,
                "type": code_type,
                "image": img_str
            })
            
            # 現在のインデックスを更新
            self.current_qr_index = len(self.qr_codes) - 1
            
            # QRフォームを閉じる
            self.cancel_qr_form()
            
            # QR表示を更新
            self.update_qr_display()
            
        except Exception as e:
            messagebox.showerror("エラー", f"QRコードの生成に失敗しました: {str(e)}")
    
    def generate_qr_code(self, data):
        """QRコードを生成"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        return qr.make_image(fill_color="black", back_color="white")
    
    def generate_datamatrix(self, data):
        """Data Matrixコードを生成"""
        if not DATAMATRIX_AVAILABLE:
            raise ImportError("pylibdmtxがインストールされていません")
        
        encoded = pylibdmtx.encode(data.encode('utf8'))
        return Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    
    def prev_qr(self):
        """前のQRコードを表示"""
        if self.qr_codes:
            self.current_qr_index = (self.current_qr_index - 1) % len(self.qr_codes)
            self.update_qr_display()
        
    def next_qr(self):
        """次のQRコードを表示"""
        if self.qr_codes:
            self.current_qr_index = (self.current_qr_index + 1) % len(self.qr_codes)
            self.update_qr_display()
    
    def update_qr_display(self):
        """QRコードの表示を更新"""
        if not self.qr_codes:
            # QRがない場合はプレースホルダーを表示
            self.qr_display.config(text="QRコードがありません\nQR追加ボタンでQRコードを登録してください", 
                                   image="", compound=tk.CENTER)
            return
        
        # 現在のQRコードを取得
        qr_data = self.qr_codes[self.current_qr_index]
        
        # Base64からイメージを復元
        img_data = base64.b64decode(qr_data["image"])
        img = Image.open(BytesIO(img_data))
        
        # 表示サイズを調整
        display_width = self.qr_display.winfo_width() or 200
        display_height = self.qr_display.winfo_height() or 200
        
        # アスペクト比を維持しつつリサイズ
        ratio = min(display_width / img.width, display_height / img.height)
        new_width = int(img.width * ratio)
        new_height = int(img.height * ratio)
        
        img = img.resize((new_width, new_height))
        
        # tk.PhotoImageに変換
        self.photo = ImageTk.PhotoImage(img)
        
        # ラベルを更新
        self.qr_display.config(image=self.photo, compound=tk.CENTER)
        self.qr_display.image = self.photo  # 参照を保持
    
    def save_qr_codes(self):
        """QRコードをJSONファイルに保存"""
        data = {
            "qr_codes": self.qr_codes,
            "current_index": self.current_qr_index
        }
        
        try:
            with open("qr_codes.json", "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"QRコードの保存に失敗しました: {str(e)}")
    
    def load_qr_codes(self):
        """JSONファイルからQRコードをロード"""
        try:
            if os.path.exists("qr_codes.json"):
                with open("qr_codes.json", "r") as f:
                    data = json.load(f)
                    self.qr_codes = data.get("qr_codes", [])
                    self.current_qr_index = data.get("current_index", 0)
                    
                    # インデックスが範囲外の場合は調整
                    if self.qr_codes and not (0 <= self.current_qr_index < len(self.qr_codes)):
                        self.current_qr_index = 0
        except Exception as e:
            print(f"QRコードのロードに失敗しました: {str(e)}")


if __name__ == "__main__":
    root = tk.Tk()
    app = QROverlayTool(root)
    
    # ウィンドウが表示された後にQRの表示を更新
    root.after(100, app.update_qr_display)
    
    # ウィンドウが閉じられるときにQRコードを保存
    root.protocol("WM_DELETE_WINDOW", app.exit_app)
    
    root.mainloop()