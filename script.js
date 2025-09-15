// --- 設定 ---
// Renderで公開したサーバーのURLをここに貼り付ける
const API_BASE_URL = 'https://panel-game-server.onrender.com'; 
// ------------------------------------

// グローバル変数としてプレイヤーIDを保持
let myPlayerId = 'Player1';

// ページの読み込みが完了したら、ゲームの初期化を開始する
window.onload = function() {
    // URLからプレイヤーIDを取得する
    const params = new URLSearchParams(window.location.search);
    const player = params.get('player');
    if (player) {
        myPlayerId = player;
    }
    console.log(`ページが読み込まれました。${myPlayerId}としてゲームを初期化します。`);
    initializeGame();
};

// ゲームの初期化を行う非同期関数
async function initializeGame() {
    const infoDisplay = document.getElementById('info-display');
    const gameBoard = document.getElementById('game-board');
    const adminPanel = document.getElementById('admin-panel');
    const scoreContainer = document.getElementById('score-container');

    // 表示をリセット
    gameBoard.style.display = 'grid';
    scoreContainer.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE_URL}/get_status?player=${myPlayerId}`);
        if (!response.ok) {
            throw new Error(`Server responded with status ${response.status}`);
        }
        const data = await response.json();

        if (data.status === 'success') {
            if (data.round === 0) {
                infoDisplay.textContent = 'ゲーム開始待機中...';
                gameBoard.style.display = 'none';
            } else if (data.round === 'clear') {
                infoDisplay.textContent = 'ゲームクリア！お疲れ様でした！';
                gameBoard.style.display = 'none';
                scoreContainer.style.display = 'none';
                adminPanel.style.display = myPlayerId === 'Admin' ? 'flex' : 'none'; // 管理者には操作パネルを表示
            } else {
                const { round, n, panels, backgroundImage } = data;
                infoDisplay.textContent = `ラウンド ${round} (${n}x${n})`;
                
                // --- 背景画像を設定 ---
                if (backgroundImage) {
                     console.log(`[ブラウザ側の確認] 背景画像として'${backgroundImage}'を設定しようとしています。`);
                    gameBoard.style.backgroundImage = `url('${backgroundImage}')`;
                }
                
                createGrid(n, panels);
            }
        } else {
            throw new Error(data.message || 'ゲーム情報の取得に失敗しました。');
        }
    } catch (error) {
        console.error('通信エラー:', error);
        infoDisplay.textContent = `エラー: ${error.message}`;
        gameBoard.style.display = 'none';
    }

    // 管理者パネルの表示制御とイベントリスナーの設定
    setupAdminControls();
}

/**
 * グリッド（ゲーム盤）を生成する関数
 * @param {number} n - グリッドのサイズ (n x n)
 * @param {Array<Array<string>>} panels - パネルの状態を保持する2次元配列
 */
function createGrid(n, panels) {
    const gameBoard = document.getElementById('game-board');
    gameBoard.innerHTML = '';
    gameBoard.style.setProperty('--n', n);

    if (!panels || panels.length === 0) {
        console.error("サーバーから有効なパネルデータを受け取れませんでした。");
        return;
    }

    for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
            const panel = document.createElement('div');
            panel.classList.add('panel');

            if (panels[r] && (panels[r][c] === '1' || panels[r][c] === '2')) {
                panel.classList.add('is-hidden');
            }

            panel.addEventListener('click', () => {
                handlePanelClick(panel, r, c);
            });

            gameBoard.appendChild(panel);
        }
    }
}

/**
 * パネルがクリックされたときの処理
 * @param {HTMLElement} panel - クリックされたパネル要素
 * @param {number} r - 行番号 (0から)
 * @param {number} c - 列番号 (0から)
 */
async function handlePanelClick(panel, r, c) {
    if (panel.classList.contains('is-hidden') || myPlayerId === 'Admin') {
        const isAdminMode = document.getElementById('admin-mode-checkbox')?.checked;
        if (myPlayerId !== 'Admin' || !isAdminMode) {
             return; // 通常プレイヤーまたは管理者モードOFFなら何もしない
        }
    }

    panel.classList.add('is-hidden');

    const isAdminMode = document.getElementById('admin-mode-checkbox')?.checked;
    const endpoint = (myPlayerId === 'Admin' && isAdminMode) ? '/admin_open_panel' : '/open_panel';
    
    console.log(`[ブラウザ側の確認] サーバーに送信するID: '${myPlayerId}'`);

    try {
        await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user: myPlayerId, row: r + 1, col: c + 1 }),
        });
    } catch (error) {
        console.error('通信エラー:', error);
        panel.classList.remove('is-hidden'); // エラーが起きたらパネルを元に戻す
    }
}


/**
 * 管理者用コントロールのセットアップ
 */
function setupAdminControls() {
    const adminPanel = document.getElementById('admin-panel');
    if (myPlayerId === 'Admin') {
        adminPanel.style.display = 'flex';

        const nextRoundBtn = document.getElementById('next-round-button');
        const calcScoreBtn = document.getElementById('calc-score-button');
        const resetBtn = document.getElementById('reset-game-button');

        if (nextRoundBtn) {
            nextRoundBtn.onclick = async () => {
                await fetch(`${API_BASE_URL}/next_round`, { method: 'POST' });
                window.location.reload();
            };
        }
        if (calcScoreBtn) {
            calcScoreBtn.onclick = async () => {
                const response = await fetch(`${API_BASE_URL}/calculate_scores`);
                const data = await response.json();
                if (data.status === 'success') {
                    displayScores(data.results);
                }
            };
        }
        if (resetBtn) {
            resetBtn.onclick = async () => {
                if (confirm("本当にゲーム全体をリセットしますか？")) {
                    await fetch(`${API_BASE_URL}/reset_game`, { method: 'POST' });
                    window.location.reload();
                }
            };
        }
    } else {
        adminPanel.style.display = 'none';
    }
}

/**
 * スコアを画面に表示する関数
 * @param {Array<Object>} results - サーバーから受け取った結果の配列
 */
function displayScores(results) {
    const gameBoard = document.getElementById('game-board');
    const scoreContainer = document.getElementById('score-container');
    const adminPanel = document.getElementById('admin-panel');

    gameBoard.style.display = 'none';
    adminPanel.style.display = 'none';
    scoreContainer.style.display = 'block';
    scoreContainer.innerHTML = '<h2>スコアランキング</h2>';

    const table = document.createElement('table');
    table.innerHTML = `
        <thead>
            <tr>
                <th>順位</th>
                <th>プレイヤー</th>
                <th>スコア</th>
                <th>開いた枚数</th>
            </tr>
        </thead>
    `;
    const tbody = document.createElement('tbody');
    results.forEach((res, index) => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${index + 1}</td>
            <td>${res.player}</td>
            <td>${res.score}</td>
            <td>${res.opened}</td>
        `;
        tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    scoreContainer.appendChild(table);

    // 管理者の場合のみ「次のラウンドへ」ボタンを追加
    if (myPlayerId === 'Admin') {
        const nextRoundBtn = document.createElement('button');
        nextRoundBtn.id = 'next-round-button-in-score';
        nextRoundBtn.textContent = '次のラウンドへ';
        nextRoundBtn.onclick = async () => {
            await fetch(`${API_BASE_URL}/next_round`, { method: 'POST' });
            window.location.reload();
        };
        scoreContainer.appendChild(nextRoundBtn);
    }
}

