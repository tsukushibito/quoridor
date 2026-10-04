# QF1視点・教師対応と距離基準のNN0独立裁定 / quoridor-4lc.199

有限支持：固定12witnessで系統的なview/field誤対応を検出せず、既距離情報には再利用validation教師を予測する情報がある。全NNUE特徴無効・教師不良・容量・過学習の一意原因は確定しない。新NN/model/forward/session/GPU/train/game/test再開は0。

196はcoordinatorの196-finite-acceptance.jsonを確認し、本人close/backupした。199は新ready/show goal+self、pause無し・saved critic割当を確認してclaim、00:46台に静的実開始。旧196の結果/期限/charge90/180秒を保持し、本199は新static120秒配分である。newcommand01:00/科学stop01:05/process01:15/提出01:25の早側を維持する。

教師値/lossを見ず、train96+validation24のlabel-free metadataからopening8/12/16/20/24/28×STM P1/P2、rowID辞書順最初の12枠を固定した。fixed-witnesses.json SHA 5e2a47eb0ce4a8a9ac7c1bc32d1d5c6aa43119c21f08253dc54fba85f62b3cd6。欠測0、worstgame選別0。規則の結果、全12はtrain01の6gameに所属する。validationや全履歴の変換保証へ拡張しない。

独自Python算術ではshared RuleA/変換関数/evaluatorをimportせず、元openingと直前row actionから盤面・壁所属を復元、独立BFS距離・float32 bitsを導出した。648のP2上下反転とQF1 P2 180度回転は異なる表現規約として別々に計算し、両者を同じ配列へ無条件にコピーしない。pawn、H/V壁の占有とanchor、remaining own/opponent、STM concat、距離f32bits、648全channel、canonical QF1 SHAは全12で保存raw/teacher/journal/metadataに一致した。

| opening ply | STM | witness rowID | raw→teacher→label / 入力 |
|---|---|---|---|
| 8 | P1 | native194-train01-01-GPU24-ply-10 | PASS |
| 8 | P2 | native194-train01-01-GPU24-ply-11 | PASS |
| 12 | P1 | native194-train01-02-GPU24-ply-12 | PASS |
| 12 | P2 | native194-train01-02-GPU24-ply-13 | PASS |
| 16 | P1 | native194-train01-03-GPU24-ply-16 | PASS |
| 16 | P2 | native194-train01-03-GPU24-ply-17 | PASS |
| 20 | P1 | native194-train01-04-GPU24-ply-20 | PASS |
| 20 | P2 | native194-train01-04-GPU24-ply-21 | PASS |
| 24 | P1 | native194-train01-05-GPU24-ply-24 | PASS |
| 24 | P2 | native194-train01-05-GPU24-ply-25 | PASS |
| 28 | P1 | native194-train01-06-GPU24-ply-28 | PASS |
| 28 | P2 | native194-train01-06-GPU24-ply-29 | PASS |

worker.cjsはrootNN=first_NN.value、rootmean=cp.root_mean、leafNN=last_leafNNを別fieldとして保存。Rust root_mean=root.sum/root.visits、backupは各nodeの手番視点で値を足し親ごとに符号反転する。JSもqValue=valueSum/visitCountと同じ視点規約。exportはrootmean_view=root side-to-moveを要求しrootmeanをtraining labelへそのまま保存、z_stmは独立field。model.pyのinputsはidsをSTM/opponent順に整列し、forwardへside=1を渡すので追加のP2符号反転をしない。12witnessでraw rootNNと保存NN137最後のf32value bits、rawrootmean→teacherrootmean→label、sideとSTM zの対応を確認した。

