# Rust棋力評価環境の構築

2026-10-06、ユーザーは推奨した棋力評価環境を専用セッションで構築し、運用しながら調整する方針を承認した。Beads子issueとsaved threadをRootのallocation.jsonへ記録する。固定チーム・常設role・周期LLM監視は再開しない。

## 目的と境界

既存のLinux release Rust arenaを拡張し、評価器、探索器、AI全体の同時間比較を再現可能にする。新しいarenaを並立させない。Wasmは製品経路の一つで、Linux nativeを主とする。今回の成果は運用可能な入口・fixture・小さな動作確認であり、本格的棋力評価、Elo昇格、Sigma教師生成、新モデル・学習・データ取得を含まない。

- 評価器比較は探索・ordering・TT・ルール・時間・資源を固定し、凍結NNUEと距離Dを比較する。
- 探索比較は同じ凍結評価器・モデルで変更前後を比較する。同depth/nodeの意味・速度比較と、同wall timeの棋力比較を別mode・別分母にする。
- 全体比較は将来固定Sigmaモデル/設定と同時間で行える接線を用意する。MCTS Kとαβ深度の同等性を仮定せず、K固定診断を同時間の棋力へ混同しない。
- core/ai/nnueの評価数学、TT key/history/namespace/replacement、search ordering/MPC/枝刈り、モデルlayoutを変更しない。必要な重大設計は事実・競合・意思決定効果・全費とともにRoot経由で人間へ戻す。

## 開始手順

- 初期状態からの合法Action prefixと完全な履歴を保存し、再生して盤面/手番/壁/終局を検証する。任意の合法っぽい壁配置や盤面だけの保存で履歴を欠落させない。
- 同じ開始prefix/historyを使い、candidateのP1/P2担当を交換した2gameを一familyにする。色交換と左右反転augmentationを混同しない。
- 初期盤面、主評価用、傾いた局面・戦術診断を区別する。主bookと最終評価bookは調整用と分け、候補の結果でbookを選び直さない。
- 将来のSigma book生成は固定model/seed/時間又はK/noise設定の有力手から多様なprefixを作る。参照Qは定義・視点・集約を固定し、rootmean/NN root/選択child Qを混同しない。STMへ符号を合わせたabs(Q)<=0.2を暫定main目安、0.2〜0.4は補助、さらに傾いた群は診断とする。閾値は校正済み確率や均衡保証ではない。
- 終局/一手勝ち等の厳密チェックを保存する。Sigma同士の確認対局を後で実施できる設定と結果接線を用意するが、今回大book生成やGPU Sigma対局は未配分。決定的な同条件repeatを独立標本へ数えない。
- 開始prefixの系譜/cohort/兄弟関係、元seed、参照設定/source/model hash、選別理由・全候補分母を記録する。未知の独立性やbook全体への一般化を補完しない。

## 時計・結果・集計

- 初期presetは100ms/手を主条件、500ms/手を補助条件とする。これらは比較用設定の実装であり、全presetの科学実行を許可するものではない。
- 両側のCPU、RAM、TT容量、実用実装の条件を記録する。モデル初期化/warmupと各着手の実caller全費を分離し、完成反復深化のdepth/PV/node/leaf/NN/TT useful-hit/counterを取得可能な範囲で残す。内部時計の重複・欠測は明示する。
- 思考時間と実caller時間、deadline、実move受理時刻を区別する。設定のdepth/node capで停止した場合に、時間を使い切った比較へ読み替えない。期限前に得た合法な最終完成反復手を返すことと、期限後の結果を受理することを区別する。
- 時間超過/不正手/engine error/取消/全job budget/ply capをtypedで記録する。規則由来のdrawとunknownを混同しない。対局の厳密時計・forfeit方針をconfigとmanifestに固定し、事後に都合良く変えない。既engineが実現できない時計保証は未達と報告し、探索数学を無断で変更しない。
- 全予定slotの成否を記録する。primaryは完全に成立したfamily pairのscoreとし、予定/開始/完了game、完全pair、不完全pair、unknown理由、cohort別分母を併記する。unknown除外の単純game scoreを全予定実績と呼ばない。全未知を0/1に割り当てた予定分母のscore範囲も可能なら出す。
- 完全pair単位の平均・不確実性を出す。既定の固定sample集計でpaired bootstrap seed/resample数と適用範囲を明示し、1pairや系譜依存から精度を保証しない。開いた結果の繰返し確認で通常95%区間を停止規則にしない。SPRT/Elo校正の新方式は今回実装を義務にせず、別判断へ残す。
- code/config/book/history/model/schema/hash、planned slots、時計と取消/回収、各gameのActionと終局理由、集計分母・限界を一つのrun manifestへ束縛する。必要結果はbounded JSON/CSVと圧縮観測へ、検証可能な集計にする。
- 学習の最終sealed testや開封済み研究評価をこのbookへ無断転用しない。学習担当の凍結モデル引渡し後の棋力評価は別に具体配分する。

