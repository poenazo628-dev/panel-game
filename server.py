import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import gspread
import traceback
import time
from functools import wraps

# --- 設定 ---
ROUND_IMAGES = [
    'tabetabe1.png', 'tabetabe2.png', 'tabetabe3.png',
    'tabetabe4.png', 'tabetabe5.png', 'tabetabe6.png',
    'tabetabe7.png', 'tabetabe8.png', 'tabetabe9.png'
]
SPREADSHEET_NAME = 'tabetabe-panel'
PRESET_RANGES = [
    'A2:B3', 'C2:E4', 'F2:I5', 'J2:N6', 'O2:T7',
    'U2:AA8', 'AB2:AI9', 'AJ2:AR10', 'AS2:BB11'
]
# -----------

app = Flask(__name__)
CORS(app)

# --- スプレッドシートへの接続 ---
spreadsheet = None
try:
    creds_json_str = os.environ.get('GSPREAD_CREDENTIALS')
    if creds_json_str:
        creds_json = json.loads(creds_json_str)
        gc = gspread.service_account_from_dict(creds_json)
        spreadsheet = gc.open(SPREADSHEET_NAME)
        print("スプレッドシートへの接続に成功しました。")
    else:
        print("!!! GSPREAD_CREDENTIALS環境変数が見つかりません。!!!")
except Exception as e:
    print(f"!!! スプレッドシートへの接続中にエラーが発生しました: {e} !!!")
# ------------------------------------

# --- [新機能] 自動再試行（リトライ）デコレーター ---
def retry_on_error(attempts=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"--- !!! 関数 '{func.__name__}' でエラー発生 (試行 {i + 1}/{attempts}) !!! ---")
                    traceback.print_exc()
                    if i < attempts - 1:
                        print(f"--- {delay}秒待機して再試行します... ---")
                        time.sleep(delay)
                        # 次の試行のためにスプレッドシート接続を再確認
                        global spreadsheet
                        if not spreadsheet:
                           # 再接続処理 (必要に応じて)
                           pass
                    else:
                        print(f"--- !!! 最大再試行回数({attempts}回)に達しました。500エラーを返します。 !!! ---")
                        # 最後の試行でも失敗した場合はエラーを返す
                        raise e
        return wrapper
    return decorator
# ---------------------------------------------

# --- APIエンドポイント ---

@app.route('/get_status')
@retry_on_error()
def get_status():
    player_id = request.args.get('player', 'Player1')
    if player_id == 'ping':
        return jsonify({"status": "success", "message": "Server is awake."})

    if not spreadsheet:
        return jsonify({"status": "error", "message": "Spreadsheet not connected"}), 500

    admin_sheet = spreadsheet.worksheet('AdminControl')
    cell_value = admin_sheet.cell(1, 2).value
    current_round = int(cell_value) if cell_value and cell_value.isdigit() else 0
    
    if current_round > 9:
        return jsonify({"status": "success", "round": "clear"})
    if current_round == 0:
        return jsonify({"status": "success", "round": 0})

    n = current_round + 1
    safe_round_index = max(0, min(current_round - 1, len(ROUND_IMAGES) - 1))
    background_image = ROUND_IMAGES[safe_round_index]
    sheet_to_fetch = 'Player1' if player_id == 'Admin' else player_id
    player_sheet = spreadsheet.worksheet(sheet_to_fetch)
    cell_range = f'A1:{gspread.utils.rowcol_to_a1(n, n)}'
    panel_data = player_sheet.get(cell_range)

    return jsonify({
        "status": "success", "round": current_round, "n": n,
        "panels": panel_data, "backgroundImage": background_image
    })

@app.route('/open_panel', methods=['POST'])
@retry_on_error()
def open_panel():
    data = request.json
    user_id = data.get('user', 'Player1')
    row = data.get('row')
    col = data.get('col')
    worksheet = spreadsheet.worksheet(user_id)
    worksheet.update_cell(row, col, '1')
    return jsonify({"status": "success"})

@app.route('/admin_open_panel', methods=['POST'])
@retry_on_error()
def admin_open_panel():
    data = request.json
    row = data.get('row')
    col = data.get('col')
    worksheet = spreadsheet.worksheet('Player1')
    worksheet.update_cell(row, col, '2')
    return jsonify({"status": "success"})