原CP root_valueSum/全backup traceはwitness rawに保存されていない。従ってrootmeanは最終cp fieldのsource経路と数値bindingまでで、全探索のroot統計を新たに再計算した認証ではない。12witnessの多数でrootNN/rootmean/leafNNは異なる値のまま別保存され、labelをrootNNやleafNNへ置換していない。producer bindingのQF1/worker/schema SHAと実ファイル一致、shared interface packetと両runのsource SHAも別receiptで一致。その他private原sourceは現在の停止source/hashの範囲を明記した。

unsealed原archiveのtrain/validation games.jsonlのみとtrain01の必要raw memberをstreamし、member SHAをmanifestと照合。全rawの複製/展開0。train96+validation24の120全gameで保存最終prefixからpawn終局winnerを復元し、5901ラベルのwinner→STM zを独自算術して一致した。これは保存prefix/goal整合であって全合法性の別RuleA再証明ではない。原173正式holdout、rawtest、mixedstatus/all144-status、旧preview、旧195testlabel/resultperrowは今回未読。

初版checkerは直進actionが隣接opponentを跳ぶ規約を欠いたため、後半gameの最終prefix勝者対応で停止した。失敗source audit-failed-r1.py / compute.stderr / failure-r1.jsonを保存し、占有に基づくstraight jump decodeへ修復した。最初の差を元教師科学negativeへ変換しない。追加のmetadata source binding初版は未読common.pyをreadsetでlookupして失敗したため、source-bind-failure-r1.jsonで記録し停止source SHAを直接確認する管理修復を行った。

距離診断の式は結果前に1案だけ固定。s=f32(distance opponent)-f32(distance self)、train96の各row重み1/(96*n_game)、非clip WLSからa,bを求めて予測clip(a+b*s,-1,1)。validationをfitへ使用せず、追加特徴/多式/grid/sweepなし。train-only定数は同重みのrootmean平均。

a=0.0629424241510423、b=8.27642510742221（正）、mean(s)=-0.00629239449270931、Var(s)=0.00440828518183899、Cov(s,rootmean)=0.0364848421596495。定数=0.0108638923857777。分散非0なのでWLS係数は一意。正のsは自分の経路が相手より短いSTM状況を表すが、正slopeだけで視点や棋力を認定しない。

| partition / 基準 | rows/game | rootmean row MSE | rootmean game MSE | 真z row MSE | 真z game MSE | z符号 row/game |
|---|---|---:|---:|---:|---:|---|
| train/distance | 4653/96 | 0.413910127 | 0.405943742 | 0.720498536 | 0.683917260 | 0.739308/0.753522 |
| train/constant | 4653/96 | 0.706722641 | 0.724320391 | 0.999907891 | 0.999891792 | 0.504836/0.505206 |
| validation/distance | 1248/24 | 0.489313868 | 0.485146815 | 0.843601512 | 0.822535033 | 0.710737/0.720326 |
| validation/constant | 1248/24 | 0.666005155 | 0.678780468 | 0.999909103 | 0.999881918 | 0.504808/0.505433 |

全train4653/96・固定val1248/24は同maskの全eligible。各6cohortも全分母を残す。

| partition / opening | rows/game | 距離 rootmean game MSE | 定数 rootmean game MSE | 距離 z game MSE | 定数 z game MSE | 距離 z符号game |
|---|---|---:|---:|---:|---:|---:|
| train/8 | 918/16 | 0.469496969 | 0.715425810 | 0.754097628 | 0.999913756 | 0.717398 |
| train/12 | 848/16 | 0.317722564 | 0.622595909 | 0.677782417 | 0.999852361 | 0.748393 |
| train/16 | 806/16 | 0.364529199 | 0.705332239 | 0.699809326 | 0.999884843 | 0.782446 |
| train/20 | 832/16 | 0.442881625 | 0.748056801 | 0.678254776 | 0.999940050 | 0.715749 |
| train/24 | 638/16 | 0.432963686 | 0.777238860 | 0.669951569 | 0.999851041 | 0.776247 |
| train/28 | 611/16 | 0.408068410 | 0.777272728 | 0.623607846 | 0.999908705 | 0.780898 |
| validation/8 | 252/4 | 0.327327084 | 0.495400184 | 0.987078484 | 0.999923600 | 0.647198 |
| validation/12 | 230/4 | 0.431525994 | 0.723202020 | 0.690210713 | 0.999837846 | 0.793589 |
| validation/16 | 201/4 | 0.611404825 | 0.555408494 | 1.100359672 | 1.000036950 | 0.489493 |
| validation/20 | 202/4 | 0.660449085 | 0.818382478 | 0.831280045 | 0.999638243 | 0.776009 |
| validation/24 | 171/4 | 0.275052028 | 0.886472133 | 0.477863327 | 0.999736846 | 0.917818 |
| validation/28 | 192/4 | 0.605121871 | 0.593817496 | 0.848417955 | 1.000118024 | 0.697851 |

