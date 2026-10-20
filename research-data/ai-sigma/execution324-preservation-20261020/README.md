# 324の保存区切り（2026-10-20）

人間の通常commit/push継続指示を、26の実native・normal collection・保存解析STOP後に実施した。モデル、重み、封印データ、DB、lock、巨大cache/build、実行用imageは保存対象へ混ぜない。科学的検査・再計測を行う保存処理ではない。

- `environment-validation.json`: 従来foreignとして保護した既存環境変更の独立保存。JSON/限定整形・shell構文・Cargo.lock意味対応だけを確認し、container rebuildやtool更新を実行していない。
- `legacy-frozen-records.json`: 未追跡だった旧arena/perfの小さい設定・reportの原bytes/SHA。予定・失敗・未入場を実施済みに変更せず、凍結bytesを再整形しない。
- `completed-and-forward-records.tar.gz`: 20〜27の終了済み比較条件・必要な元データ・保存集計・操作code/失敗記録。25.3/27の前向き対局controlsは**未入場**として含む。
- `unqualified-root-diagnostic-source.tar.gz`: 28の固定診断差分とSOURCE_ONLY確認。実subjectはalpha/neighbour_opportunity/measurement。AI1/RunnerLIB1は**UNBUILT/UNTYPED/UNRUN**で、root分担prototypeや診断26/比較312は未実行。
- `legacy-untracked-source-backup.tar.gz`: 現役callerではない旧`.orig`の原bytes保全。新しい互換source入口としては配置しない。元のlocal copyも変更しない。

各archiveの`.manifest.json`に、元project相対member、元path、mode/size/SHA256とarchive identityを記す。全memberをstreamで読み戻して元bytes/modeと一致したことを確認する。展開する場合は別の空directoryを選び、元pathへ戻す場合は対象reader停止と既存fileの所有/未保存変更を確認する。元入力・model/libraryの外部参照をarchiveの存在だけで再資格化しない。共有する通常opening bookは一度だけ保存し、private weightsは参照のまま保持する。

原26は100DepthComplete+4NodeLimit UNKNOWNで完成gate未達、基準実装を保持する。原25不成立の4UNKNOWN/100unperformed/旧64STOPPED、独立25.3新104のgatePASSと混在順位、原24/27の有限条件と費用・UNKNOWNを変更しない。28のSOURCE_CLEARはsoftware/image/native/performance資格ではない。詳細は既存の[研究知見](../../../docs/research-findings.md)と[最適化agenda](../../../docs/design/ai-nnue-optimization-agenda.md)、担当・状態はBeadsを参照する。
