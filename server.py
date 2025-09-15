import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import gspread

# --- ラウンドごとの背景画像リスト (更新済み) ---
# 画像名をtabetabe1.jpg ~ tabetabe9.jpgに設定
ROUND_IMAGES = [
    'tabetabe1.png',
    'tabetabe2.png',
    'tabetabe3.png',
    'tabetabe4.png',
    'tabetabe5.png',
    'tabetabe6.png',
    'tabetabe7.png',
    'tabetabe8.png',
    'tabetabe9.png',
]
# ------------------------------------

# --- 環境変数から認証情報を読み込む ---
creds_json_str = os.getenv('GSPREAD_CREDENTIALS')
if not creds_json_str:
    raise ValueError("環境変数 GSPREAD_CREDENTIALS が設定されていません。")

creds_dict = json.loads(creds_json_str)
gc = gspread.service_account_from_dict(creds_dict)
# ------------------------------------

# スプレッドシート名を更新
SPREADSHEET_NAME = 'tabetabe-panel'

app = Flask(__name__)
CORS(app)

try:
    spreadsheet = gc.open(SPREADSHEET_NAME)
    print("スプレッドシートへの接続に成功しました。")
except Exception as e:
    print(f"スプレッドシートへの接続に失敗しました: {e}")
    spreadsheet = None

def colnum_to_a1(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string

@app.route('/get_status')
def get_status():
    if not spreadsheet: return jsonify({"status": "error", "message": "Spreadsheet not connected"})
    player_id = 'Player1'
    try:
        player_id = request.args.get('player', 'Player1')
        if player_id == 'Admin':
            player_id = 'Player1'

        admin_sheet = spreadsheet.worksheet('AdminControl')
        current_round = int(admin_sheet.cell(1, 2).value)
        n = current_round + 1
        
        background_image = ''
        round_index = current_round - 1
        if 0 <= round_index < len(ROUND_IMAGES):
            background_image = ROUND_IMAGES[round_index]
        else:
            print(f"!!! 警告: 無効なラウンド番号({current_round})です。デフォルトの画像を使用します。 !!!")
            if ROUND_IMAGES:
                background_image = ROUND_IMAGES[0]

        player_sheet = spreadsheet.worksheet(player_id)
        panel_data = player_sheet.get(f'A1:{colnum_to_a1(n)}{n}')
        
        return jsonify({
            "status": "success",
            "round": current_round,
            "n": n,
            "panels": panel_data,
            "backgroundImage": background_image
        })
    except Exception as e:
        print(f"!!! /get_statusでエラー発生 (Player: {player_id}): {e} !!!")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/calculate_scores')
def calculate_scores():
    if not spreadsheet: return jsonify({"status": "error", "message": "Spreadsheet not connected"})
    try:
        admin_sheet = spreadsheet.worksheet('AdminControl')
        current_round = int(admin_sheet.cell(1, 2).value)
        n = current_round + 1
        total_panels = n * n
        
        results = []
        player_sheets = spreadsheet.worksheets()
        player_ids = [f"Player{i}" for i in range(1, 9)]

        for player_sheet in player_sheets:
            if player_sheet.title in player_ids:
                player_id = player_sheet.title
                panel_data = player_sheet.get(f'A1:{colnum_to_a1(n)}{n}')
                
                opened_count = 0
                for r in range(n):
                    for c in range(n):
                        if r < len(panel_data) and c < len(panel_data[r]):
                            cell = panel_data[r][c]
                            if cell == '1' or cell == '2':
                                opened_count += 1
                
                closed_count = total_panels - opened_count
                score = abs(closed_count - opened_count)
                
                results.append({
                    "player": player_id,
                    "score": score,
                    "opened": opened_count,
                    "closed": closed_count
                })

        results.sort(key=lambda x: x['score'], reverse=True)
        return jsonify({"status": "success", "results": results})

    except Exception as e:
        print(f"!!! /calculate_scoresでエラー発生: {e} !!!")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/open_panel', methods=['POST'])
def open_panel():
    if not spreadsheet: return jsonify({"status": "error", "message": "Spreadsheet not connected"})
    data = request.json
    user_id = 'Unknown'
    try:
        user_id = data.get('user', 'Unknown')
        row = data.get('row')
        col = data.get('col')
        worksheet = spreadsheet.worksheet(user_id)
        worksheet.update_cell(row, col, '1')
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"!!! /open_panelでエラー発生 (Player: {user_id}): {e} !!!")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/admin_open_panel', methods=['POST'])
def admin_open_panel():
    if not spreadsheet: return jsonify({"status": "error", "message": "Spreadsheet not connected"})
    data = request.json
    user_id = 'Unknown'
    try:
        user_id = data.get('user', 'Unknown')
        row = data.get('row')
        col = data.get('col')
        worksheet = spreadsheet.worksheet(user_id)
        worksheet.update_cell(row, col, '2')
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"!!! /admin_open_panelでエラー発生 (Player: {user_id}): {e} !!!")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/next_round', methods=['POST'])
def next_round():
    if not spreadsheet: return jsonify({"status": "error", "message": "Spreadsheet not connected"})
    try:
        admin_sheet = spreadsheet.worksheet('AdminControl')
        current_round = int(admin_sheet.cell(1, 2).value)
        next_round_num = current_round + 1
        if next_round_num > 9:
            next_round_num = 1
        admin_sheet.update_cell(1, 2, next_round_num)
        
        n = next_round_num + 1
        start_col_num = 1
        if next_round_num > 1:
            for i in range(2, next_round_num + 1):
                start_col_num += i
        
        end_col_num = start_col_num + n - 1
        start_row, end_row = 2, n + 1
        start_col_a1, end_col_a1 = colnum_to_a1(start_col_num), colnum_to_a1(end_col_num)
        preset_range = f"{start_col_a1}{start_row}:{end_col_a1}{end_row}"

        presets_sheet = spreadsheet.worksheet('AdminPresets')
        preset_data_2d = presets_sheet.get(preset_range, value_render_option='UNFORMATTED_VALUE')
        
        new_board_data = []
        for r in range(10):
            row_data = []
            for c in range(10):
                if r < n and c < n:
                    if r < len(preset_data_2d) and c < len(preset_data_2d[r]) and str(preset_data_2d[r][c]) == '1':
                        row_data.append('2')
                    else:
                        row_data.append('0')
                else:
                    row_data.append('')
            new_board_data.append(row_data)

        player_ids = [f"Player{i}" for i in range(1, 9)]
        for player_id in player_ids:
            try:
                player_sheet = spreadsheet.worksheet(player_id)
                player_sheet.update('A1:J10', new_board_data)
            except gspread.exceptions.WorksheetNotFound:
                print(f"!!! {player_id}シートが見つかりません。盤面リセットをスキップします。 !!!")
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"!!! /next_roundでエラー発生: {e} !!!")
        return jsonify({"status": "error", "message": str(e)})

# --- ▼▼▼ サーバー起動部分を修正 ▼▼▼ ---
if __name__ == '__main__':
    # Render環境ではgunicornがこのファイルを実行するため、
    # この部分はローカルでのテスト実行時にのみ使用されます。
    # PORT環境変数がなければ、ローカルテスト用に8080をデフォルトとします。
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
# --- ▲▲▲ 修正ここまで ▲▲▲ ---

