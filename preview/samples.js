// サンプルデータ
const samples = {
  // サンプル1：電気回路問題（ジュール熱の計算）
  sample1: {
    markdown: `# 令和4年度試験問題と解説
## 午前の部

※ 問題番号【No. 1】から【No. 15】までは，15 問題のうちから 10 問題を選択し，解答してください。

---

【問題 No. 1】 $2 \\, \\Omega$ の抵抗に $10 \\, \\mathrm{V}$ の電圧を 1 分間加えたとき，この抵抗に発生する熱量として，正しいものはどれか。

## 1. $20 \\, \\mathrm{J}$
## 2. $50 \\, \\mathrm{J}$
## 3. $1,200 \\, \\mathrm{J}$
## 4. $3,000 \\, \\mathrm{J}$

---

【解 説】
抵抗に電気を流した時に発生する熱量をジュール熱といい，ジュールの法則により，「抵抗に流れる電流によって毎秒発生する熱量は，電流の 2 乗と抵抗の積に比例する。」ことから，熱量 $Q$ [J]，抵抗 $R$ [$\\Omega$]，電圧 $V$ [V]，電流 $I$ [A]，時間 $t$ [秒] とすれば，ジュール熱は以下の式で表すことができる。
$$ Q = VIt = RI^2t \\quad [\\mathrm{J}] $$
抵抗に流れる電流 $I$ [A] は，$I = \\frac{V}{R} = \\frac{10}{2} = 5 \\, \\mathrm{A}$
$$ Q = 2 \\times 5^2 \\times 60 = 3,000 \\, \\mathrm{J} $$
したがって，4 が正しいものである。`,

    json: {
      problems: [
        {
          id: 1,
          question: "$2 \\, \\Omega$ の抵抗に $10 \\, \\mathrm{V}$ の電圧を 1 分間加えたとき，この抵抗に発生する熱量として，正しいものはどれか。",
          choices: [
            {
              number: 1,
              text: "$20 \\, \\mathrm{J}$"
            },
            {
              number: 2,
              text: "$50 \\, \\mathrm{J}$"
            },
            {
              number: 3,
              text: "$1,200 \\, \\mathrm{J}$"
            },
            {
              number: 4,
              text: "$3,000 \\, \\mathrm{J}$"
            }
          ],
          explanation: "抵抗に電気を流した時に発生する熱量をジュール熱といい，ジュールの法則により，「抵抗に流れる電流によって毎秒発生する熱量は，電流の 2 乗と抵抗の積に比例する。」ことから，熱量 $Q$ [J]，抵抗 $R$ [$\\Omega$]，電圧 $V$ [V]，電流 $I$ [A]，時間 $t$ [秒] とすれば，ジュール熱は以下の式で表すことができる。$Q = VIt = RI^2t \\quad [\\mathrm{J}]$",
          correct_answer: 4,
          has_formula: true,
          year: "令和4年度",
          subject: "電気回路",
          embedding_file: "令和4年度_sample_page_001_embedding.npy"
        }
      ]
    },
    info: "このサンプルには複雑な数式表現があります。特に分数や2乗、単位などの表示を確認してください。"
  },
  
  // サンプル2：力率改善問題
  sample2: {
    markdown: `令和4年度（午前の部）

### 【問題 No.11】
配電線路に 600 kW, 遅れ力率 80 % の三相負荷があるとき，電力用コンデンサを負荷と並列に接続して力率を 100 % に改善するために必要なコンデンサ容量 [kvar] として，正しいものはどれか。

## 1. 360 kvar
## 2. 450 kvar
## 3. 480 kvar
## 4. 800 kvar

### 【解説】
配電線路の有効電力と力率改善に要するコンデンサ容量の関係を表すと，次のベクトル図のようになる。
![図: 有効電力とコンデンサ容量の関係を示すベクトル図](../images/令和4年度_sample_page_002_figure_1.png)
図 有効電力とコンデンサ容量の関係 $^1)$
この図により，力率改善に必要なコンデンサ容量 $Q_c$ [kvar] は，以下の式で表すことができる。
$Q_c = Q_1 - Q_2 = P \\tan \\theta_1 - P \\tan \\theta_2$ [kvar]
三角関数の公式より，
$\\sin^2 \\theta + \\cos^2 \\theta = 1$, $\\tan \\theta = \\frac{\\sin \\theta}{\\cos \\theta}$
であるので，
$Q_c = P \\times \\left( \\frac{\\sqrt{1-\\cos^2 \\theta_1}}{\\cos \\theta_1} - \\frac{\\sqrt{1-\\cos^2 \\theta_2}}{\\cos \\theta_2} \\right)$ [kvar]`,

    json: {
      problems: [
        {
          id: 11,
          question: "配電線路に 600 kW, 遅れ力率 80 % の三相負荷があるとき，電力用コンデンサを負荷と並列に接続して力率を 100 % に改善するために必要なコンデンサ容量 [kvar] として，正しいものはどれか。",
          choices: [
            {
              number: 1,
              text: "360 kvar"
            },
            {
              number: 2,
              text: "450 kvar"
            },
            {
              number: 3,
              text: "480 kvar"
            },
            {
              number: 4,
              text: "800 kvar"
            }
          ],
          has_figure: true,
          figure_description: "有効電力とコンデンサ容量の関係を示すベクトル図。P, Q1, Q2, Qc, θ1, θ2 が示されている",
          correct_answer: 2,
          year: "令和4年度",
          subject: "電力システム",
          embedding_file: "令和4年度_sample_page_002_embedding.npy"
        }
      ]
    },
    info: "このサンプルには図表と複雑な数式（分数、平方根、三角関数）が含まれています。"
  },
  
  // サンプル3：送電線のたるみ計算問題（表を含む）
  sample3: {
    markdown: `# 令和4年度（午前の部）

### 【問題 No.21】
架空送電線における支持点間の電線のたるみの近似値 D [m] 及び電線の実長の近似値 L [m] を求める式の組合せとして，適当なものはどれか。
ただし，各記号は次のとおりとし，電線支持点の高低差はないものとする。
- S : 径間 [m]
- T : 電線の最低点の水平張力 [N]
- W : 電線の単位長さ当たりの重量 [N/m]

|       | たるみ                     | 実長                       |
| :---- | :------------------------- | :------------------------- |
| 1.    | $D = \\frac{WS^2}{3T}$      | $L = S + \\frac{8D^2}{3S}$  |
| 2.    | $D = \\frac{WS^2}{8T}$      | $L = S + \\frac{3D^2}{8S}$  |
| 3.    | $D = \\frac{WS^2}{3T}$      | $L = S + \\frac{3D^2}{8S}$  |
| 4.    | $D = \\frac{WS^2}{8T}$      | $L = S + \\frac{8D^2}{3S}$  |

### 【解 説】
図に示す電線支持点 AB において，高低差がない径間の電線の実長を求めるには，まず，電線のたるみ D [m] を求める。
たるみの近似値 D を求める式は，
- W : 単位長さ当たりの電線の重量 [N/m]
- S : 径間 [m]
- T : 最低点 M の電線の水平張力 [N]
とすると，
$D = \\frac{WS^2}{8T}$ [m]`,

    json: {
      problems: [
        {
          id: 21,
          question: "架空送電線における支持点間の電線のたるみの近似値 D [m] 及び電線の実長の近似値 L [m] を求める式の組合せとして，適当なものはどれか。",
          has_table: true,
          table_content: [
            ["", "たるみ", "実長"],
            ["1.", "D = WS²/3T", "L = S + 8D²/3S"],
            ["2.", "D = WS²/8T", "L = S + 3D²/8S"],
            ["3.", "D = WS²/3T", "L = S + 3D²/8S"],
            ["4.", "D = WS²/8T", "L = S + 8D²/3S"]
          ],
          correct_answer: 4,
          year: "令和4年度",
          subject: "送電工学",
          embedding_file: "令和4年度_sample_page_003_embedding.npy"
        }
      ]
    },
    info: "このサンプルにはMarkdownの表形式と表内の数式が含まれています。表のレスポンシブ表示を確認してください。"
  },
  
  // サンプル5：RC回路応答問題（微分方程式と図表）
  sample5: {
    markdown: `# 令和4年度（午前の部）

## 【問題 No.44】
図に示す回路において，スイッチ S を時刻 $t = 0$ で閉じるとき，$t > 0$ における電荷 $q$ の満たす微分方程式として，正しいものはどれか。
ただし，コンデンサ $C$ の初期電荷は零であり，また，抵抗 $r$ とコイル $L$ の抵抗は零とする。

![図：直列RLC回路](../images/令和4年度_sample_page_005_figure_1.png)

## 1. $L\\frac{d^2q}{dt^2} + r\\frac{dq}{dt} + \\frac{1}{C}q = E$
## 2. $L\\frac{d^2q}{dt^2} + R\\frac{dq}{dt} + \\frac{1}{C}q = E$
## 3. $L\\frac{dq}{dt} + (R+r)\\frac{dq}{dt} + \\frac{1}{C}q = E$
## 4. $L\\frac{d^2q}{dt^2} + (R+r)\\frac{dq}{dt} + \\frac{1}{C}q = E$`,

    json: {
      problems: [
        {
          id: 44,
          question: "図に示す回路において，スイッチ S を時刻 $t = 0$ で閉じるとき，$t > 0$ における電荷 $q$ の満たす微分方程式として，正しいものはどれか。",
          has_circuit_diagram: true,
          circuit_description: "直列RLC回路",
          choices: [
            {
              number: 1,
              text: "$L\\frac{d^2q}{dt^2} + r\\frac{dq}{dt} + \\frac{1}{C}q = E$"
            },
            {
              number: 2,
              text: "$L\\frac{d^2q}{dt^2} + R\\frac{dq}{dt} + \\frac{1}{C}q = E$"
            },
            {
              number: 3,
              text: "$L\\frac{dq}{dt} + (R+r)\\frac{dq}{dt} + \\frac{1}{C}q = E$"
            },
            {
              number: 4,
              text: "$L\\frac{d^2q}{dt^2} + (R+r)\\frac{dq}{dt} + \\frac{1}{C}q = E$"
            }
          ],
          correct_answer: 4,
          year: "令和4年度",
          subject: "電気回路",
          embedding_file: "令和4年度_sample_page_005_embedding.npy"
        }
      ]
    },
    info: "このサンプルには非常に複雑な数式（微分方程式）が含まれています。分数や微分表現の表示を確認してください。"
  },
  
  // サンプル9：機械力学問題（連立方程式と複数図表）
  sample9: {
    markdown: `# 令和4年度（午後の部）

## 【問題 No.83】
図1 のような装置の固有振動モードについて考える。質量 $m_1$, $m_2$ を質量のない棒と軸で連結し，軸回りに回転運動できるようにしている。$m_1$, $m_2$ と棒との距離をそれぞれ $l_1$, $l_2$ とする。ばね定数 $k$ のばねが図1 のように配置されている。図2のような $\\theta_1$, $\\theta_2$ を変位としたとき，装置の運動方程式は式(1)のように表される。
$m_1 l_1^2 \\ddot{\\theta_1} + kl_1 \\theta_1 = 0$ ・・・(1-1)
$m_2 l_2^2 \\ddot{\\theta_2} + kl_2 \\theta_2 = 0$ ・・・(1-2)

![図1](../images/令和4年度_sample_page_009_figure_1.png)
![図2](../images/令和4年度_sample_page_009_figure_2.png)

この装置の固有振動モードの振動数のうち，小さい方の振動数 $f$ [Hz] を求める式として，正しいものはどれか。
ただし，$m_1 = 6$ [kg]，$m_2 = 3$ [kg]，$l_1 = 0.15$ [m]，$l_2 = 0.30$ [m]，$k = 1.5 \\times 10^3$ [N/m] とする。

## 1. $f = \\frac{1}{2\\pi}\\sqrt{\\frac{k}{m_1 l_1}}$ [Hz]
## 2. $f = \\frac{1}{2\\pi}\\sqrt{\\frac{k}{m_2 l_2}}$ [Hz]
## 3. $f = \\frac{1}{2\\pi}\\sqrt{\\frac{k}{m_1 l_1^2}}$ [Hz]
## 4. $f = \\frac{1}{2\\pi}\\sqrt{\\frac{k}{m_2 l_2^2}}$ [Hz]`,

    json: {
      problems: [
        {
          id: 83,
          question: "図1 のような装置の固有振動モードについて考える。質量 $m_1$, $m_2$ を質量のない棒と軸で連結し，軸回りに回転運動できるようにしている。$m_1$, $m_2$ と棒との距離をそれぞれ $l_1$, $l_2$ とする。ばね定数 $k$ のばねが図1 のように配置されている。図2のような $\\theta_1$, $\\theta_2$ を変位としたとき，装置の運動方程式は式(1)のように表される。",
          equations: [
            "$m_1 l_1^2 \\ddot{\\theta_1} + kl_1 \\theta_1 = 0$ ・・・(1-1)",
            "$m_2 l_2^2 \\ddot{\\theta_2} + kl_2 \\theta_2 = 0$ ・・・(1-2)"
          ],
          has_multiple_figures: true,
          figures: [
            {
              description: "装置の構成図",
              path: "../images/令和4年度_sample_page_009_figure_1.png"
            },
            {
              description: "変位の定義図",
              path: "../images/令和4年度_sample_page_009_figure_2.png"
            }
          ],
          choices: [
            {
              number: 1,
              text: "$f = \\frac{1}{2\\pi}\\sqrt{\\frac{k}{m_1 l_1}}$ [Hz]"
            },
            {
              number: 2,
              text: "$f = \\frac{1}{2\\pi}\\sqrt{\\frac{k}{m_2 l_2}}$ [Hz]"
            },
            {
              number: 3,
              text: "$f = \\frac{1}{2\\pi}\\sqrt{\\frac{k}{m_1 l_1^2}}$ [Hz]"
            },
            {
              number: 4,
              text: "$f = \\frac{1}{2\\pi}\\sqrt{\\frac{k}{m_2 l_2^2}}$ [Hz]"
            }
          ],
          year: "令和4年度",
          subject: "機械力学",
          embedding_file: "令和4年度_sample_page_009_embedding.npy"
        }
      ]
    },
    info: "このサンプルには複数の図表と連立微分方程式、選択肢にある複雑な分数・平方根表現などがあります。"
  }
}; 