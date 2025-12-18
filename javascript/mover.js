onUiLoaded(async () => {
    // UIを移動させる関数
    const movePanel = (tabName) => {
        // Python側で決めたID
        const sourceId = `advanced_styles_wrapper_${tabName}`;
        // コンテナのID (これに追加すれば必ず最下部に縦並びになる)
        const targetId = `${tabName}_prompt_container`;

        const source = document.getElementById(sourceId);
        const target = document.getElementById(targetId);

        // 要素が存在し、まだ移動していない場合に実行
        if (source && target && source.parentNode !== target) {
            // appendChildを使うことで、コンテナ内の最後尾（ネガティブプロンプトの下）に追加される
            target.appendChild(source);
        }
    };

    // txt2img と img2img それぞれで移動を実行
    movePanel("txt2img");
    movePanel("img2img");
});

function startSmartObserver() {
    const PANEL_ID = "advanced_styles_wrapper";

    const runMover = () => {
        const myPanel = document.getElementById(PANEL_ID);
        if (!myPanel) return;

        // 既に移動済み（コンテナ内にいる）なら何もしない
        if (myPanel.parentNode && myPanel.parentNode.id.includes("prompt_container")) {
            return; 
        }

        // --- 移動先検索 ---
        let targetRow = null;
        
        // 1. ID検索
        const rowIds = [
            "txt2img_neg_prompt_row",
            "img2img_neg_prompt_row",
            "txt2img_negative_prompt_row",
            "img2img_negative_prompt_row"
        ];
        for (const id of rowIds) {
            const el = document.getElementById(id);
            if (el && el.offsetParent !== null) {
                targetRow = el;
                break;
            }
        }

        // 2. テキスト検索
        if (!targetRow) {
            const all = document.querySelectorAll("span, label, p, div");
            const words = ["Negative prompt", "ネガティブプロンプト"];
            for (const el of all) {
                if (el.offsetParent !== null && words.includes(el.textContent.trim())) {
                    let cand = el.closest(".row") || el.closest(".form");
                    if (cand) {
                        targetRow = cand;
                        break;
                    }
                }
            }
        }

        // --- 移動実行 ---
        if (targetRow && targetRow.parentNode) {
            if (targetRow.nextSibling !== myPanel) {
                targetRow.parentNode.insertBefore(myPanel, targetRow.nextSibling);
            }
        }
    };

    // 初回実行
    runMover();

    // 監視設定
    const observer = new MutationObserver((mutations) => {
        let shouldCheck = false;
        for (const m of mutations) {
            if (m.addedNodes.length > 0) {
                shouldCheck = true;
                break;
            }
        }
        if (shouldCheck) {
            runMover();
        }
    });

    const app = document.querySelector("gradio-app") || document.body;
    observer.observe(app, { childList: true, subtree: true });
}