import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import gspread
import traceback

# --- 画像とスプレッドシートの設定 ---
ROUND_IMAGES = [
    'tabetabe1.png', 'tabetabe2.png', 'tabetabe3.png',
    'tabetabe4.png', 'tabetabe5.png', 'tabetabe6.png',
    'tabetabe7.png', 'tabetabe8.png', 'tabetabe9.png'
]
SPREADSHEET_NAME = 'tabetabe-panel'
# ------------------------------------

app = Flask(__name__)
CORS(app)

# --- スプレッドシートへの接続 ---
try:
    creds_json_str = os.environ.get('GSPREAD_CREDENTIALS')
    creds_json = json.loads(creds_json_str)
    gc = gspread.service_account_from_dict(creds_json)
    spreadsheet = gc.open(SPREADSHEET_NAME)
    print("スプレッドシートへの接続に成功しました。")
except Exception as e:
    print(f"スプレッドシートへの接続に失敗しました: {e}")
    spreadsheet = None
# ------------------------------------

# --- APIエンドポイント ---

@app.route('/get_status')
def get_status():
    player_id = request.args.get('player', 'Player1')

    # --- [修正] Pingリクエストをここで処理 ---
    if player_id == 'ping':
        return jsonify({"status": "success", "message": "Server is awake."})
    # ------------------------------------

    if not spreadsheet:
        return jsonify({"status": "error", "message": "Spreadsheet not connected"}), 500

    try:
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
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/open_panel', methods=['POST'])
def open_panel():
    data = request.json
    user_id = data.get('user', 'Player1')
    row = data.get('row')
    col = data.get('col')
    try:
        worksheet = spreadsheet.worksheet(user_id)
        worksheet.update_cell(row, col, '1')
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin_open_panel', methods=['POST'])
def admin_open_panel():
    data = request.json
    user_id = data.get('user', 'Player1')
    row = data.get('row')
    col = data.get('col')
    try:
        worksheet = spreadsheet.worksheet(user_id)
        worksheet.update_cell(row, col, '2')
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/next_round', methods=['POST'])
def next_round():
    try:
        admin_sheet = spreadsheet.worksheet('AdminControl')
        current_round_str = admin_sheet.cell(1, 2).value
        current_round = int(current_round_str) if current_round_str and current_round_str.isdigit() else 0
        
        new_round = current_round + 1
        admin_sheet.update_cell(1, 2, str(new_round))

        if new_round > 9:
             return jsonify({"status": "success", "new_round": "clear"})

        presets_sheet = spreadsheet.worksheet('AdminPresets')
        n = new_round + 1
        
        start_row = sum(i for i in range(2, new_round + 1)) if new_round > 1 else 2
        start_col = sum(i + 1 for i in range(1, new_round)) + 1 if new_round > 1 else 1
        
        end_row = start_row + n - 1
        end_col = start_col + n - 1
        preset_range = f'{gspread.utils.rowcol_to_a1(start_row, start_col)}:{gspread.utils.rowcol_to_a1(end_row, end_col)}'
        preset_data = presets_sheet.get(preset_range)

        for i in range(1, 9):
            player_id = f'Player{i}'
            try:
                player_sheet = spreadsheet.worksheet(player_id)
                
                max_size = 10
                max_range = f'A1:{gspread.utils.rowcol_to_a1(max_size, max_size)}'
                
                # より確実なクリア処理
                clear_data = [[''] * max_size for _ in range(max_size)]
                player_sheet.update(max_range, clear_data, value_input_option='RAW')
                
                update_cells = []
                for r_idx, row_data in enumerate(preset_data):
                    for c_idx, cell_value in enumerate(row_data):
                        # 数値の1と文字の'1'の両方に対応
                        if str(cell_value) == '1':
                            cell = gspread.Cell(row=r_idx + 1, col=c_idx + 1, value='2')
                            update_cells.append(cell)

                if update_cells:
                    player_sheet.update_cells(update_cells, value_input_option='RAW')
            except gspread.WorksheetNotFound:
                continue
        
        return jsonify({"status": "success", "new_round": new_round})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/calculate_scores', methods=['GET'])
def calculate_scores():
    try:
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
                score = opened_count # スコア = 開いた枚数
                results.append({"player": player_id, "score": score, "opened": opened_count})
            except gspread.WorksheetNotFound:
                continue
        
        results.sort(key=lambda x: x['score'], reverse=True)
        
        results_sheet = spreadsheet.worksheet('Results')
        results_sheet.append_row([f"Round {current_round} Results"])
        for res in results:
            results_sheet.append_row([res['player'], res['score'], res['opened']])

        return jsonify({"status": "success", "results": results})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/reset_game', methods=['POST'])
def reset_game():
    try:
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
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

