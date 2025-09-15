// APIサーバーのURL
// ▼▼▼▼▼【最終ステップで書き換える場所】▼▼▼▼▼
// Renderで公開したサーバーのURLをここに貼り付ける
const API_BASE_URL = 'https://panel-game-server.onrender.com'; // このURLはご自身のものに書き換えてください
// ▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲▲

let myPlayerId = 'Player1'; // デフォルトのプレイヤーID

// ページの読み込みが完了したら、ゲームの初期化を開始する
window.onload = function() {
    const urlParams = new URLSearchParams(window.location.search);
    myPlayerId = urlParams.get('player') || 'Player1'; // URLからプレイヤーIDを取得
    console.log(`ページが読み込まれました。${myPlayerId}としてゲームを初期化します。`);
    
    // Adminの時だけ管理者パネルを表示し、ボタンを有効化する
    if (myPlayerId === 'Admin') {
        const adminPanel = document.getElementById('admin-panel');
        if (adminPanel) {
            adminPanel.style.display = 'block';
            setupAdminControls();
        }
    }

    initializeGame();
};

// ゲームの初期化を行う関数
async function initializeGame() {
    try {
        const response = await fetch(`${API_BASE_URL}/get_status?player=${myPlayerId}`);
        const data = await response.json();

        if (data.status === 'success') {
            const round = data.round;
            const infoDisplay = document.getElementById('info-display');
            const gameBoard = document.getElementById('game-board');
            const scoreContainer = document.getElementById('score-container');

            // --- ▼▼▼ ラウンド0の処理を追加 ▼▼▼ ---
            if (round === 0) {
                if (infoDisplay) infoDisplay.textContent = 'ゲーム開始待機中...';
                if (gameBoard) gameBoard.style.display = 'none';
                if (scoreContainer) scoreContainer.style.display = 'none';
                
                // 管理者の場合、「次のラウンドへ」ボタンを「ゲーム開始」として表示
                if (myPlayerId === 'Admin') {
                    const nextRoundButton = document.getElementById('next-round-button');
                    if (nextRoundButton) nextRoundButton.textContent = 'ゲーム開始';
                }

            } else {
            // --- ▲▲▲ ここまで追加 ▲▲▲ ---
                const n = data.n;
                const panels = data.panels;
                const backgroundImage = data.backgroundImage;
                
                if (infoDisplay) {
                    infoDisplay.textContent = `ラウンド ${round} (${n}x${n})`;
                }
                if (gameBoard) gameBoard.style.display = 'grid'; // 表示を確実にする
                createGrid(n, panels, backgroundImage);
            }

        } else {
            document.getElementById('info-display').textContent = 'エラー：ゲーム情報の取得に失敗しました。';
        }
    } catch (error) {
        console.error('通信エラー:', error);
        document.getElementById('info-display').textContent = 'エラー：サーバーに接続できません。';
    }
}

/**
 * グリッドを生成する関数
 */
