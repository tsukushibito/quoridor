# SIGMA-SHARED-MEMORY / quoridor-4lc.107 / 現行契約2

既experiment saved01a0f31d-6d15-7620-bb63-4b4f878e4746が単独owner。親現行版6/common/experiment/実行記録規約を継承。本書はユーザーの共有メモリ方針と、直後の「まって」による部分保留を適用する。旧契約1のframe配送対照はGit履歴へ保持し、未実行の24要求を今回の既定計画から外す。107の同turnへ有効本文を配送し、新issue／新ownerを作らない。

## 現在の方針と保留範囲

先行ユーザー指示の主経路はブラウザmainと探索WorkerのSharedArrayBuffer＋Atomicsで最新完成暫定手を公開／読取すること。初回完成後に有効手を保持し、MCTSで更新する。毎更新message→Playwright→Nodeを応答経路の必須にしない。世代／局面の一致、完成済みfieldの整合、初回無し／取消の意味を保つ。mainのbusy waitやWorker保有lock待ちを作らず、詳細CP／数値／診断保存は応答経路から分ける。NodeとSABを直接共有できると仮定しない。

ユーザーの最新「まって」は、直前のbrowser-only-validation-directive（Node審判／時計／必須事後検証を除去し、対局と検証をブラウザ内へ全面変更）の適用と新実行開始を保留する。この除去／全面切替に依存する変更も保留。既に着手した場合は該当scopeを安全な状態で停止し、版／現在の変更／所有process／未実行を記録、次のユーザー指示まで進めない。研究全体や先行共有メモリ方針の一括pause／cancelと解釈しない。待機や報告で保留解除を推定しない。

現在進められるのは、Node除去へ依存しないSAB protocol・整合性・世代／取消／未完成／初回無しの小NN0 mock、secure context／crossOriginIsolated／COOP／COEP・既依存読込の安いpreflight、設計差分と現状の記録。これらが保留した全面変更に依存する場合はその部分も停止。旧frame通知削減の測定へすり替えず、Nodeを最終制御主体とする別案も勝手に確定しない。実AI／新対局のbrowser-only切替は未配分のまま待つ。

## 診断上の既知事項

103 late2は両方とも有効完成cacheを持つ。asym147参照は初回106.403ms／最新397.565ms、seal411予定→499.050、最終506.253。jump54候補は初回102.496ms／最新381.887ms、seal→502.441／最終502.883。checkpoint=falseは最終late拒否後であり、初回推論未完成とは呼ばない。Node timer実行遅れは直近の保存要因だが同期処理／通知／OS寄与は未特定。SAB導入だけでtimer遅延解消を認定しない。AI計算・browser採用・外部automation／収集を区別し、旧Node条件の成績を新browser条件へ統合しない。将来の共通診断条件は実行前に定義するが、本保留中にその全面切替を実行しない。

## 所有・資源・期限

write scopeはtools/ai-sigma-cp-frame/、自己resume-20261002/CP-FRAME/、research-data/ai-sigma/107-cp-frame/、docs/reports/ai-sigma-experiment-cp-frame.md。103／97／105等の停止source／結果、共有model／役割／registry／92はread-only。新build／取得／model／kernel／GPU／学習／製品統合／push／新role／再委譲を配分しない。既コードの必要な参照と小差分で実装し全copy／全史hashを要求しない。

処理05:20UTC、新heavy05:15UTC、提出05:30UTCの既期限を維持。静的CPU0/currentRSS RAM1guard896MiB/各60s総180s。NN上限CPU2単logical/threads1/currentRSS RAM4guard3.5GiB/各180s総300sは上限として保持するが、保留された経路に依存する新NN開始を許可しない。保存32MiBguard28は既entry予約内追加0。親CPU4/RAM8/保持＋未使用有効予約12GiB、05:39:12新重job停止／05:44:12監督停止／05:47:12monitor回収／05:49:12枠終了は不変。ユーザーの待機で期限を自動延長しない。

許可された小デバッグは同課題／総残予算内で反復可、Git版とrun／設定／必要結果／失敗要点を区別する。旧条件／失敗を上書きしない。長期processがあれば正確な所有identity／停止状態を記録し未知ownerへsignalしない。受領と該当scope停止／現許可範囲を短くcoordinatorへACK。本文前に必要停止証拠、Git／必要data、Beads backup/reportを保存する。正式公平性／NI／Sigma同等／actual_goは未認定。
