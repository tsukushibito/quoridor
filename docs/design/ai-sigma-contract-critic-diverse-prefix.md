# SIGMA-DIVERSE-PREFIX-INDEPENDENT / quoridor-4lc.122 / 契約1・枠8

既critic 01a0f31d-8227-7e03-a7e6-915b4918c11b → coordinator。研究目標/親現行枠8/common/120改定critic/実行記録規約の全文を継承。ready/show goal,self・pause無し/本人担当確認後本issueのみclaimし受領開始を報告。119の保存された棋譜・時計・責任分母を必要範囲で独立裁定する。正しい集計と、棋力差/改善を検出できる評価設計の妥当性を分ける。統括の判断を追認する必要はなく、独立した不明/反証/次案を返す。

原119停止JSONは research-data/ai-sigma/119-diverse-prefix/runtime-source-stopped-before-report.json、実SHA624c0728471aea3a389f68c0fe7d4b8a48b6afb0fdc3da804888447e69ad3b3f。pair1 tested8124d876ed69128f16485f8d6b7216171e792789、pair2–8 tested532c87349fa0baf233fa905f5f3d8c88a5560a9f。prefix-document.json/preregister.jsonとprefix119-pair{1..8}-r1.{summary.json,manifest.json,tar.gz}の固定保存を参照。最終source/data/handoff Gitはまだ保存中で、同turnへ到着後追送する。先行固定archiveと最終未着を区別し、原119保存writerへ停止/追加gateを要求しない。

AI前固定8prefix:生成seed31001〜31008/ply4,5,8,9,12,13,16,17、P1/P2各4、全accepted attempt index0（総8生成attempt）。実探索seed1979、各候補色1→2、C1.5/固定Sigma/同model/ORT1.21.0 CPU/Wasm/threads1/T500/cutoff402/adopt411/専用2Worker各SAB/browser main対局を維持。原owner集計は16goal・候補W4D0L12・764正常合法公開、late/初回無し/AI責任loss/infra未完了0、startup48/手NN7764。全8pairscoreは旧117/118と混ぜず、prefix既plyと今回新公開数を区別する。ランダム合法prefixは均衡/IID/代表性を保証しない。

新NN/model-load/GPU/対局/holdout生成/build/取得0。先に必要source/manifest/schemaを小静的確認、必要archive memberだけstream取得して自域へ一pairずつ展開。118のbrowser checkerを読み再利用できるが、原119の集計をrequireするだけを独立算術としない。実browser内でprefix/history/key/手番/色/Action/SAB完成sequence・generation/不変body/goalと全16棋譜・764公開をreplayし、故障未完了分母を確認。RuleA共有の独立性限界を明記。Nodeは外側起動/監視/回収/終了後保存のみ、Node審判/毎手時計/必須Node replayに戻さない。大入力はbrowserへJSON textで渡しbrowser内parse等を用い、既OOM失敗を反復の前提にしない。

全保存公開stampと時計の必要算術を照合し、相手t0<旧ACK・自Worker旧zero後t0/自待ち・旧返却discard・新API開始/Worker停止/ACKwallを分離。起終clock区間の有限支持と途中drift/内核CPU/hard realtime未保証を保持。公開後新NNの確実/可能の分母を保存情報に合わせ、未観測を0補完しない。最大8root sampleは数値読取前に選定規則（両engine/P1P2/各prefixをできる範囲）を固定し、648bits/137NN shape/finite/strict[-1,1]/engine固有順/ActionP2/prior/訪問規約をbrowser内検査。固定golden参照の有無を分け、全深部一般NN一致やrootparentQ補完をしない。新NN0、全764rootgateを一律に追加しない。

分類と棋譜を確認した後、どの問いにこの評価が答えられ、何が未判別かを独立に述べる。全pair勝敗・同側winner/AIscore・完遂分母を用い、同側勝利が多いことを自動的な無価値認定としない。一方先後交換だけで棋力差への感度が成立したとも呼ばない。最大1つの次評価案に、結果が選定を変える分岐/最小費用/交絡を示せる。121のhypothesis調査を待つ新gateではなく並行見解として報告する。正式NI/評価校正/全faultproofを診断入口に追加しない。

119最終guardはproc/exe+argv/read-error/stop-unconfirmed launch0をNN0確認したが、測定8124/532版はargv0識別だった。過去admissionを最終guard成功へ遡及格上げしない。原helper失敗・旧policy/結果を保存し、新版で旧gamesを再分類しない。原21run/1517identity現在不在と当時innercontrolled/outerwait/Modeldrop/monitorcallbackを別確認。現在不在は自然終了/全期間保証ではない。自checker/設定は同scope総予算内で修復可、失敗ログ/版と未実施を保持する。

単独writer: tools/ai-sigma-diverse-prefix-independent/、.artifacts/ai-sigma/resume-20261002/DIVERSE-PREFIX-INDEPENDENT/、research-data/ai-sigma/122-diverse-prefix-independent/、docs/reports/ai-sigma-critic-diverse-prefix.md。119/121/共有source/model/common/roles/registry/92/main/default indexはreadonly。契約は統括所有。

静的CPU[0]単logical/RAM1guard896MiB、各60秒/合計180秒。Chrome NN0でもCPU[2]単logical/RAM6GiB currentRSSguard5.5GiB、各180秒/総browser360秒、起動前119 heavy停止/現在外heavy0/headroomを確認し直列。同役二重起動/pause/所有/資源を守り、LLM active数拒否0。保存new32MiB guard28/既critic128MiB・combined112MiB内、予約追加0。現保持と未使用予約を確認、必要member一pair展開→必要結果Git保存・原正本不削除。現在量不足ならコピー量を減らすか不足/未完了を返す。

処理は受領30分又は13:10UTC、新runは受領25分又は13:05UTC、提出は受領40分又は13:20UTCの早い方。親CPU4/RAM8GiB/保存12GiB/14:05:49新重job/14:10:49監督/14:13:49monitor/14:15:49終了を維持。本文前source/Chrome/子停止・必要hashafterを固定、必要Git/入力/command/開始終了/失敗/再現と必要archive復元を記録しbackup/report→coordinator。受入れは有限支持/不支持/不成立/未完了、正式公平性/NI/Sigma同等/actual_goは未認定。goal/他者close0。原最終handoff未着なら担当と未確認を明記する。
