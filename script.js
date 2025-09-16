// --- サーバー設定 ---
const API_BASE_URL = 'https://panel-game-server.onrender.com';

// --- グローバル変数 ---
let myPlayerId = 'Player1'; // デフォルト

// --- サーバーをスリープさせないための機能 ---
function keepServerAwake() {
    fetch(`${API_BASE_URL}/get_status?player=ping`)
        .then(response => {
            if (!response.ok) {
                console.warn('サーバーへのPingに失敗しました。');
            }
        })
        .catch(error => console.warn('サーバーへのPingでエラー:', error));
}
setInterval(keepServerAwake, 30 * 1000); // 30秒ごとに実行

// --- 初期化処理 ---
window.onload = function() {
    // URLからプレイヤーIDを取得
    const params = new URLSearchParams(window.location.search);
    myPlayerId = params.get('player') || 'Player1';
    
    console.log(`ページが読み込まれました。${myPlayerId}としてゲームを初期化します。`);
    
    setupAdminControls();
    initializeGame();
};

// --- メインのゲームロジック ---
async function initializeGame() {
    try {
        const response = await fetch(`${API_BASE_URL}/get_status?player=${myPlayerId}`);
        if (!response.ok) {
            throw new Error(`Server responded with status ${response.status}`);
        }
        const data = await response.json();

        if (data.status === 'success') {
            if (data.round === 'clear') {
                // --- [新機能] ゲームクリア時に最終スコアを表示 ---
                showFinalResults();
                return;
            }
            if (data.round === 0) {
                showStandbyScreen();
                return;
            }
            
            const { round, n, panels, backgroundImage } = data;
            document.getElementById('info-display').textContent = `ラウンド ${round} (${n}x${n})`;
            createGrid(n, panels, backgroundImage);

        } else {
            showErrorScreen(`ゲーム情報の取得に失敗しました。`);
        }
    } catch (error) {
        console.error('初期化エラー:', error);
        showErrorScreen(error.message);
    }
}

// --- 画面表示関連 ---

function createGrid(n, panels, backgroundImage) {
    const gameBoard = document.getElementById('game-board');
    const scoreContainer = document.getElementById('score-container');
    gameBoard.innerHTML = '';
    gameBoard.style.display = 'grid';
    scoreContainer.style.display = 'none';

    // --- [改善] 背景画像の設定 ---
    if (backgroundImage) {
        // 画像への完全なパスを生成
        const imageUrl = new URL(backgroundImage, window.location.href).href;
        gameBoard.style.backgroundImage = `url('${imageUrl}')`;
        console.log(`[ブラウザ側の確認] 背景画像として'${backgroundImage}'を設定しようとしています。`);
    } else {
        gameBoard.style.backgroundImage = 'none';
    }
    gameBoard.style.setProperty('--n', n);

    for (let r = 0; r < n; r++) {
        for (let c = 0; c < n; c++) {
            const panel = document.createElement('div');
            panel.classList.add('panel');

            if (panels[r] && (panels[r][c] === '1' || panels[r][c] === '2')) {
                panel.classList.add('is-hidden');
            }

            panel.addEventListener('click', () => onPanelClick(panel, r, c));
            gameBoard.appendChild(panel);
        }
    }
}

function displayScores(results) {
    const gameBoard = document.getElementById('game-board');
    const scoreContainer = document.getElementById('score-container');
    gameBoard.style.display = 'none';
    scoreContainer.style.display = 'block';

    let html = '<h2>スコアランキング</h2><ol>';
    results.forEach(result => {
        html += `<li>${result.player}: ${result.score} 点 (開いた枚数: ${result.opened})</li>`;
    });
    html += '</ol>';
    
    if (myPlayerId === 'Admin') {
         html += '<button id="next-round-in-score" class="admin-button">次のラウンドへ</button>';
    }

    scoreContainer.innerHTML = html;
    
    if (myPlayerId === 'Admin') {
        const nextBtn = document.getElementById('next-round-in-score');
        if (nextBtn) {
            nextBtn.onclick = () => onNextRoundClick();
        }
    }
}

function showStandbyScreen() {
    document.getElementById('info-display').textContent = 'ゲーム開始待機中...';
    document.getElementById('game-board').style.display = 'none';
    document.getElementById('score-container').style.display = 'none';
}

function showErrorScreen(message) {
    document.getElementById('info-display').textContent = `エラー: ${message}`;
    document.getElementById('game-board').style.display = 'none';
    document.getElementById('score-container').style.display = 'none';
}

// --- [新機能] 最終結果を表示する画面 ---
async function showFinalResults() {
    const gameBoard = document.getElementById('game-board');
    const scoreContainer = document.getElementById('score-container');
    gameBoard.style.display = 'none';
    scoreContainer.style.display = 'block';
    
    document.getElementById('info-display').textContent = 'ゲームクリア！お疲れ様でした！';
    scoreContainer.innerHTML = '<h2>最終結果を集計中...</h2>';

    try {
        const response = await fetch(`${API_BASE_URL}/get_final_scores`);
        const data = await response.json();

        if (data.status === 'success') {
            let html = '<h2>最終総合ランキング</h2><ol>';
            data.results.forEach(result => {
                html += `<li>${result.player}: ${result.score} 点</li>`;
            });
            html += '</ol>';
            scoreContainer.innerHTML = html;
        } else {
            scoreContainer.innerHTML = '<h2>最終結果の取得に失敗しました。</h2>';
        }
    } catch (error) {
        console.error('最終結果の取得エラー:', error);
        scoreContainer.innerHTML = '<h2>最終結果の取得中にエラーが発生しました。</h2>';
    }
}

// --- イベントハンドラ ---

async function onPanelClick(panel, r, c) {
    if (panel.classList.contains('is-hidden')) return;

    panel.classList.add('is-hidden');

    const isAdminMode = document.getElementById('admin-mode-check')?.checked;
    const endpoint = isAdminMode ? '/admin_open_panel' : '/open_panel';

    try {
        await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user: myPlayerId,
                row: r + 1,
                col: c + 1,
            }),
        });
    } catch (error) {
        console.error('通信エラー:', error);
    }
}

async function onNextRoundClick() {
    try {
        await fetch(`${API_BASE_URL}/next_round`, { method: 'POST' });
        window.location.reload();
    } catch (error) {
        console.error('次のラウンドへの移行に失敗:', error);
    }
}

async function onCalcScoreClick() {
    try {
        const response = await fetch(`${API_BASE_URL}/calculate_scores`);
        const data = await response.json();
        if (data.status === 'success') {
            displayScores(data.results);
        } else {
            showErrorScreen('スコア計算に失敗しました。');
        }
    } catch (error) {
        console.error('スコア計算中にエラー:', error);
    }
}

async function onResetGameClick() {
    try {
        await fetch(`${API_BASE_URL}/reset_game`, { method: 'POST' });
        window.location.reload();
    } catch (error) {
        console.error('ゲームのリセットに失敗:', error);
    }
}


// --- 管理者用機能 ---
function setupAdminControls() {
    const adminPanel = document.getElementById('admin-panel');
    if (myPlayerId === 'Admin') {
        adminPanel.style.display = 'block';

        const nextBtn = document.getElementById('next-round-button');
        const calcBtn = document.getElementById('calc-score-button');
        const resetBtn = document.getElementById('reset-game-button');

        if(nextBtn) nextBtn.onclick = () => onNextRoundClick();
        if(calcBtn) calcBtn.onclick = () => onCalcScoreClick();
        if(resetBtn) resetBtn.onclick = () => onResetGameClick();
        
    } else {
        adminPanel.style.display = 'none';
    }
}

