# rootから統括へ：ユーザー明示4時間再開と課題集合の自律実行

ユーザー最新指示「とりあえず課題一覧をチームに伝えて自律的に進めるようにして。一旦、4時間枠で。」を正式な新枠許可として配送する。frame22開始2026-10-05T11:36:03Z、終了15:36:03Z（JST20:36:03〜翌00:36:03）固定。準備完了から起点を取り直さない。新heavy入口15:26:03、監督scheduler正owned15:31:03、monitor15:34:03、必要保存15:36:03。旧frame21/runの期限・結果・失敗・累積は不変更。

## 実委任

親goal quoridor-4lcは統括継続担当。まず新 docs/design/ai-nnue-optimization-agenda.md の課題集合を既saved担当へ具体課題と合わせ全文又は必要範囲で伝え、自律判断を実作業へ接続する。特定一案の固定優先や全案義務でなく、探索速度、評価/学習、教師生成を全体で比較して最大障害・期待効果・情報価値・全費から現在計画を更新する。独立課題は編集ownerと実物理上限・測定非競合の範囲で並行。役名で実装実験をexperiment一人に固定しない。少し試して悪かったことを方式全体の断念にせず、実験不成立・不足データ/不足学習・条件上不支持を区別し、保留と再検討条件を残す。Supervisorへこの集中/機会損失/断念と役の実働を既自然/節目で点検する材料を渡す。通常のroot再確認や全役承認を入口にしない。

最終目標NNUE最高棋力。frame21はu128 wall_distance main採用79fc729、同仕事αβD/NNUE高速化とMCTS K64無明確利益。MCTS CPU API 99.1%が支配し実resident真GPUbatchは有力だが、保存profileと現役callerから選定する。A距離保持残差BEST200 val .478510/B DAG4 .478866、400悪化は小96train再用val条件の知見、全経路特徴やNNUEの反証でない。L/IはRust接続・行動差、棋力24slotは1LOSS/2UNKNOWN/21未開始で未成立。TT手跨ぎ/ordering/leaf差分などagendaの機会も比較する。統括は具体問い/条件/資源/採否と担当をBeadsへ登録して実配送し、重要結果で配分を更新する。初回は15分目安で実配分/本人開始と運用loaded又は障害をrootへ知らせる。全体の成果保証は求めない。

## 資源と正本

既上限CPU合計4logical、RAMcurrent8GiB、保持物・依存cache・一時物＋有効未使用予約12GiB、GPU推論VRAM6GiB/1job30min。GPU学習旧累積2hの確認済み残のみ、不明なら新0。運用1logical/current1GiB/92既112MiBを研究物理合計内で確認。現量/既予約/unknownはfresh確認し累積resetや未知free扱い0。最新整理観測retained10051764224+保守forecast/unknown合計10478641152Bは参考で、新admissionには再確認する。旧capsを新許可枠の自動resetとしない、個別現在配分を統括が明示する。新依存/model取得、共有環境更新、製品採用・push公開、未知資産削除は今回追加許可0。同saved model/effort/settings/既AppServer維持、人数gate0/同役二重start0。

main /workspaces/quoridorが正本。旧ai-sigma/research-team/scheduler checkoutは撤去済みで呼ばない。必要資産は .worktree/assets/{models,checkpoints,inputs} と research-paths.json v2 / scripts/dev/research-assets.py で解決しrunへ実path/hash記録。SigmaONNX .worktree/assets/models/ai-sigma/reference/sigma-pcr250/best.onnx SHA d790dac68389f7602ff8a887a2385417d3c925fe22da7164c86e9226f943908d。現managed WT frame21-features/frame21-searchは保存sourcepoint/比較用途の確認後使える。必要ならhelperで別managed WT、恒常mirror0。Git復元を実比較の毎回前提にせず必要旧版は比較専用に限定保持。

Rootはagenda/本handoffだけGit保存して書込停止し、dispatch受理時に通常Git/index統合ownerを統括へ解放する。並行writerは停止path/SHAを引渡し、一人だけ統合する。整形は変更コード全言語に適用。旧科学data/開封test/173正式198非学習は保持。

## 92運用と終了

既steward92へ一度だけframe22親本文版22とruntime期限/binding更新を実配分すること。docs/design/ai-sigma-continuation-20261001.md は92 solewriterを維持しRootは編集0。上記全文を現在有効本文へ整合し旧active枠をGit履歴へ。registry current_operation、現役source/assets、新hashへ実validate/freshstart/running-loaded/exact PIDtickを本人確認、period1200/max_turn_seconds=null維持。旧停止/失敗stateはexactturnとreceiptを区別して扱い全state消去しない。静的研究は運用準備待ちgate0、heavyはcurrent loadedと実物理admit。

終了準備でStewardの整理/長期保守判断とSupervisorの目標貢献/役割実働/配分振返りを実配送して既枠内で判断を得る。通知のみを完了とせず時間不足なら理由/担当/次機会を保存し自動延長0。新科学停止と92の正owned/scheduler/monitor回収・必要保存の時刻を所有する。旧維持予算の確認、各owner子wait/現在identity不在、Beads notes/backupを完了し親最高目標は未達ならcloseしない。

現在計画 docs/reports/ai-sigma-coordinator-current-priorities.md をframe22へ更新し、今回課題一覧を設計参照として一つにする。研究を計画だけで止めず必要な修正・実験・評価を許可内で継続する。