@app.route('/next_round', methods=['POST'])
@retry_on_error()
def next_round():
    admin_sheet = spreadsheet.worksheet('AdminControl')
    current_round_str = admin_sheet.cell(1, 2).value
    current_round = int(current_round_str) if current_round_str and current_round_str.isdigit() else 0
    
    new_round = current_round + 1
    admin_sheet.update_cell(1, 2, str(new_round))

    if new_round > 9:
         return jsonify({"status": "success", "new_round": "clear"})

    presets_sheet = spreadsheet.worksheet('AdminPresets')
    preset_range = PRESET_RANGES[new_round - 1]
    preset_data = presets_sheet.get(preset_range)

    for i in range(1, 9):
        player_id = f'Player{i}'
        try:
            player_sheet = spreadsheet.worksheet(player_id)
            player_sheet.clear()
            
            update_cells = []
            for r_idx, row_data in enumerate(preset_data):
                for c_idx, cell_value in enumerate(row_data):
                    value_to_set = '2' if str(cell_value) == '1' else '0'
                    cell = gspread.Cell(row=r_idx + 1, col=c_idx + 1, value=value_to_set)
                    update_cells.append(cell)
            if update_cells:
                player_sheet.update_cells(update_cells, value_input_option='RAW')
        except gspread.WorksheetNotFound:
            continue
    
    return jsonify({"status": "success", "new_round": new_round})

@app.route('/calculate_scores', methods=['GET'])
@retry_on_error()
def calculate_scores():
    admin_sheet = spreadsheet.worksheet('AdminControl')
    current_round_str = admin_sheet.cell(1, 2).value
    current_round = int(current_round_str) if current_round_str and current_round_str.isdigit() else 1
    n = current_round + 1
    total_panels = n * n
    
    results = []
    for i in range(1, 9):
        player_id = f'Player{i}'
        try:
            player_sheet = spreadsheet.worksheet(player_id)
            all_values = player_sheet.get(f'A1:{gspread.utils.rowcol_to_a1(n, n)}')
            
            opened_count = 0
            for row in all_values:
                for cell in row:
                    if str(cell) == '1' or str(cell) == '2':
                        opened_count += 1
            
            unopened_count = total_panels - opened_count
            score = abs(unopened_count - opened_count)
            results.append({"player": player_id, "score": score, "opened": opened_count})
        except gspread.WorksheetNotFound:
            continue
    
    results.sort(key=lambda x: x['score'])
    
    results_sheet = spreadsheet.worksheet('Results')
    results_sheet.append_row([f"--- Round {current_round} ---"])
    for res in results:
        results_sheet.append_row([res['player'], res['score'], res['opened']])

    return jsonify({"status": "success", "results": results})

@app.route('/get_final_scores', methods=['GET'])
@retry_on_error()
def get_final_scores():
    results_sheet = spreadsheet.worksheet('Results')
    all_data = results_sheet.get_all_values()
    total_scores = {f'Player{i}': 0 for i in range(1, 9)}

    for row in all_data:
        if len(row) > 0 and isinstance(row[0], str) and row[0].startswith('---'):
            continue
        if len(row) >= 2:
            try:
                player_id, score = row[0], int(row[1])
                if player_id in total_scores:
                    total_scores[player_id] += score
            except (ValueError, IndexError):
                continue
    
    final_results = [{'player': pid, 'score': t_score} for pid, t_score in total_scores.items()]
    final_results.sort(key=lambda x: x['score'])
    return jsonify({"status": "success", "results": final_results})


@app.route('/reset_game', methods=['POST'])
@retry_on_error()
def reset_game():
    admin_sheet = spreadsheet.worksheet('AdminControl')
    admin_sheet.update_cell(1, 2, '0')

    for i in range(1, 9):
        try:
            player_sheet = spreadsheet.worksheet(f'Player{i}')
            player_sheet.clear()
        except gspread.WorksheetNotFound:
            continue
    results_sheet = spreadsheet.worksheet('Results')
    results_sheet.clear()
    return jsonify({"status": "success", "message": "ゲームがリセットされました。"})

# 500エラーハンドリング
@app.errorhandler(Exception)
def handle_exception(e):
    traceback.print_exc()
    return jsonify(status="error", message="Internal Server Error"), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

