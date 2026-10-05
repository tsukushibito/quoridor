# ORT pending試作の固定引渡し

quoridor-4lc.26 → .29 / coordinator / 2026-10-01。
最終manifest SHA cde86343753c09be704ff2d02f45e2e484689ab8f78df2a8de13444cbc03c4ae、final.wasm 1f54d0b8f0c6d3d7d51935886ed506e44376a2052506be62ca7a726c85a78a01を固定。統括実照合134hash全一致、process記録223 PID/starttick現存0。初回統括helperはtracked_processesをdictと誤読したため0件と出力、listへ修正して上記223件を確認後にruntime解放した。実run最終01:05、runtime停止01:08、source停止01:34と最終宣言/33jobの退出を合わせて確認。完全build fingerprint/瞬間peak/外部負荷の証明ではない。

自己報告ではBのNN約13ms対A44–45ms、固定goldenの有効sim中央値約20対9。Bは27/30成功、3GUARD・warm1拒否を保持し、未応答を成功に変換しない。品質・速度因果・全時計成功・採用は未認定、独立gate待ち。通常Wasm hash不変と通常runtime再検証未実施を区別。最大NN>g、ORT heap/RSS共存、人工8・真の合法200手/no-legal、deep overlay/entropy/rawview等旧未確認を保持。

.29へ最終固定版runtime steerを送り、数値/継続/破棄境界とguard時の完成tree喪失を検証する。元固定版の修正・新対局0。GUARD正常停止時のowned checkpoint保全は独立gateを受けた別契約の候補。競合A tract/B分離ORT/C B0およびH2探索設定/H3時計/H4小標本を残す。旧32局m8/T500g91成績は不変、Sigma同等/正式NI未立証、目標未達。全体期限04:00UTC/過去逸脱保持。
