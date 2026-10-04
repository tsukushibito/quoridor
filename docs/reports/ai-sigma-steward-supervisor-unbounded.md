# Supervisor turn上限撤廃 / 92

ユーザー明示により `max_turn_seconds=null` をmain scheduler/現在の運用copy/config/contract/guard/state/promptへ適用。親版17の開始・終了は変更せず、turn制限本文のみ整合した。役・common・registry・モデル/effortは変更していない。

標準40件、現運用copy28件、guard15件が成功。nullable受理、180越え/次周期二重開始なし、現在ownedへの上限撤廃で時計維持、pause/endで正確ownedのみ回収、子timeoutを確認した。チェックCPU0合計約13秒、NN/GPU/buildなし。

旧monitor/schedulerは08:51:50までに秩序停止。09:04:33通常fresh start、新scheduler6049/start35765166、monitor6062/start35765187、同boot。24期待hash/current loaded config/contract/owned nullは `frame16-turn-unbounded/running-loaded.json`。root独立受入れ09:05:12、旧4interrupted/欠測・停止gap保持。恒久idle resumeは既同設定RPC受理、developer本文readbackは非対応。

上限撤廃の実反映と自然点検/提案/notes/backupの効果は別に扱う。初回自然turnの公開成果は後続確認中。09:45:50重job通知、09:50:50正owned監督+scheduler、09:53:50monitor、09:55:50保存の92長期責任を維持する。

main専用変更5sourceは研究Gitの `research-data/ai-sigma/92-supervisor-turn-unbounded/main-owned-source.tar.gz` とmanifestで保存・軽い読み戻し一致。研究checkoutへmain専用実装を全mirrorしていない。未知/他者indexを変更せず明示path/private indexで保存。過去raw/旧失敗は削除・救済していない。
