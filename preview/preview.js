// DOM要素の取得
const sampleSelector = document.getElementById('sample-selector');
const contentElement = document.getElementById('content');
const displayInfo = document.getElementById('display-info');
const viewModeRadios = document.querySelectorAll('input[name="view-mode"]');
const deviceButtons = document.querySelectorAll('.device-btn');
const previewFrame = document.getElementById('preview-frame');

// 現在の表示状態
let currentSample = null;
let currentViewMode = 'preview';

// サンプルセレクタの変更イベント
sampleSelector.addEventListener('change', (e) => {
  const selectedValue = e.target.value;
  if (selectedValue && samples[selectedValue]) {
    currentSample = samples[selectedValue];
    updateContent();
    updateDisplayInfo();
  } else {
    contentElement.innerHTML = '<p>サンプルを選択してください</p>';
    displayInfo.innerHTML = '<p>サンプルを選択してください</p>';
  }
});

// 表示モードラジオボタンの変更イベント
viewModeRadios.forEach(radio => {
  radio.addEventListener('change', (e) => {
    currentViewMode = e.target.value;
    updateContent();
  });
});

// デバイス切り替えボタンのクリックイベント
deviceButtons.forEach(button => {
  button.addEventListener('click', (e) => {
    // 現在のアクティブクラスを削除
    deviceButtons.forEach(btn => btn.classList.remove('active'));
    
    // クリックされたボタンにアクティブクラスを追加
    const clickedButton = e.target;
    clickedButton.classList.add('active');
    
    // プレビューフレームのクラスを変更
    const deviceType = clickedButton.dataset.device;
    previewFrame.className = deviceType;
  });
});

// コンテンツ更新
function updateContent() {
  if (!currentSample) return;
  
  let content = '';
  
  switch (currentViewMode) {
    case 'preview':
      content = marked.parse(currentSample.markdown);
      break;
    case 'markdown':
      content = `<pre><code>${escapeHtml(currentSample.markdown)}</code></pre>`;
      break;
    case 'json':
      content = `<pre><code>${escapeHtml(JSON.stringify(currentSample.json, null, 2))}</code></pre>`;
      break;
  }
  
  contentElement.innerHTML = content;
  
  // KaTeX数式のレンダリング（プレビューモードの場合のみ）
  if (currentViewMode === 'preview') {
    renderMathInElement(contentElement, {
      delimiters: [
        {left: '$$', right: '$$', display: true},
        {left: '$', right: '$', display: false}
      ],
      throwOnError: false
    });
  }
}

// 表示情報の更新
function updateDisplayInfo() {
  if (!currentSample) return;
  
  displayInfo.innerHTML = `
    <h4>サンプル情報</h4>
    <p>${currentSample.info}</p>
    <h4>確認ポイント</h4>
    <ul>
      ${hasFormula(currentSample) ? '<li>数式表示</li>' : ''}
      ${hasTable(currentSample) ? '<li>表の表示</li>' : ''}
      ${hasImage(currentSample) ? '<li>画像表示</li>' : ''}
      ${hasComplexStructure(currentSample) ? '<li>複雑な構造</li>' : ''}
    </ul>
  `;
}

// サンプルに数式が含まれているかチェック
function hasFormula(sample) {
  return sample.markdown.includes('$') || 
         (sample.json && sample.json.problems.some(p => p.has_formula));
}

// サンプルに表が含まれているかチェック
function hasTable(sample) {
  return sample.markdown.includes('|') || 
         (sample.json && sample.json.problems.some(p => p.has_table));
}

// サンプルに画像が含まれているかチェック
function hasImage(sample) {
  return sample.markdown.includes('![') || 
         (sample.json && sample.json.problems.some(p => p.has_figure || p.has_circuit_diagram || p.has_multiple_figures));
}

// サンプルに複雑な構造が含まれているかチェック
function hasComplexStructure(sample) {
  return sample.markdown.includes('##') ||
         (sample.json && sample.json.problems.some(p => p.choices && p.choices.length > 0));
}

// HTML特殊文字をエスケープする関数
function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// 画像パスを修正するためのダミーイメージを表示
function setupDummyImages() {
  // イメージのsrc属性を監視し、見つからない場合はダミー画像を表示
  const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
      if (mutation.type === 'childList') {
        const images = contentElement.querySelectorAll('img');
        images.forEach(img => {
          img.onerror = function() {
            this.src = 'https://via.placeholder.com/400x300?text=仮想イメージ';
            this.onerror = null;
          };
        });
      }
    });
  });
  
  observer.observe(contentElement, { childList: true, subtree: true });
}

// ページ読み込み時の初期化
document.addEventListener('DOMContentLoaded', () => {
  setupDummyImages();
}); 