function createGrid(n, panels, backgroundImage) {
    const gameBoard = document.getElementById('game-board');
    if (!gameBoard) return;
    
    gameBoard.innerHTML = '';
    gameBoard.style.setProperty('--n', n);

    if (backgroundImage) {
        console.log(`[ブラウザ側の確認] 背景画像として'${backgroundImage}'を設定しようとしています。`);
        gameBoard.style.backgroundImage = `url('${backgroundImage}')`;
    } else {
        console.log('[ブラウザ側の確認] 背景画像の情報がサーバーから送られてきませんでした。');
        gameBoard.style.backgroundImage = 'none';
    }

    for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
            const panel = document.createElement('div');
            panel.classList.add('panel');

            if (panels && panels[r] && (panels[r][c] === '1' || panels[r][c] === '2')) {
                panel.classList.add('is-hidden');
            }

            panel.addEventListener('click', async () => {
                if (panel.classList.contains('is-hidden')) return;
                
                panel.classList.add('is-hidden');

                const isAdmin = document.getElementById('admin-mode-checkbox')?.checked;
                const endpoint = isAdmin ? '/admin_open_panel' : '/open_panel';
                
                console.log(`[ブラウザ側の確認] サーバーに送信するID: '${myPlayerId}'`);

                try {
                    await fetch(`${API_BASE_URL}${endpoint}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ user: myPlayerId, row: r + 1, col: c + 1 }),
                    });
                } catch (error) {
                    console.error('パネル開放リクエストで通信エラー:', error);
                }
            });
            gameBoard.appendChild(panel);
        }
    }
}

/**
 * 管理者用の操作パネルをセットアップする関数
 */
function setupAdminControls() {
    // --- ▼▼▼ リセットボタンの機能を追加 ▼▼▼ ---
    const resetGameButton = document.getElementById('reset-game-button');
    if (resetGameButton) {
        resetGameButton.addEventListener('click', async () => {
            // 確認ダイアログは挟まずに即時実行
            console.log('「ゲームをリセット」ボタンがクリックされました。');
            try {
                await fetch(`${API_BASE_URL}/reset_game`, { method: 'POST' });
                window.location.reload();
            } catch (error) {
                console.error('ゲームリセットで通信エラー:', error);
            }
        });
    }
    // --- ▲▲▲ ここまで追加 ▲▲▲ ---

    const nextRoundButton = document.getElementById('next-round-button');
    if (nextRoundButton) {
        nextRoundButton.addEventListener('click', async () => {
            console.log('「次のラウンドへ」ボタンがクリックされました。');
            try {
                await fetch(`${API_BASE_URL}/next_round`, { method: 'POST' });
                // 自分の画面だけリロードする
                window.location.reload();
            } catch (error) {
                console.error('次のラウンドへの移行で通信エラー:', error);
            }
        });
    }

    const calculateScoreButton = document.getElementById('calculate-score-button');
    if (calculateScoreButton) {
        calculateScoreButton.addEventListener('click', () => {
            console.log('「スコアを計算」ボタンがクリックされました。');
            displayScores();
        });
    }
}

/**
 * スコアを計算して表示する関数
 */
async function displayScores() {
    try {
        const response = await fetch(`${API_BASE_URL}/calculate_scores`);
        const data = await response.json();

        if (data.status === 'success') {
            const gameBoard = document.getElementById('game-board');
            const scoreContainer = document.getElementById('score-container');
            const adminPanel = document.getElementById('admin-panel');

            if (gameBoard) gameBoard.style.display = 'none';
            if (adminPanel) adminPanel.style.display = 'none'; 

            if (scoreContainer) {
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
                    <tbody>
                    </tbody>
                `;
                const tbody = table.querySelector('tbody');
                data.results.forEach((result, index) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${index + 1}</td>
                        <td>${result.player}</td>
                        <td>${result.score}</td>
                        <td>${result.opened}</td>
                    `;
                    tbody.appendChild(row);
                });
                scoreContainer.appendChild(table);
                
                if (myPlayerId === 'Admin') {
                    const nextRoundBtnOnScore = document.createElement('button');
                    nextRoundBtnOnScore.textContent = '次のラウンドへ';
                    nextRoundBtnOnScore.style.marginTop = '20px';
                    nextRoundBtnOnScore.style.padding = '10px 20px';
                    nextRoundBtnOnScore.style.fontSize = '1.1em';

                    nextRoundBtnOnScore.addEventListener('click', async () => {
                         try {
                            await fetch(`${API_BASE_URL}/next_round`, { method: 'POST' });
                            window.location.reload();
                        } catch (error) {
                            console.error('スコア画面からの次のラウンドへの移行で通信エラー:', error);
                        }
                    });
                    scoreContainer.appendChild(nextRoundBtnOnScore);
                }
                
                scoreContainer.style.display = 'block';
            }
        }
    } catch (error) {
        console.error('スコア計算で通信エラー:', error);
    }
}

