import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
import gspread
import traceback
import time

# --- 画像とスプレッドシートの設定 ---
ROUND_IMAGES = [
    'tabetabe1.png', 'tabetabe2.png', 'tabetabe3.png',
    'tabetabe4.png', 'tabetabe5.png', 'tabetabe6.png',
    'tabetabe7.png', 'tabetabe8.png', 'tabetabe9.png'
]
SPREADSHEET_NAME = 'tabetabe-panel'

# --- AdminPresetsシートの読み取り範囲を直接指定 ---
PRESET_RANGES = [
    'A2:B3',    # Round 1 (2x2)
    'C2:E4',    # Round 2 (3x3)
    'F2:I5',    # Round 3 (4x4)
    'J2:N6',    # Round 4 (5x5)
    'O2:T7',    # Round 5 (6x6)
    'U2:AA8',   # Round 6 (7x7)
    'AB2:AI9',  # Round 7 (8x8)
    'AJ2:AR10', # Round 8 (9x9)
    'AS2:BB11'  # Round 9 (10x10)
]
# ----------------------------------------------------

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
    if player_id == 'ping':
        return jsonify({"status": "success", "message": "Server is awake."})

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
    row = data.get('row')
    col = data.get('col')
    try:
        worksheet = spreadsheet.worksheet('Player1')
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
                score = abs(unopened_count - opened_count)
                
                results.append({"player": player_id, "score": score, "opened": opened_count})
            except gspread.WorksheetNotFound:
                continue
        
        results.sort(key=lambda x: x['score'])
        
        results_sheet = spreadsheet.worksheet('Results')
        results_sheet.append_row([f"Round {current_round} Results"])
        for res in results:
            results_sheet.append_row([res['player'], res['score'], res['opened']])

        return jsonify({"status": "success", "results": results})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/get_final_scores', methods=['GET'])
def get_final_scores():
    try:
        results_sheet = spreadsheet.worksheet('Results')
        
        # --- [新機能] SUMIF関数で合計スコアをスプレッドシートに計算させる ---
        # 1. 計算用のラベルとプレイヤーIDを書き込む (例: E列とF列)
        summary_labels = [['Player', 'Total Score']]
        player_ids = [[f'Player{i}'] for i in range(1, 9)]
        results_sheet.update('E1', summary_labels)
        results_sheet.update('E2', player_ids)

        # 2. SUMIF関数を書き込む (B列のプレイヤーIDがE列と一致したらC列のスコアを合計)
        formulas = [[f'=SUMIF(B:B, E{i+2}, C:C)'] for i in range(8)]
        results_sheet.update('F2', formulas, value_input_option='USER_ENTERED')
        
        # 3. Google Sheetsが計算するのを少し待つ
        time.sleep(1) 

        # 4. 計算結果を読み取る
        calculated_scores = results_sheet.get('F2:F9', value_render_option='UNFORMATTED_VALUE')

        final_results = []
        for i in range(8):
            player_id = f'Player{i+1}'
            try:
                # calculated_scoresは [['123'], ['456']] のようなリストのリスト
                score = int(calculated_scores[i][0]) if i < len(calculated_scores) and calculated_scores[i] else 0
            except (ValueError, IndexError):
                score = 0
            final_results.append({'player': player_id, 'score': score})
        # -----------------------------------------------------------------
            
        final_results.sort(key=lambda x: x['score'])

        return jsonify({"status": "success", "results": final_results})

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

