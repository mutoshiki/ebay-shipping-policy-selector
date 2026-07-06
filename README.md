# Film Camera Shipping Guide V6

フィルムカメラ、レンズ、アクセサリーを検索し、商品別の梱包資材・付属品まで合算してeBay配送ポリシーを判定する静的Webアプリです。

## V6の変更

- EU加盟国の送料を、旧SpeedPAK DDP固定額から日本郵便 国際エアパケット（DDU）へ更新
- EU送料を第3地帯と同額に統一：100g $8.99〜2,000g $35.99
- EUカードへ「国際エアパケット・DDU」と明示
- EUでは関税・現地通関手数料が購入者へ請求される可能性がある旨を警告表示
- 150ユーロ以下でeBayがVATを徴収した注文はIOSS番号入力が必要である旨を表示
- V5の商品別梱包プロファイル、編集可能な付属品重量、1,959件の商品データを維持

## eBay実運用の確認

2026-07-06にINT-AP-0100G-V2〜INT-AP-2000G-V2のEU行を更新。300gテストでは次を確認済みです。

- United States: $25.99
- Germany / France / Italy / Romania / Netherlands / United Kingdom: $11.99
- Taiwan: $8.99
- EUで「Includes import fees」表示なし

配送ポリシー20件は既存の送料一覧へ紐付いているため変更していません。

## 注意

EU向けはDDUです。購入者に関税や現地通関手数料が請求される可能性があります。日本郵便 国際エアパケットは梱包後2kgまでです。

## ファイル

- `index.html`：GitHub Pages用
- `styles.css`
- `app.js`
- `data/database.js`
- `data/database.json`
- `data/eu-japanpost-current-rates.csv`
- `backups/`：変更前のeBay設定CSV
- `film-camera-shipping-assistant-v6-standalone.html`：単体版