保存QF1の同train96/固定val対象との数値比較（再forward0、saved curve receiptの比較）。全BESTstep0でありLASTを採用候補へ救済しない。

| output | partition | rootmean row/game MSE | z row/game MSE | z符号row |
|---|---|---|---|---:|
| WD0/initial | train | 0.719629094/0.737418315 | 1.013610065/1.013701873 | 0.495164 |
| WD0/initial | validation | 0.677447061/0.690175574 | 1.014215447/1.014144988 | 0.495192 |
| WD0/LAST | train | 0.001974719/0.001781704 | 0.305869877/0.277313827 | 0.894692 |
| WD0/LAST | validation | 0.976987707/1.009580396 | 1.372112264/1.408749273 | 0.543269 |
| L2WD01/initial | train | 0.719629094/0.737418315 | 1.013610065/1.013701873 | 0.495164 |
| L2WD01/initial | validation | 0.677447061/0.690175574 | 1.014215447/1.014144988 | 0.495192 |
| L2WD01/LAST | train | 0.018164023/0.016614357 | 0.287471465/0.259801256 | 0.902858 |
| L2WD01/LAST | validation | 0.928204843/0.957840742 | 1.302474477/1.333014963 | 0.511218 |

距離基準はtrainとvalidationで定数より低いrootmean/z MSEと高い符号率を示す。既QF1入力に含まれる距離に少なくとも予測情報があるため「全特徴無情報」の説明はこの範囲では支持しない。これは再利用validationの記述的診断で独立testではなく、過学習/teachernoise/容量/最適化の一意原因は分離しない。rootmeanは探索教師、真zは保存終局結果であり両者の意味を分ける。

次案は最大1：trainのみで凍結したこの距離基準を初期valueへ明示し、学習側をrootmeanとの残差に限定する最小NNUE対照を次の許可枠で判別する。clip後の基準へ残差0ならこの保存基準を再現する仕様、固定validationで未学習基準を下回るかを確認してから新候補をfreezeする。今回/旧testへ条件選定を戻さず、新独立testは別に結果前固定する。本taskで自動実装/学習/新testを開始しない。全NNUE移行や無限速度診断を入口にしない。

資源/停止：00:46:20 label-free固定、00:55:25の現heavy空/92ownedNone/直前観測00:55:17・次01:11:55を記録して短NN0 jobをadmit。retry直前00:56:50にはownedNone、物理fullscanは初回admitと終了00:57:23に保存しており間の全host非競合を保証しない。成功00:56:51 exit0、wall0.695717秒/過去peak RSS78929920B<448MiB、PID3845257現在不在・source科学子停止/CPU0解放。初版失敗の実wall未捕捉は未知のまま60秒保守課金、全静的charge90/120秒内として停止。旧196charge不変。新2MiB＋Git/一時metadata1MiB込みforecast102347236<既112MiB、旧unknown88190086保持/親増額0。own小保存は256KiB目安以内、default/privateindex編集0、in-memory Git/必要bytes復元・Beads notes/backup・coordinator受入れcloseへ。
