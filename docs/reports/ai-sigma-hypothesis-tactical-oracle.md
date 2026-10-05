# SIGMA-TACTICAL-ORACLE / quoridor-4lc.127

hypothesis → coordinator、契約1・枠8。**NN0の有限戦術ラベルを4合法局面に作成できた。** 即勝ち2局面に加え、131合法手中129手が相手の次手goalを許し、H(3,0)/H(4,0)だけが回避する非自明局面を認証した。全て同じ自明問題という説明は弱まる。長期勝敗・500ms AIの失着・棋力/NI/Sigma同等は未測定。NN/model-load/AI Worker/game/build/GPU0、actual_go=false。

ready/show goal/self、pauseなし/本人割当確認後127だけclaim。受領13:51:45.164866 UTC、処理14:06:45/newrun14:01:45/提出14:11:45。Chrome監視は親の重job停止14:05:49を早側に採用し、延長0。121 P2の有限認証部分だけ実施し、126の量差混在・原結果を変更0。

事前登録は4幾何規則・順序・各attempt8上限。初期Stateから各手をRuleA合法集合で確認して進め、pawn/壁残数/手番/historyを直接改変していない。各case最初のattemptで適合、棄却0。root込み1＋適用したroot child＋適用した相手childをnodeとして、各20000上限を固定した。全root合法手の即goalを先に調べ、即勝ちが無い場合だけ相手全合法手の即goalをdepth2で列挙する。

| case | prefix ply | root合法手 | node | 有限ラベル |
| --- | ---: | ---: | ---: | --- |
| own-near-goal | 14 | 132 | 133 | 即勝ち1手、root全件完備 |
| opponent-threat | 14 | 131 | 16932 | 129手は相手即goal可能、2手のみ回避、depth2完備 |
| both-near | 16 | 132 | 133 | 即勝ち1手、root全件完備 |
| wall-protected-threat | 16 | 124 | 15047 | 既設H壁により全124手は次手即負けを回避、depth2完備 |

即勝ちcaseの相手分岐は仕様通り未列挙で、空集合を「相手脅威なし」の認証にしない。防御caseのsafeは次手即goal回避だけで、長期勝ちを意味しない。wall-protectedは失着尺度が全手同点になる負対照であり、難しい問題として水増ししない。合法実入力の即goal/脅威assertとcap1 mockが通過、上限停止は未解決で安全手0。200手draw/深い戦略/他ルール一般性は未認証。

生成・認証はChromium mainのみ、Nodeは起動/外監視/終了後保存。モデル/探索Worker/2AI Worker/SABを起動・改変0。AI評価関数は使わず、共有RuleA Stateで合法列挙する独立checkerである。ただしRuleA自体の独立実装/真のルール正しさを今回証明したわけではない。

初回admissionは/proc/exeの外部サービス読取拒否でfalse。手順ミスで次のNode commandまで進んだが、monitor deadlineが親停止より遅い自己設定を拒否し、Chrome/ownership生成前で停止した。原失敗を保持。専用入口にadmission true/30秒以内必須を追加し、監視期限を早側に訂正。外部docker-init/shell/keepalive/SSHは読取可能なUID/name/argvで分類し、子も別走査。unknown/interpreterのexe読取errorは引続き拒否する。125/126記録81identity現在不在、外Chrome/研究heavy無し、available RAM約20.8GBを確認後r2を起動した。hostmemoryは親研究RAM台帳とは別。

r1はChrome0/Node exit1、r2はbrowser NN0/exit0、管理wallは合計約6秒/90秒内。r2観測currentRSS peak1,147,957,248B<5.5GiB、全観測TID CPU[2]。Nodeheap192MiB、AS制限0、専用TMP/XDG、single-root/subreaper/所有ledgerで監視。本文前にbrowser timer0/monitor callback完了/innercontrolled remaining0/outerownedwait remainingunknown0・記録33identity現在不在を保存した。controlled強制回収と現在不在を自然終了・全期間保証へしない。初期短command/全CPU/瞬間peakの欠測を保持する。

旧hypothesis保持を保守6,164,480Bとして減額せず、自域/Chrome temp/保存とcombined14MiB guardで監視した（peak7,708,672B、最終量manifest）。既16MiB予約内、親12GiB追加0、未使用予約と保持実量は別。全旧量/全owner/Gitobject増分は独立再測定していない。原データ削除0、21memberの必要run/失敗/所有ログarchiveをstream復元照合し、source/config/合法history/ラベル/停止を研究Gitへ。

**次判断:** この狭い尺度の正解ラベルは得られたので、別配分があれば同入力で現candidate/固定Sigma/意図的root1 stressを比較できる。優先は非自明なopponent-threat＋即勝ち＋wall対照で、全4が独立棋力標本ではない。候補だけ認証失着なら具体的terminal/search原因へ、両側なら共通モデル/探索へ、全passならこの自明範囲の反復を止める。root1を普遍的弱者とは仮定しない。今回12根AI評価許可0、枠残量で次実行が可能かは統括配分へ返す。

再現command: `timeout 60s taskset -c 2 env UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 python3 -B tools/ai-sigma-tactical-oracle/runner.py --config <new-config> node --max-old-space-size=192 --max-semi-space-size=4 --no-node-snapshot /workspaces/quoridor/.worktree/ai-sigma/tools/ai-sigma-tactical-oracle/entry.cjs <new-run-id>`。別の現在配分・新出力を使い、admissionを新時刻で確認する。

詳細：[生成/ラベル](../../research-data/ai-sigma/127-tactical-oracle/labels-and-inputs.json)、[事前登録](../../research-data/ai-sigma/127-tactical-oracle/preregister.json)、[停止](../../research-data/ai-sigma/127-tactical-oracle/runtime-source-stopped-before-report.json)、[復元manifest](../../research-data/ai-sigma/127-tactical-oracle/archive-manifest.json)。自己source/process書込み停止後backup/report、受入れcoordinator、goal/他者close0。
