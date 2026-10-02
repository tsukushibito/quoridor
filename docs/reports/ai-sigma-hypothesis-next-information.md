# SIGMA-NEXT-INFORMATION-CHOICE / quoridor-4lc.139

**次はcandidateの実parent meanを記録したFPU一因子対照を選ぶ。監視負荷対照は今回不採択、現政策は維持する。** 問いは「未訪問Q0を変えることで、候補の判断を有用な方向に変えられるか」。費用境界を理解したこと自体を棋力への進展としない。最大1次実験の提案であり、今回NN/model-load/AIWorker/Chrome/game/build/GPU/取得/委譲0、actual_go/係数採用/改善・NI/Sigma認定0。

本人受領18:13:36.946567UTC、ready/show goal+self・pauseなし・本人担当後139のみclaim。開始RPCはturn/steer01a0fdce-1b14-74c3-8568-666580961af3 accepted。処理18:38:36.946567、新command18:35:36.946567、提出18:48:36.946567早側、親枠9/23:20:59・CPU4/RAM8GiB/保存12GiBを継承。旧136source/子停止後の自己新scope。138は読取時intakeのみ、裁定未着を開始gateにしない。

必要報告・既analysis/proposals/sourceだけを参照した。追加raw根読取を0と事前固定し、archiveコピー/展開、新状態/全棋譜/全deep解析0。136のbounded6根結果をcompactで再利用することと、今回の追加根0を区別する。137の保存CP列はroot件数と別分母で扱った。

| 判断候補 | 次の実装判断へのつながり | 今回の選定 |
| --- | --- | --- |
| 監視負荷対照 | 監視を軽くする判断は可能。ただし参照1状態の量変動が候補の手品質を制限する証拠は未着 | 保留。候補の品質対照で量不足が示されるか、安全運用自体が必要な場合に再検討 |
| candidate FPU一因子 | 実meanによる未訪問選択と完成手の変化を直接試せる。品質出口が悪ければ変更を止める | 最大1次案として選定 |
| 深い有限oracle | policyに依らないラベルが得られれば価値がある。現中盤の非自明な認証済みラベルは無い | 今回は選ばず、列挙深さを自動拡大しない |

独自の小算術では、137のaccepted CP列40件から各共通KのActionを再照合し、6組・49比較で一致した。steady採用backup8/9/15とAction154/154/162、APIawait中央値38.02515/36.72754/20.88013msは保存列から再算して一致。sample3のActionはK2で162、K8で154、K14で162と戻る。多いKほど手が一方向に良くなる証拠ではない。共通K根edge全bits一致は137owner主張として参照し、今回独立raw bits監査とは呼ばない。CPU→Worker未対応、端点欠測・guardian CPU不在・監視負荷未校正を保ち、APIawaitを純NN/CPUへ変換しない。

134全8compact winner/forced_sideから再算した得点は135独立replay集計と一致した。入力3の強制161は[1,1]、133は[0,0]、入力4の32/42は両[0,0]。これは固定Sigma後続policy依存の局所出口である。候補finish-firstは入力3を161→133へ変えるため、参照への接近を改善とする根拠はむしろ弱い。現候補の119弱さ/長期品質/単一原因とは分離する。

FPUを選ぶ根拠は、136入力3/4でcandidate訪問済み親Qが20/20・29/29すべて負、未訪問Q0がそれらより楽観的で、配分への直接介入が未実施な点である。ただしcandidateの真parent meanは保存に無く、正/負やFPU方向は未確定。現kernel Nodeはvisitsのみ（kernel.rs:200）、未訪問Q0（:535）、交互backup（:493/:741）、finishはvisits→prior→seed（:359）。参照FPU実式はnode mean−.2sqrt(visited basePrior和)。edge平均・参照mean・人工値で欠測を埋めない。C/FPU/N/f32/order/finish/capsの束比較を単因子効果にしない。

[最大1次案](../../research-data/ai-sigma/139-next-information-choice/next-experiment-v1.json)は以下を結果前固定する。現在の実行許可ではない。

