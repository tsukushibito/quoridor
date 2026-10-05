# 専用2Worker 112/113の限定受入れ

2026-10-02UTC、112 tested game3682ab7b520024735e79e42eea79c982897c3957/機能11c994c/data2d71f67・参照69259b9と、113独立最終Git85468449a191e2e28280f0beb9a8df38e9f53b8fを受入れる。担当のsource/NN/Chrome/monitor停止・必要結果Git保存・backup・引渡しに基づき、統括が両issueの所有を引継いでcloseする。目標達成ではない。

Workerはプレイヤーごとにモデル/session/SAB/世代を分離し、通常手番側だけ新探索する。browser mainが対局/合法判定/時計/採用、Nodeは外側起動・監視・終了後保存。完成手を確定した後の旧返却は棄却し次木へ再利用せず、相手通知/時計は旧ACKの一律前提としない。自Worker次探索のみ自旧zero回収を待つ。この構造と有限実枝を独立支持する。毎手Node審判/timer/CP往復へ戻さない。

保存initial/asym各色交換4局はgoal4、W2D0L2、298合法採用、late/未完了0をbrowser内独立replayで確認した。対局手NN1232と別機能29/課題手NN1261、startup18を分ける。相手t0<旧ACK232、旧返却discard211、旧API区間が次t0を跨ぐ210を別観測として保持する。API awaitは内核CPU時間でない。旧単Worker/C1対照のWDLへ統合しない。

独立機能7は正常6合法+取消null1、動的4ply、公開最大418.055ms、手NN68/startup6。相手t0旧ACK前4、discard4、自待ち最大11.515msを確認した。独立7rootは固定golden5/動的自己2、保存root12sampleは別分母で型/finite/strict/P2/Actionprior/固有訪問規約を支持。全深部/全NN/任意tree一般性の証明ではない。共有RuleAによるルール独立性限界を保持する。

原pair Worker停止upper<=500280/lower>50018、ACKwall超過18を有効思考超過や棋力不公平へ直接変換しない。両推論1threadで同logicalCPU2を使い、残処理と相手検索が競合し得る。残処理CPUと待ちの対称性、途中clock drift/OS硬締切、正式同実効計算資源は未成立。500msは採用の試験条件であり正式公平性/NI/Sigma同等/actual_goは認定しない。

原機能版ACK_known採取時点不足は旧raw保持しgame版実t0と区別。systemErrorによる途中通知拒否、独立初回monitor deadline設定拒否(Chrome/NN0)を失敗として保存し、修正版結果へ付替えない。112 stop25911f3e41ea771798fe5f5d358bc0f52c4bedc0c3b93bd1b7689ca5531adb90、113 stop1dab2d2192ecac24c40a6b1b50e938ae3b12831832424e0de50d8cf72e33b880。原450/自己79identity現在不在とforced/controlled/outer同identity回収・Modeldrop両zero/main timer/message/monitorcallback停止は別証拠で、自然終了/全期間保証へ格上げしない。

最終必要入力の統括照合は.artifacts/ai-sigma/resume-20261002/112-final-coordinator-intake-check.json、113-final-coordinator-intake-check.json、113-stop-coordinator-intake-check.json。原archive01f5ef08…4950と独立archive94c8e031…6d98の実SHA/Gitblob、必要summary/stop等member hash一致を確認した。全member復元は担当120/48の報告と区別する。112 source必要3実bytes、113の原7source Gitblob/stop/current照合も保持する。

根拠は[112報告](ai-sigma-experiment-player-workers.md)とresearch-data/ai-sigma/112-player-workers/、research-data/ai-sigma/113-player-workers-independent/のsummary/archive/bindingと独立報告。研究のbrowser対局経路・専用Worker切替は有限成立したが、4局の診断から同等証明はできない。

現在枠の新重jobは10:02:31まで、全終了10:12:31。新重い評価を追加せず、残りは92既ownerの10:07:31 scheduler/正確owned、10:10:31 monitor回収、10:12:31証拠保存を統括が受入れる。次枠は未許可。次の提案は、固定版・入力と資源/残処理費用の扱いを結果前定義した比較計画と必要な標本を用意すること。現行の500ms採用機能支持と正式同実効資源の主張を分ける。必要な残処理CPU/自己待ちの小計測を先に選び、旧成績を正式標本へ再分類せず、別許可なしに実行しない。
