import tkinter as tk
from tkinter import simpledialog, messagebox, ttk, StringVar, BooleanVar
from PIL import Image, ImageTk
import io
import json
import os
import base64
from io import BytesIO
import getpass

# Data Matrixサポートの確認
try:
    from pylibdmtx import pylibdmtx
    DATAMATRIX_AVAILABLE = True
except ImportError:
    DATAMATRIX_AVAILABLE = False
    
class DataMatrixTool:
    """
    Data Matrixコード表示ツール
    機能:
    - 複数のData Matrixコードを登録・保存
    - タイトルバーを除くUIを表示/非表示に切り替え
    - ユーザーごとの設定ファイルに保存
    """
    
    def __init__(self, root):
        """アプリケーションをルートウィンドウで初期化する"""
        # メインアプリケーションウィンドウ
        self.root = root
        self.root.title("Data Matrixコードツール")
        self.root.geometry("350x250")
        
        # 標準ウィンドウ装飾を使用
        self.root.overrideredirect(False)
        
        # Data Matrixコードの保存
        self.datamatrix_codes = []
        self.current_index = 0
        
        # UI表示フラグ
        self.ui_visible = True
        
        # 常に最前面に表示する変数
        self.always_on_top = BooleanVar(value=True)
        self.root.attributes("-topmost", self.always_on_top.get())
        
        # 保存されたData Matrixコードをロード
        self.load_codes()
        
        # UIを作成
        self.create_ui()
        
        # 初期表示
        self.update_display()
        
        # デバッグ情報を表示
        print(f"ロードされたコード数: {len(self.datamatrix_codes)}")
        if self.datamatrix_codes:
            print(f"現在のインデックス: {self.current_index}")
            print(f"最初のコードデータ: {self.datamatrix_codes[0]['data'][:20]}...")
    
    def create_ui(self):
        """全てのUI要素を作成"""
        # メインフレーム
        self.main_frame = tk.Frame(self.root, bg="#f0f0f1")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # タイトルバー
        self.title_bar = tk.Frame(self.main_frame, bg="#2c3e50", height=25)
        self.title_bar.pack(fill=tk.X, side=tk.TOP)
        
        # タイトルラベル
        self.title_label = tk.Label(self.title_bar, text="Data Matrixコードツール", 
                                    bg="#2c3e50", fg="white", padx=5)
        self.title_label.pack(side=tk.LEFT)
        
        # UIのトグルボタン
        self.ui_toggle_button = tk.Button(self.title_bar, text="UI切替", bg="#3498db", fg="white",
                                        font=("Arial", 8), bd=0, padx=5, command=self.toggle_ui)
        self.ui_toggle_button.pack(side=tk.RIGHT, padx=2)
        
        # コンテンツフレーム（タイトルバー以外の全UI要素を含む）
        self.content_frame = tk.Frame(self.main_frame, bg="#f0f0f1")
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 表示部分と選択ボタンを含む中央フレーム
        self.center_frame = tk.Frame(self.content_frame, bg="#f0f0f1")
        self.center_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Data Matrix表示エリア
        self.display_frame = tk.Frame(self.center_frame, bg="#ffffff", bd=1, relief=tk.SUNKEN)
        self.display_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)
        
        self.code_display = tk.Label(self.display_frame, bg="#ffffff")
        self.code_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # コード選択ボタンエリア - 明示的に幅と高さを設定
        self.buttons_frame = tk.Frame(self.center_frame, bg="#ecf0f1", bd=1, relief=tk.SUNKEN, width=100, height=200)
        self.buttons_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0), pady=5)
        
        # ボタンフレームを固定サイズに
        self.buttons_frame.pack_propagate(False)
        
        # コントロールバー
        self.control_frame = tk.Frame(self.content_frame, bg="#ecf0f1", height=30)
        self.control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        # Data Matrix追加ボタン
        self.add_button = tk.Button(self.control_frame, text="追加", bg="#2ecc71", fg="white",
                                  font=("Arial", 8), bd=0, padx=5, command=self.show_form)
        self.add_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 削除ボタン
        self.delete_button = tk.Button(self.control_frame, text="削除", bg="#e74c3c", fg="white",
                                    font=("Arial", 8), bd=0, padx=5, command=self.delete_current)
        self.delete_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 前後ボタン
        self.prev_button = tk.Button(self.control_frame, text="←", bg="#9b59b6", fg="white",
                                   font=("Arial", 8), bd=0, padx=5, command=self.prev_code)
        self.prev_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        self.next_button = tk.Button(self.control_frame, text="→", bg="#9b59b6", fg="white",
                                   font=("Arial", 8), bd=0, padx=5, command=self.next_code)
        self.next_button.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 常に最前面に表示するチェックボックス
        self.topmost_check = tk.Checkbutton(self.control_frame, text="最前面", 
                                          variable=self.always_on_top, bg="#ecf0f1",
                                          command=self.toggle_topmost)
        self.topmost_check.pack(side=tk.LEFT, padx=2, pady=2)
        
        # 登録フォーム（デフォルトでは非表示）
        self.form_frame = tk.Frame(self.content_frame, bg="#ecf0f1", padx=10, pady=10)
        
        # キーボードバインディングを追加
        self.root.bind("<Left>", lambda event: self.prev_code())
        self.root.bind("<Right>", lambda event: self.next_code())
    
    def update_buttons(self):
        """コード選択ボタンを更新する"""
        # デバッグ情報表示
        print(f"update_buttons が呼ばれました。コード数: {len(self.datamatrix_codes)}")
        
        # 既存のボタンを削除
        for widget in self.buttons_frame.winfo_children():
            widget.destroy()
            
        if not self.datamatrix_codes:
            # コードがない場合は何も表示しない
            print("コードがないため、ボタンは作成されません")
            return
            
        # ボタンを作成
        for i, code in enumerate(self.datamatrix_codes):
            # データの短縮表示用
            data = code["data"]
            if len(data) > 10:
                data = data[:7] + "..."
                
            # 行と列の計算（6行で次の列に移動）
            row = i % 6
            col = i // 6
            
            # デバッグ情報表示
            print(f"ボタン作成: インデックス={i}, データ={data}, 行={row}, 列={col}")
            
            # ボタンの作成
            btn = tk.Button(
                self.buttons_frame, 
                text=data,
                bg="#3498db" if i == self.current_index else "#95a5a6",
                fg="white",
                font=("Arial", 8),
                bd=0,
                padx=2,
                pady=2,
                width=10,
                command=lambda idx=i: self.select_code(idx)
            )
            btn.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
        
        # ボタン作成後にフレームを更新
        self.buttons_frame.update()
        print(f"ボタン更新完了。合計 {len(self.datamatrix_codes)} 個のボタンを作成")
        
    def select_code(self, index):
        """ボタンで選択されたコードを表示"""
        if 0 <= index < len(self.datamatrix_codes):
            self.current_index = index
            self.update_display()
            
    def delete_current(self):
        """現在表示中のコードを削除"""
        if not self.datamatrix_codes:
            messagebox.showinfo("情報", "削除するコードがありません")
            return
            
        # 確認ダイアログ
        confirm = messagebox.askyesno("確認", "現在のコードを削除しますか？")
        if not confirm:
            return
            
        # 現在のコードを削除
        del self.datamatrix_codes[self.current_index]
        
        # インデックスを調整
        if not self.datamatrix_codes:
            self.current_index = 0
        elif self.current_index >= len(self.datamatrix_codes):
            self.current_index = len(self.datamatrix_codes) - 1
            
        # 表示を更新
        self.update_display()
        self.save_codes()  # 変更を保存
        
    def toggle_ui(self):
        """タイトルバー以外のUIの表示/非表示を切り替え"""
        if self.ui_visible:
            # コンテンツフレーム全体を非表示
            self.content_frame.pack_forget()
            # ウィンドウのサイズをタイトルバーだけのサイズに調整
            self.root.geometry(f"{self.root.winfo_width()}x25")
            self.ui_visible = False
        else:
            # コンテンツフレームを再表示
            self.content_frame.pack(fill=tk.BOTH, expand=True)
            # ウィンドウのサイズを元に戻す
            self.root.geometry("350x250")
            self.ui_visible = True
    
    def toggle_topmost(self):
        """常に最前面に表示する属性を切り替え"""
        self.root.attributes("-topmost", self.always_on_top.get())
    
    def show_form(self):
        """Data Matrix登録フォームを表示"""
        # 現在のコンテンツを一時的に削除
        self.display_frame.pack_forget()
        self.buttons_frame.pack_forget()
        self.control_frame.pack_forget()
        
        # フォームを表示
        self.form_frame.pack(fill=tk.BOTH, expand=True)
        
        # フォームの子要素を削除（再作成のため）
        for widget in self.form_frame.winfo_children():
            widget.destroy()
        
        # フォームの要素を作成
        tk.Label(self.form_frame, text="データ:", bg="#ecf0f1").grid(row=0, column=0, sticky="w", pady=5)
        data_entry = tk.Entry(self.form_frame, width=25)
        data_entry.grid(row=0, column=1, pady=5)
        data_entry.focus()
        
        # 保存ボタン
        save_button = tk.Button(self.form_frame, text="保存", bg="#2ecc71", fg="white",
                              command=lambda: self.add_code(data_entry.get()))
        save_button.grid(row=2, column=0, pady=10)
        
        # キャンセルボタン
        cancel_button = tk.Button(self.form_frame, text="キャンセル", bg="#e74c3c", fg="white",
                                command=self.cancel_form)
        cancel_button.grid(row=2, column=1, pady=10)
    
    def cancel_form(self):
        """フォームをキャンセル"""
        self.form_frame.pack_forget()
        
        # 表示部分と選択ボタンを含む中央フレーム
        self.center_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Data Matrix表示エリアとボタンエリアを再表示
        self.display_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)
        self.buttons_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0), pady=5)
        
        # コントロールバーを再表示
        self.control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=5)
        
        # 表示を更新
        self.update_display()
    
    def add_code(self, data):
        """新しいData Matrixコードを追加"""
        if not data:
            messagebox.showerror("エラー", "データを入力してください")
            return
        
        if not DATAMATRIX_AVAILABLE:
            messagebox.showerror("エラー", "pylibdmtxがインストールされていません。\n"
                               "'pip install pylibdmtx'を実行してください。")
            return
        
        try:
            # Data Matrixコードを生成
            img = self.generate_datamatrix(data)
            
            # 画像をBase64に変換
            buffered = BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            
            # コードを保存
            self.datamatrix_codes.append({
                "data": data,
                "image": img_str
            })
            
            # 現在のインデックスを更新
            self.current_index = len(self.datamatrix_codes) - 1
            
            # フォームを閉じる
            self.cancel_form()
            
            # 表示を更新
            self.update_display()
            
            # 保存
            self.save_codes()
            
        except Exception as e:
            messagebox.showerror("エラー", f"Data Matrixコードの生成に失敗しました: {str(e)}")
    
    def generate_datamatrix(self, data):
        """Data Matrixコードを生成"""
        if not DATAMATRIX_AVAILABLE:
            raise ImportError("pylibdmtxがインストールされていません")
        
        encoded = pylibdmtx.encode(data.encode('utf8'))
        return Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    
    def prev_code(self):
        """前のコードを表示"""
        if self.datamatrix_codes:
            self.current_index = (self.current_index - 1) % len(self.datamatrix_codes)
            self.update_display()
            
    def next_code(self):
        """次のコードを表示"""
        if self.datamatrix_codes:
            self.current_index = (self.current_index + 1) % len(self.datamatrix_codes)
            self.update_display()
    
    def update_display(self):
        """コードの表示を更新"""
        # デバッグ情報表示
        print(f"update_display が呼ばれました。コード数: {len(self.datamatrix_codes)}")
        
        if not self.datamatrix_codes:
            # コードがない場合はプレースホルダーを表示
            self.code_display.config(text="Data Matrixコードがありません\n追加ボタンでコードを登録してください", 
                                   image="", compound=tk.CENTER)
            # ボタンも明示的に更新
            self.update_buttons()
            return
        
        # 現在のコードを取得
        code_data = self.datamatrix_codes[self.current_index]
        
        # 現在表示中のコードの情報を表示（インデックス番号とデータ）
        code_info = f"コード {self.current_index + 1}/{len(self.datamatrix_codes)}: {code_data['data']}"
        
        # Base64からイメージを復元
        img_data = base64.b64decode(code_data["image"])
        img = Image.open(BytesIO(img_data))
        
        # 画像はリサイズせず、オリジナルサイズで表示
        self.photo = ImageTk.PhotoImage(img)
        
        # ラベルを更新し、コード情報も表示
        self.code_display.config(image=self.photo, text=code_info, compound=tk.BOTTOM)
        self.code_display.image = self.photo  # 参照を保持
        
        # ボタンも明示的に更新
        self.update_buttons()
    
    def get_config_path(self):
        """ユーザーごとの設定ファイルパスを取得"""
        # Windowsのログインユーザー名を取得
        username = getpass.getuser()
        
        # ユーザーのホームディレクトリを取得
        home_dir = os.path.expanduser('~')
        # アプリケーションの設定ディレクトリを作成
        config_dir = os.path.join(home_dir, '.datamatrix_tool')
        
        # ディレクトリが存在しない場合は作成
        if not os.path.exists(config_dir):
            try:
                os.makedirs(config_dir)
            except Exception as e:
                print(f"設定ディレクトリの作成に失敗しました: {str(e)}")
                # 失敗した場合はカレントディレクトリを使用
                return f"datamatrix_codes_{username}.json"
        
        # ユーザー固有の設定ファイルパス
        return os.path.join(config_dir, f'datamatrix_codes_{username}.json')
    
    def save_codes(self):
        """コードをJSONファイルに保存"""
        data = {
            "codes": self.datamatrix_codes,
            "current_index": self.current_index
        }
        
        try:
            config_path = self.get_config_path()
            with open(config_path, "w") as f:
                json.dump(data, f)
            print(f"コードを保存しました: {config_path}")
        except Exception as e:
            print(f"コードの保存に失敗しました: {str(e)}")
    
    def load_codes(self):
        """JSONファイルからコードをロード"""
        try:
            config_path = self.get_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    data = json.load(f)
                    self.datamatrix_codes = data.get("codes", [])
                    self.current_index = data.get("current_index", 0)
                    
                    # インデックスが範囲外の場合は調整
                    if self.datamatrix_codes and not (0 <= self.current_index < len(self.datamatrix_codes)):
                        self.current_index = 0
                print(f"コードをロードしました: {config_path}")
            
            # ロードされたコードがなければ初期プリセットを作成
            if not self.datamatrix_codes:
                print("初期プリセットを作成します")
                self.create_presets()
                
        except Exception as e:
            print(f"コードのロードに失敗しました: {str(e)}")
            # エラーが発生した場合も初期プリセットを作成
            print("エラーが発生したため、初期プリセットを作成します")
            self.create_presets()
    
    def create_presets(self):
        """初期プリセットを作成"""
        if not DATAMATRIX_AVAILABLE:
            print("pylibdmtxがインストールされていないため、プリセットを作成できません")
            return
            
        presets = [
            {"name": "TestString", "data": "ts"},
            {"name": "Number", "data": "12"},
            {"name": "テスト", "data": "test"}
        ]
        
        try:
            for preset in presets:
                # Data Matrixコードを生成
                img = self.generate_datamatrix(preset["data"])
                
                # 画像をBase64に変換
                buffered = BytesIO()
                img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                
                # コードを保存
                self.datamatrix_codes.append({
                    "name": preset["name"],
                    "data": preset["data"],
                    "image": img_str
                })
            
            # 最初のプリセットを選択
            self.current_index = 0
            print(f"{len(presets)}個のプリセットを作成しました")
            
            # 設定ファイルに保存
            self.save_codes()
            
        except Exception as e:
            print(f"プリセット作成中にエラーが発生しました: {str(e)}")



if __name__ == "__main__":
    # pylibdmtxが利用可能か確認
    if not DATAMATRIX_AVAILABLE:
        print("警告: pylibdmtxがインストールされていません。")
        print("Data Matrixコードを生成するには次のコマンドを実行してください:")
        print("pip install pylibdmtx")
        # それでも続行する
    
    root = tk.Tk()
    root.geometry("350x250")  # 少し幅を広げてボタン用のスペースを確保
    app = DataMatrixTool(root)
    
    # ウィンドウが表示された後に表示を更新（ボタンも一緒に更新される）
    root.after(100, app.update_display)
    
    # ウィンドウが閉じられるときにコードを保存
    root.protocol("WM_DELETE_WINDOW", lambda: (app.save_codes(), root.destroy()))
    
    root.mainloop()