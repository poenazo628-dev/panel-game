import gspread

# --- ！！！ここの2行を自分の環境に合わせて書き換えてください！！！ ---
KEY_FILE_NAME = 'project-tabetabe-6bd62e07fa6f.json'
SPREADSHEET_NAME = 'tabetabe-panel' # あなたが作成したスプレッドシートの名前
# ------------------------------------------------------------------

try:
    # 認証処理
    gc = gspread.service_account(filename=KEY_FILE_NAME)
    # スプレッドシートを開く
    spreadsheet = gc.open(SPREADSHEET_NAME)

    print(f"'{SPREADSHEET_NAME}' を開きました。")

    # 'AdminControl'シートを選択
    worksheet = spreadsheet.worksheet('AdminControl')
    print("'AdminControl'シートを選択しました。")

    # A1セルに書き込み
    worksheet.update_cell(1, 1, 'Hello World!')
    print("A1セルに 'Hello World!' と書き込みました。")

    # A1セルを読み込み
    value = worksheet.cell(1, 1).value
    print(f"A1セルの値を読み込みました: {value}")

    print("\nテスト成功です！")

except Exception as e:
    print("\nエラーが発生しました。")
    print("---エラー内容---")
    print(e)
    print("----------------")