## writer・セッション・資源

- 新saved main session、Rootと同fullaccess=danger-full-access/approvalPolicy=neverを明示し、同Root model/effortのまま。cwdはmanaged `.worktree/arena-evaluation`。本人はready/show、owner、実cwdを確認してclaimする。
- 本人一人がWTのrunner arena/config/対応tests・configs/arena・必要な統計/開始手順moduleと対応案内を編集する。現役入口を更新し不要shim・複製を作らない。独立moduleへ責務を分け、巨大runtimeへ無関係な機能を積み増さない。
- 318はai/core探索源、319はdata/学習/dataset入口のwriter。runnerの同file上でも担当機能を分け、既sourceが必要ならRootへ停止版統合を戻す。main/source/index/commit/ref/merge操作はRootだけ。本人はWT sourceの停止path/SHAで引渡し、Git index/ref変更0。
- CPU最大2 logical、重い作業はRootが割当てるslotで0,1を候補とし、319の2,3と区別する。family RAM最大2GiB、GPU0/新取得0/新依存0。全親CPU4/RAM8/VRAM6/保存12GiB/UNKNOWN128MiB維持。
- 新保存64MiB inclusive（code/WT8、build40、必要evidence8、Git/temp8MiBの目安）。完了maintenanceのforward reservation160→96MiBとarena64を保存し、current資産・old fees/caps・UNKNOWNを減額/削除しない。shared targetの現在分と新増分、WT/ignored/tmp/Gitも束縛しfresh directed coverageを維持する。見積り不成立なら具体不足をRootへ戻す。
- compile/tests/lint/NN0 fixturesは累計600秒、初回native動作確認は最大2job/全attempt180秒/各job90秒。初回はD対Dまたは人工小終局prefixによる時計・色交換・取消・pair/unknownの機能確認で最大4game slot、NN/GPU0。モデル本対局・Sigma book生成・十分な対局数の比較は今回未配分。
- 静的source実装は直ちに開始可。2026-10-06の連携調整で、319のprivate immutable native参照成立と318ビルドのexact STOP通知後は、通常のビルド・限定NN0ソフト検証をCPU0,1/RAM2GiB/GPU0で319固定本fitと並行可。共有target writerは一人、親CPU/RAM内、同時費は競合ありと記録する。初回は最大300秒を既600秒内で使い、実arena smoke/時計は319自然STOPまで開始しない。速度比較・arena実時計と競合する仕事は非重複を維持し、他owner interrupt/kill0、Rootの受領ACKだけを次工程gateにしない。
- 長jobは既research-jobのbounded log/cancel/exact child cleanup/一度の完了通知を使い、完了イベントまでIdle。新server/cron/周期LLM監視・固定role・追加executor/reviewerの再帰委譲は今回配分0。必要独立レビューの対象と予算は実装停止後にRootが決める。

## 検証と引渡し

最低限、prefix再生/history/兄弟pairと色対応、early終局、invalid prefix、side mapping、時計/cancel/期限/ノードcapの理由、未知/部分pairを含む集計、empty/allunknown/true draw、一意slot復元・モデル設定bindingを意味のあるfixtureで確認する。変更した全手書きsource/configは既formatterで整形し、対象tests/lintをbudget内で実施する。検証を全suite反復へ膨らませない。

初報はclaim/cwd/fullaccess/保存forecast/編集境界/実computeの有無を簡潔に返す。重大判断・意味ある結果・slot必要性・障害・source停止をRoot thread `01a0f2e9-357d-7ef3-a2fe-b16f80accda5`、issue `quoridor-4lc`へ通常報告。静的実装を受付成功・環境完成・棋力結果と呼ばない。Beads本人更新/backup sync、停止source/子回収、明示path/SHA、validation、残費、未完了と次の実用対局費を返す。Rootが受入れ・main統合する。

## 通常ソフト修復の追加配分（2026-10-06）

初回software job `ea112b67` は一時linker objectのinventory raceでexit1となり、controller176.195790845秒・全直接子回収・cleanup/remaining空を保持する。manifest2fixturesはPASS、integration/build-final/lintは未成立。既600秒の残423.804209155秒から、新たにONE recovery phase最大240秒を前向き配分する（support command最大10秒＋outer job最大230秒、worker最大210秒で回収余裕）。旧初回300秒・失敗費をresetしない。

旧guard source/SHAを保存し、single-statとbounded inventory retryで修復する。retry枯渇はUNKNOWN・admission拒否を維持し、消失fileを無条件freeへ換算しない。限定NN0 race/枯渇fixture後、fresh within・実物理・共有target唯一writerを確認して未完了の限定integration/build/Clippyだけを継続する。製品source14path・既PASS fixtureを再用し、fullsuite/NN/arena時計を追加しない。CPU0,1/RAM2/GPU0/build40MiB/inclusive64MiB、319固定fitとの並行・318への直接target開始/終了通知は不変更。このphase失敗時の更なる反復は未配分。
