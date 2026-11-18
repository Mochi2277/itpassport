# ITパスポート学習室

ITパスポート試験の非公式・無料学習サイト。GitHubリポジトリは独立運用です。

## 現在実装済み

- IPA令和7年度（2025年）公開問題をベースにした**表現調整版100問（問1〜100）**
- オリジナル練習問題12問
- 4択・採点・解説、年度/出題種別・分野別選択、ランダム/復習モード
- localStorageによる端末内の学習履歴保存
- スマートフォン対応
- 楽天アフィリエイトの**未設定**広告枠

**重要**: IPAの問題は原文どおりの完全転載ではなく、要約・表現調整した演習版です。元の表・図・長い設問は文章に置き換えている場合があります。正式な問題文・選択肢は必ずIPA原文PDFで照合してください。教材リンクは楽天ブックスの通常リンクであり、アフィリエイトリンクではありません。

## 起動

`index.html` をブラウザで開いてください。静的なHTML/CSS/JavaScriptのみで動きます。

## Cloudflare Pages

Cloudflare Dashboardから Workers & Pages → Create → Pages → Connect to Git。
このリポジトリを選び、Framework preset: None、Build command: 空欄、Build output directory: `/` または `.` を選択します。公開にはCloudflare側の接続操作が必要です。

## IPA公式資料

- [令和7年度 問題PDF](https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2025r07_ip_qs.pdf)
- [令和7年度 正答PDF](https://www3.jitec.ipa.go.jp/JitesCbt/html/openinfo/pdf/questions/2025r07_ip_ans.pdf)
- [IPA公開問題一覧](https://www.ipa.go.jp/shiken/mondai-kaiotu/)

## 問題の追加

`questions.js` の `window.QUESTIONS` 配列に問題オブジェクトを追加してください。

- `id`: 一意の問題ID
- `year`: 例えば `2025`、`オリジナル`
- `number`: IPA公開問題の問番号
- `field`: ストラテジ系、マネジメント系、テクノロジ系
- `topic`: 分野
- `q`: 問題文
- `choices`: ア〜エの4択配列
- `answer`: 0～3（アが0）
- `explanation`: オリジナル解説
- `tip`: 復習時のメモ
- `source`/`sourceUrl`: 公式出典とPDFへのURL
- `adapted`: 文章を調整した場合 `true`

公式問題の採録では、**問題本文、選択肢、図表、正答PDFとの照合を必須**とします。現段階では2025年度の全100問を学習用の表現調整版として登録済み。2026年度分は未登録です。

## 広告と公開前作業

楽天アフィリエイトの掲載サイト登録、リンクの発行、適切なPR表記が必要です。お問い合わせ、プライバシーポリシー、広告についての説明も公開前に検討してください。学習履歴はこのブラウザのlocalStorageにだけ保存され、端末間で同期されません。

IPAによる運営や後援はありません。
## 品質検査（2026-11-18）

- 2025年度の問1〜100に欠番・重複なし
- 正答インデックス（ア=0〜エ=3）はIPA公式の正答一覧100件と機械照合済み
- 全問に4択とオリジナル解説あり
- 一部の問題文・図表は要約・文章化されているため、原文の完全再現や全設問の個別専門監修を保証するものではありません
- 初期公開後、文章の誤記・説明の正確性は継続して改善してください

フォントはGoogle FontsのBIZ UDPGothicを使用しています。ネットワーク制限時は端末側の代替フォントとなります。
