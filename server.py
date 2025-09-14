from flask import Flask, jsonify, request
from flask_cors import CORS
import gspread

# --- 設定項目 ---
KEY_FILE_NAME = 'project-tabetabe-6bd62e07fa6f.json' # あなたのJSONファイル名に書き換えてください
SPREADSHEET_NAME = 'tabetabe-panel' # あなたのスプレッドシート名に書き換えてください
# ----------------


app = Flask(__name__)
CORS(app)

try:
    gc = gspread.service_account(filename=KEY_FILE_NAME)
    spreadsheet = gc.open(SPREADSHEET_NAME)
    print("スプレッドシートへの接続に成功しました。")
except Exception as e:
    print(f"スプレッドシートへの接続に失敗しました: {e}")
    spreadsheet = None

# 列番号をA1形式のアルファベットに変換するヘルパー関数
def colnum_to_a1(n):
    string = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        string = chr(65 + remainder) + string
    return string

@app.route('/calculate_scores')
def calculate_scores():
    if not spreadsheet: return jsonify({"status": "error", "message": "Spreadsheet not connected"})
    try:
        admin_sheet = spreadsheet.worksheet('AdminControl')
        current_round = int(admin_sheet.cell(1, 2).value)
        n = current_round + 1
        total_panels = n * n
        
        results = []
        for i in range(1, 9):
            player_id = f"Player{i}"
            try:
                player_sheet = spreadsheet.worksheet(player_id)
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

            except gspread.exceptions.WorksheetNotFound:
                print(f"{player_id}シートが見つかりません。スコア計算から除外します。")
                continue

        return jsonify({"status": "success", "results": results})

    except Exception as e:
        print(f"!!! /calculate_scoresでエラー発生: {e} !!!")
        return jsonify({"status": "error", "message": str(e)})

# ▼▼▼▼▼ ここの関数を修正しました ▼▼▼▼▼
@app.route('/get_status')
def get_status():
    if not spreadsheet: return jsonify({"status": "error"})
    try:
        player_id = request.args.get('player', 'Player1')
        admin_sheet = spreadsheet.worksheet('AdminControl')
        current_round = int(admin_sheet.cell(1, 2).value)
        n = current_round + 1
        player_sheet = spreadsheet.worksheet(player_id)
        
        # バグ修正：ラウンドのサイズに合わせて、正しい範囲のデータを取得するように修正
        panel_data = player_sheet.get(f'A1:{colnum_to_a1(n)}{n}')
        
        return jsonify({"status": "success", "round": current_round, "n": n, "panels": panel_data})
    except Exception as e:
        print(f"!!! /get_statusでエラー発生: {e} !!!")
        return jsonify({"status": "error", "message": str(e)})
# ▲▲▲▲▲ ここまで修正 ▲▲▲▲▲

@app.route('/open_panel', methods=['POST'])
def open_panel():
    if not spreadsheet: return jsonify({"status": "error"})
    try:
        data = request.json
        user_id = data.get('user', 'Unknown')
        row = data.get('row')
        col = data.get('col')
        worksheet = spreadsheet.worksheet(user_id)
        worksheet.update_cell(row, col, '1')
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"!!! /open_panelでエラー発生 (Player: {data.get('user', 'Unknown')}): {e} !!!")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/admin_open_panel', methods=['POST'])
def admin_open_panel():
    if not spreadsheet: return jsonify({"status": "error"})
    try:
        data = request.json
        user_id = data.get('user', 'Unknown')
        row = data.get('row')
        col = data.get('col')
        worksheet = spreadsheet.worksheet(user_id)
        worksheet.update_cell(row, col, '2')
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"!!! /admin_open_panelでエラー発生 (Player: {data.get('user', 'Unknown')}): {e} !!!")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/next_round', methods=['POST'])
def next_round():
    if not spreadsheet: return jsonify({"status": "error"})
    try:
        admin_sheet = spreadsheet.worksheet('AdminControl')
        current_round = int(admin_sheet.cell(1, 2).value)
        next_round_num = current_round + 1
        admin_sheet.update_cell(1, 2, next_round_num)
        
        n = next_round_num + 1
        start_col_num = 1
        if next_round_num > 1:
            for i in range(2, n):
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
                    row_data.append('0')
            new_board_data.append(row_data)

        for i in range(1, 9):
            player_id = f"Player{i}"
            try:
                player_sheet = spreadsheet.worksheet(player_id)
                player_sheet.update('A1:J10', new_board_data)
            except gspread.exceptions.WorksheetNotFound:
                print(f"!!! {player_id}シートが見つかりません。スキップします。 !!!")
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"!!! /next_roundでエラー発生: {e} !!!")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