- **唯一の変更:** candidate未訪問Q0→f32(node実valueSum/visits−.2sqrt(訪問済みoriginal prior和))。C1.5/√(N+1)/visited-edge Q/f32/order/seed1979/finish/caps/backend/modelは固定、固定Sigmaを診断変更へ置換しない。両variantに同じ実node mean・FPU項記録を追加し、各node訪問incrementと同時に自手番valueを足す。初期根NN、terminal、async実経路、capsで作られないleafを区別する。記録費を無料としない。
- **機構段階:** 132登録入力3/4の2状態、旧baseline・記録付きQ0・FPU各K32＝最大6検索/192手NN、startup6別。Kは根込みcompleted backupで、terminal-noNN/NN開始・完了・採用/棄却を別に記録。順は3旧/記録/FPU、4FPU/記録/旧。1検索watchdog10秒、job120秒。これはsame-completed診断で通常T500の速度比較ではない。旧対記録付きbaselineの必要features/NN/prior/rootedge/Action parity不成立ならFPU評価を止める。
- **品質出口:** Action不変なら終了。入力3が133へ変われば既有限出口で不利なので採用を止める。未評価の新しい合法Actionが出た登録状態だけ、原政策手との同時対照を固定Sigma後続で各2反復、順baseline/FPU/FPU/baseline、最大2状態・8rolloutに制限する。T500/total200ply/seed/typed失敗・partial・停止を先固定し、全入力・全機構結果を保持する。旧既知枝を同条件で追加反復して好結果を探さない。条件分岐は今固定し、結果後の入力補充・標本増0。
- **結果別判断:** parity失敗/mean欠測は未成立。訪問だけの変化・同手・局所同得点/反復方向混在は現政策維持して枝終了。局所悪化も不採用。新手の同時局所対照が好方向かつ入力3悪化無しなら、別配分のcandidate policy診断を検討する有限根拠に留める。全体採用/棋力因果/正式NIを発行しない。

単独writer候補はexperimentの研究kernel/copy/adapter、criticは必要mean/backup/parity/局所集計のみ。予想は負の実FPUが未訪問配分を減らす可能性であり、集中や参照距離を成功基準にしない。反証は負FPUでも手不変、又は変更手の品質出口不改善。後続が両fixedSigma・事後2状態・同seed反復という交絡が残る。sameK≠同NN/CPU/wall、計測による費用、深部branch量も記録する。通常500ms candidateの改善はこの計画だけでは未評価。

費用見積りはwriter45分＋次配分cached build CPU0単1/RAM2GiB≤120秒＋機構runtime CPU2/thread1/RAM6GiB≤120秒＋任意品質最大8job各180秒＝1440秒＋独立保存15分、最悪88分。品質の思考上限は8×200×.5=800秒で外job1440秒と分けた。品質前終了ならその分は実行しない。未来保存64MiB forecastはexperiment既予約を統括が確認して配分する案で、今回の追加予約0。残枠・安全停止・cached build/headroomが不足なら実施しない。局所品質に新情報が出なければ監視実験やoracle増量へ自動連鎖しない。

136 d13bd5b5/05d20e4、1347af16352/bd339e21、1357dd43b08/5d266e04、137data437f401f/handoff4635ab3/測定451f5007へ必要hashでbind。原成果/source/kernel/model/環境/defaultindex/role/registry/92はreadonly。自己static3runはexit0/guard0、20ms観測RSS最大33,632,256B<448MiB、観測CPU0、管理jobwall計約.1085秒。初期ready/show/claim/read/生成等の短命PID/RSS・全commandCPUは未観測で0補完しない。旧保守8,531,968Bを減額せず自己current/forecastをcombined14MiB内に確認、既16MiB/追加予約0。保持・未使用予約・過去peakを分離する。

本文前に必要input afterhash、自己3job6identity現在不在・outerwait完了・source停止を保存した。現在不在≠自然/全期間保証。自己コード/Git/run/全attempt/必要command・結果・資源・停止は[自己data](../../research-data/ai-sigma/139-next-information-choice/)へ。再現は自己supervise.py <new-run> python3 check.py（期限設定は新配分で、旧期限の迂回0）。backup/report後coordinator受入れ待ち、goal/他者close0。
