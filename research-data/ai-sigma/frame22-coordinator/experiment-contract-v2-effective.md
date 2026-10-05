# frame22 常駐GPU教師生成を有効データと学習へ接続

問い:現MCTS CPU推論API99.1%支配に対し、既resident真GPUbatchのnative pumpは同K/モデル/生成規則で有効教師/全job秒を改善し独立データ不足を安く解消できるか。
担当experiment。初期読取main crates/quoridor-{runner,inference,ai,data}/現役docs、frame21-mcts-cost保存profile。新source候補は専用managedWT frame22-teacher（統括がfresh保管後作成）、runner/src/runtime.rs・推論backend必要部分・専用tests/diagnostic/dataだけsolewriter。criticのai/core/nnue源とhypothesis Python源を編集しない。既経路が十分なら新コピーを増やさず設定対照を実行。
有力案は既TensorRT graph常駐 maxB8/fill2ms、activegames24対48、同モデルK64/worker1/seed登録。同推論API要求まとめを真batch効果としない。現実backend/config制約を調べ、有力代替AOTI/CUDA又は既resident batch数違いを同総費で選択可、選択理由と実batch/queue/tail/初期化回収費を報告。新engine/model取得や新env同期0、必要既engine存在不明なら具体不足と代替を返し研究全体停止0。
GPU推論専用VRAM6GiB/1job<=30min、最大累積推論60min（4h内最大4sciencejob/各<=900s、2比較+必要資格・修復含む）CPU2logicalまでworker2/inference4（異なるphysical、他ownerと実配分調整）、currentRAM3GiB。最大96trajectory=同48family active24/48条件各48、canonicalは一条件の36train/12選定val。qualification0game、最初16complete点は同job内で品質/時計forecastし別16gameを増やさない。最大合計10000000NN/processed明示実装上界。前枠500kNNで2slot打切りを踏まえ、完全局数/終局/UNKNOWN/未開始の分母を保持し最大数の完走保証を捏造0。対戦棋力評価ではなく教師生成。同K既固定root少数でπ/action/value/合法/history/teacher意味資格、GPU数値差tolと意味範囲を結果前固定、全tree bitexactを必須gate0。有効π/rootmean/z/P2/history/groupを保存、rootmeanをleaf真値へしない。
新data+必要modelsummary/temp/Gitforecast128MiB、sharedrelease増分128MiB+新疎WT8MiBまでfresh headroomへ計上。旧2662MiB保持は別、新配分を旧capresetへしない。新deps/model取得0。既生成rawはcompress復元し不要dupは本人生成の復元確認後のみ整理。
出力は train用/選定validation用をgame単位先固定、新未見評価を勝手宣言0。hypothesisへschema/teacher/hash/family/実費を早期引渡し、96全局完了を学習入口gateにしない。初回30分目安でbackend実可否/具体案/最初job又は不足。結果から実装又は生成条件の次判断まで継続。

## 共通契約

ユーザー明示frame22 11:36:03–15:36:03UTC固定。heavy入口15:26:03、正監督15:31:03/monitor15:34:03/保存15:36:03。準備で起点reset0。旧課題caps/原失敗/成績/unknown/累積readonly。全候補一覧 docs/design/ai-nnue-optimization-agenda.md を読み今回担当外の有力案も通常報告へ。通常詳細の再承認/全roleACK0、自律選定・修復・実行を以下scope総費内で継続し重要結果で統括へ理由と次案を返す。単一試験不支持を方式全体棄却しない。本人ready/show goal+self/no pause/assigned→claim/実tool開始を短報。
main現役Rust/Python。旧checkout撤去済み、assetsはresearch-paths.json v2/scripts/dev/research-assets.pyで実path/hash解決。旧Node/trainer復活0/毎回Git復元0/恒常mirror0。新取得/環境更新/GPU学習/製品採用push公開/未知削除0。ORT_DISABLE_TELEMETRY=1をframework import前。173正式198非学習、開封testは選定に戻さない。科学source版/条件/予定分母を結果前束縛、管理失敗と科学不成立/条件不支持を分ける。
aggregate CPU4logical（運用1含む）/RAM8GiB（運用1GiB含む）/保持cachetemp+有効unused12GiB。旧予約は下記新scopeへ自動reset/重複free0。以下新配分はfresh92保管current+forecastへ含まれた確認headroomのみadmit、静的調査は全史/runtime待ちgate0。heavy本人currentloaded/configcontract/hash/正identity/CPU/RAM/GPU/admit。複数ownerの固定時間比較を重ねず実job開始/停止を短報、LLMactiveだけで物理busy0。長job背景実行→jobID/notesbackup→Idle→completion一度、盲目poll/retry0。本人子wait/currentidentity不在、源停止path/SHA/必要data復元を引渡す。Git/index/commitは統括だけ、本人privateindex0。全変更コード対象formatter適用→check/lint/必要test、原科学源archive不変更。source停止15:15目安/科学全停止15:27/必要保存15:30、親自動延長0。重大提案は結果待ちまで遅らせず報告。

## 有効追補

# 273 追加実配分: CPU topology と teacher cache 接続

同quoridor-4lc.273の有効追補。CPU2/3同physicalによる資格未実施を保持し、worker logical2 / inference logical4の計2logicalへ明示再配分する。CPU上限・RAM3GiB・VRAM6GiB・NN10m・MAX4・48family/96trajectory/36train12selectionval・期限は増やさない。host2physical reserve/affinity/cgroup/quotaを既optin admissionで再確認。275 CPU3とはworker2がsiblingsなので、固定時間比較は自然停止後に行い、GPU全job費測定とも重ねない。新current runtimeは276 receipt scheduler1233793/tick45593355・monitor1235182/tick45599721で、旧identityを代用しない。各入口で本人freshadmitする。

新solewriter pathを273のmanagedWT /workspaces/quoridor/.worktree/frame22-teacher に追加する: crates/quoridor-data/src/lib.rs の write_tensor_cache と、その変更を検証する同crateの必要testだけ。問いは新教師入力の露出maskとPython/native parityを、既cacheから追加feature再計算・別JSON全コピーなしで可能にすること。現在TeacherRowにあるstate_key/history_key/ply/feature_signature/side/ids/distanceを rows.jsonl の同rowへ保持する。idsはP1/P2順かSTM順かを名称とschemaで明記（現TeacherRow idsはP1/P2、tensor xはSTM順）。distanceは現STM順f32とsideを保存。history_keyからfullhistory/countを捏造しない。現在tensor x/distance/labelsのbytesと意味は変更しない。新fieldは既source由来でlabelsから計算しない。

必要検証はP1/P2のmetadataとtensor対応、既tensorfiles byte同一、eligible/allow_test境界・欠測を必要範囲で確認、rustfmtと該当crate test。新copy/cacheには原manifest/SHAとcanonical condition/family/登録split/全planned分母をbindし、train/selectionvalは別manifest、兄弟条件の二重露出0。新metadata等は既data128MiB/build128MiB内でforecastし、足りなければ具体量を通常報告。独立レビューは実装停止pointを受けて統括がsource/test根拠を確認し、274がPython入力・label-free mask/parityを別ownerとして確認する。全roleACK・96完走・全稿を科学入口gateへしない。

既qualification/生成規則/ラベル/モデル/K64/温度/順序/総科学budgetは変更しない。CPU topology拒否・旧数量v1/v3未実行・276停止窓を保持。登録済みcanonical片conditionの完成groupsを早期immutable handoffし、274 Bprefix12/24/36の判断を可能にする。source停止path/SHAと必要cache interfaceを次通常報告へ。
