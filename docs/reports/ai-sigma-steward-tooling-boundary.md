# 102 構成案内の反映と品質境界の判断

受領/claim04:03:06UTC、現行契約2へ継承。main/研究のAGENTS.md・README.md・研究実行規約、計6文書を更新。元本文は同bytes（main AGENTSの実行mode差は保持）。短い参照インデックス、現状の製品/研究/データ/外部資源表、現役共通機能と実験設定・独立検証・Git過去版の配置境界を実適用。READMEの固定逐次研究工程を競合仮説/並行実験へ整合。未達棋力や将来の実体移動を完了と記していない。新リンク/見出しとmirror一致を確認。研究側に無いscheduler文書への初期リンクはmain checkoutの資料案内へ訂正。

観測:判断対象12fileを限定read、Python3file ASTとNode6file --checkは成功しsourceは実行していない。97measureは27行/最大1781文字、browser10行/1040文字、100numeric5行/1949文字。両runnerは126行で行一致比96.0%、差は出力/期限/RAM/累積runtime等に集中しSIGMA77のenv名も再利用。measure/browserには時計・課題期限・Chrome/依存パス・出力・検査条件が混在。これらは今回条件として必要だが次回変更時の転記漏れリスクを持つ。root packageのcheckはWasm build/Rust fmt-clippy/製品TS検査で、研究CJS/Python専用lint/format指定を確認した設定からは見つけず、PATH/root-localのruff/black/prettier/eslintも無し。全repoの不存在や既存コードの不具合を断定しない。

1. 次に触る現役measure/browser/Workerとrunnerの可読性を優先する。作用単位で改行・命名・関数境界を整理し、既存の構文確認を編集pathに限定する。ownerは各sourceのexperiment/critic、stewardは整形規約の提案担当。次の修正前に15〜20分を目安として統括が配分。効果仮説はレビュー差分の局所化と転記漏れ低減、費用/影響は整形差分の増大。必要なら研究専用Formatter/Linterを別配分で選ぶが今回は導入なし。最小確認は構文＋変更に関係する既mockだけ、NN再実行を一律前提にしない。次修正でレビュー差分量/修正漏れを追い、改善が無ければ拡大しない。
2. 次のrunner修正時に共通の起動/所有/停止部分と課題設定を薄い境界に分ける。期限・CPU/phase/RAM/storage/run出力は検証するrun設定へ移し、共通部分から97/100の固定期限を除く案。ownerは統括が指定する単一基盤writer、experiment/criticが各設定を維持。30〜45分の将来配分目安、現在停止版のsource/Gitは変えない。効果仮説は安全修正を一箇所に集め、異なるRAM/累積capの取り違えを減らす。影響は共有故障面が増えること。採用後は既停止/期限/所有mockと設定拒否の必要ケースだけで確認し、次回の修正箇所数と設定不整合を追う。独立audit.py/numeric.cjsの算術/判定は統合せず、共有RuleA/実行基盤への依存と独立性の限界を明示する。

上記は改善案であり導入効果は未実測。品質導入を100受入れ/次研究のgateへ追加しない。文書に現行の配置方針は反映済み、実体移動/削除/共通化/全整形/新依存は未実施。source/97・100データ/roles/common/registry/92runtime/製品コードを変更0。NN/Chrome/build/model/取得0。99のGit/archive正本を参照し全raw/source複製0。短期処理終了/self-stop先保存、管理操作は累計120秒枠内、未記録peakと04:07:17後の文書リンク確認開始を保持する。92の05:39:12/05:44:12/05:47:12/05:49:12責任を維持。詳細はresearch-data/ai-sigma/102-tooling-boundary/のobservations/runner-diff/link-check/self-stopを参照。採否と必要owner/残予算はcoordinatorへ引渡す。

期限差分:新規source調査は04:05:21で終了したが、文書リンク確認/修正/本文固定は04:10:32まで続き、処理04:09:17を約75.6秒超過。全期限遵守とは記載しない。以後はGit/Beads/配送だけ。
