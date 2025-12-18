# SD WebUI Advanced Styles Manager

[English](#english) | [日本語](#japanese)

---

<a name="english"></a>
## English

**Advanced Styles Manager** is a powerful style management extension for Stable Diffusion WebUI (AUTOMATIC1111 / reForge / Forge).  
It extends the standard style functionality with **Group Management**, **Visual Selection (Gallery)**, and **Dynamic Randomization**.

> **⚠️ IMPORTANT**
> **Data Backup Recommended:**
> All style data is saved in `styles_v2.json` and the `thumbnails` folder within the extension directory.
> Please backup these files regularly, especially before updating or reinstalling the extension.

### Key Features
- **📂 Group Management**: Organize your styles into custom groups (e.g., "Lighting", "Clothing", "ArtStyle") instead of a single long list.
- **🖼️ Visual Selector**: Select styles visually using thumbnails.
  - If no image is set, a placeholder with the style name is automatically generated.
  - You can upload custom thumbnails or paste images directly from your clipboard.
- **🎲 Dynamic Random**: The **"Add Group (Random)"** button adds a dynamic slot to your prompt chain.
  - A style is randomly selected from the specified group *at generation time*.
  - Perfect for creating variations (e.g., random outfits or locations) without changing the prompt manually.
- **🔍 Advanced Search**:
  - **Scope**: Search within the "Current Group" or across "All Groups".
  - **Target**: Filter by Style Name or Prompt content.
- **📥 Import**: Easily import existing styles from WebUI's standard `styles.csv` into a specific group.

### Requirements
- **WebUI**: AUTOMATIC1111, reForge, or Forge.

### Installation

1. Open the **Extensions** tab in your WebUI.
2. Select the **Install from URL** sub-tab.
3. Paste the repository URL of this extension into the "URL for extension's git repository" field.
4. Click **Install**.
5. Go to the **Installed** tab and click **Apply and restart UI**.

### Usage

#### 1. Apply Styles Tab (Main)
- **Select Group**: Choose a category from the dropdown.
- **Select Style**: Click on a thumbnail in the gallery or select from the dropdown list.
  - **Add to Chain**: Adds the selected style to the active chain (fixed).
  - **🎲 Add Group (Random)**: Adds a "Random Slot" for that group. The style will change randomly for every image generated.
- **Generate**: The styles in the "Active Styles Chain" list will be automatically injected into your prompt/negative prompt.

#### 2. Manage Styles Tab (Edit / Delete)
- **Create / Edit**: Select a group and style to edit the prompts.
- **Thumbnail**: Upload an image or paste from the clipboard to set a cover image for the style.
- **Import**: Select a target group and click "Import from styles.csv" to migrate your existing standard styles.

### License
[MIT License](LICENSE)

---

<a name="japanese"></a>
## Japanese

**Advanced Styles Manager** は、Stable Diffusion WebUI (AUTOMATIC1111 / reForge / Forge) 向けの強力なスタイル管理拡張機能です。  
標準のスタイル機能を拡張し、**グループ管理**、**ビジュアル選択（ギャラリー）**、**動的ランダム適用** などの機能を提供します。

> **⚠️ 重要**
> **データのバックアップについて:**
> 作成したスタイルデータは、拡張機能フォルダ内の `styles_v2.json` および `thumbnails` フォルダに保存されます。
> アップデート時や再インストール時にデータが消えないよう、これらのファイルは定期的にバックアップを取ることを強く推奨します。

### 主な特徴
- **📂 グループ管理**: スタイルを「照明」「衣装」「画風」などのグループに分けて管理できます。膨大なリストから探す手間がなくなります。
- **🖼️ ビジュアルセレクター**: サムネイル画像を見てスタイルを選択できます。
  - 画像が未登録の場合は、スタイル名が書かれたプレースホルダーが自動生成されます。
  - クリップボードからの貼り付けやアップロードで、独自のサムネイルを設定可能です。
- **🎲 動的ランダム（ガチャ機能）**: **「Add Group (Random)」** ボタンで、ランダム枠をチェーンに追加できます。
  - 生成のたびに、指定したグループの中からランダムでスタイルが選ばれ適用されます。
  - プロンプトを手動で書き換えずに、衣装やシチュエーションのバリエーション出しを行うのに最適です。
- **🔍 高度な検索機能**:
  - **範囲**: 「現在のグループのみ」または「全グループ」から検索できます。
  - **対象**: スタイル名だけでなく、プロンプトの中身も含めて検索可能です。
- **📥 インポート**: WebUI標準の `styles.csv` から、指定したグループへデータを一括移行できます。

### 動作環境
- **WebUI**: AUTOMATIC1111, reForge, Forge

### インストール方法

1. WebUIの **Extensions** タブを開きます。
2. **Install from URL** タブを選択します。
3. "URL for extension's git repository" 欄に、本リポジトリのURLを貼り付けます。
4. **Install** ボタンをクリックします。
5. **Installed** タブに移動し、**Apply and restart UI** をクリックして再起動します。

### 使い方

#### 1. Apply Styles タブ（メイン操作）
- **Select Group**: カテゴリを選択します。
- **Select Style**: ギャラリーのサムネイルをクリックするか、リストから選択します。
  - **Add to Chain**: 選択したスタイルを適用リストに追加します（固定）。
  - **🎲 Add Group (Random)**: そのグループの「ランダム枠」を追加します。生成するたびにグループ内から勝手にスタイルが抽選されます。
- **Generate**: 「Active Styles Chain」にあるスタイルが、自動的にプロンプト/ネガティブプロンプトに挿入されます。

#### 2. Manage Styles タブ（編集・管理）
- **Create / Edit**: グループとスタイル名を入力して、プロンプトを新規作成・編集します。
- **Thumbnail**: 画像をアップロードまたは貼り付けることで、スタイルにサムネイルを設定できます。
- **Import**: インポート先のグループを指定し、「Import from styles.csv」を押すと、標準機能のスタイルデータを本拡張機能へ取り込みます。

### ライセンス
[MIT License](LICENSE)