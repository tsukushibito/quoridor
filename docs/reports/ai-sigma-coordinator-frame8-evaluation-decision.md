# 116計画の採否とCPU比較の実配分

116は計画成果として受け入れる。CPU-onlyと両者GPU供与、500ms採用と残処理・自待ち・実CPU/queue費用、pair単位と全attempt/未完了の区別を採用する。必要12 Git blob/manifestと停止SHA93c48fa17cdd9c479774d35770e98572e9cbc7fe28c0e300a134c6d1f2afd98d/入力不変を確認。軽い管理2job終了と失敗log欠測・短command資源欠測は保持する。

旧Hoeffdingで平均.5の幅<.05には600pair、提案運用cap330m+1200なら55.33時間/環境となる算術を確認した。現4時間枠で正式NIを保証しない。empirical Bernsteinは将来の結果前候補として保留し、理論・IID・分散・power仮定を今回の探索WDLへ後付け採用しない。55.33時間は運用cap案であり実測費用上限ではない。入力供給時t0に自待ちを含めるF時計は後続実装案として保留、現117は112/113のready-relative診断時計のまま、自待ちと入力供給時刻を別記する。旧時計や結果を遡及換算しない。

GPU115は物理model未成立を有限受入れしてclose。共有host/container/driverを変更せずGPU不足・必要条件を保存する。一方CPU比較117を実配分し、2026-10-02T10:50:10.015525UTCに既experiment idleへ契約全文turn/start accepted（turn01a0fc3c-5ed2-7ac0-acf1-cbf80d414c2f）、本人10:50:29受領・pause/担当確認・claim開始をBeadsで確認した。115停止保存後の同actor新scopeであり重複起動0。

117は候補C1.5対固定Sigma、専用2Worker/SAB/browser main、CPU[2]/推論1thread、RAM6GiB/guard5.5GiB、保存128MiB/guard112MiB既entry内。initial/asym/jump×seed1979/2098×先後交換の結果前6pair最大12局を実施する。機能2要求から進め、全失敗・未完了・初回CP・採用・残返却棄却/自待ち/ACK非依存を分離する。GPU可否を開始条件にせず、正式CI/NI/旧WDL統合0。受領・開始は対局完了や棋力認定とは別。実処理12:15/新run12:10/提出12:30UTCの早側契約、親14:05:49重job停止/14:15:49終了を維持。

次の実報告は117担当→統括。停止最終版の重大主張だけ必要範囲を独立確認し、全対局NN反復/新階層を先に追加しない。116の新正式法やF時計の採用は実117結果の救済条件に使わない。目標Sigma同等/NIは未達。
