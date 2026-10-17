429.1の保存学習分析は完了した。Wには「この更新量で新分布のlossが収束した」という証拠がなく、Fにはこの設定での訓練・検証の大きな乖離がある。ただし、Wの追加学習不足、データ量不足、序盤不足、元重みへの依存のいずれも原因として確定しない。新V lossの改善から独立棋力の改善も導けない。今回の実行は保存423/426の小さな表・設定に対する算術だけで、新しいモデル読込、forward、fit、Search、solver、bootstrap、RAW/NPZの読取、旧成功解析の再演は0である。

出典は[423の保存報告](/workspaces/quoridor/research-data/ai-sigma/nnue-teacher-refresh423/report-ja.md)と[426の保存報告](/workspaces/quoridor/research-data/ai-sigma/nnue-independent426/report-ja.md)、そこから結んだcurves、family-MSE表、実training設定、最終変換countsである。[result.json](result.json)に今回必要な設定と算術、[selected-refs.json](selected-refs.json)に小さな入力のSHA/size/mode前後一致を保存した。旧モデルの記述子は設定内の参照情報だけを保持し、payloadへアクセスしていない。

Wの四観測点は次の通りである。Tは選択3763入力、Vは2498行/52family、公開T panelは固定8192行である。

| 更新 | 新T row-MSE | 新V row-MSE | 新V family-MSE | 公開T panel MSE |
| ---: | ----------: | ----------: | -------------: | --------------: |
|    0 |  .871006774 |  .983188217 |     .945876445 |      .428704088 |
|   40 |  .855771214 |  .974504561 |     .936110020 |      .428783312 |
|   79 |  .839572504 |  .964555184 |     .924908037 |      .429288304 |
|  118 |  .824278179 |  .955988804 |     .915511250 |      .430213381 |

最後の79→118更新ではTが.015294325、新V rowが.008566380、familyが.009396787改善した。family-MSEの1更新あたり差は最初の区間が-.000244161、中間が-.000287230、最後が-.000240943である。中間より少し緩いが、最後も最初とほぼ同じ傾きで、保存点上に平坦化・検証lossの反転はない。BEST118は四つの候補の末尾であり、観測した最適点ではない。設定上限で止まった事実と合わせ、同じデータの長い更新条件を比較案に含める理由にはなる。118以後の改善、最適LR、必要更新数や強さを予測する根拠にはならない。四点間の未観測の動き、gradient、Adam内部状態はUNKNOWNである。

TとV row-MSEの差は約.11218から.13171へ広がっている。両方のlossが下がっているため、この差の拡大だけでWの過学習を確定しない。一方、52familyのうちW BESTで29改善/23悪化であり、全family一律の改善でもない。family-MSEは各family内row-MSEの非加重平均で、全rowのMSEとは違う。保存family表の再平均によって両分母と一致することだけを検証した。独立な信頼区間や追加の有意性を計算していない。

四条件の実設定は以下の通りである。全てoutcome zSTMのMSEと共通入力正規化を使い、optimizerはfresh Adamである。warmupとLRは実learning_rates配列から確認した。

| 条件 | 実初期化・訓練源                | LR warmup → 上限            | draws / 更新 / 最終batch | 実distinct / 反復draws | BEST / LAST |
| ---- | ------------------------------- | --------------------------- | ------------------------ | ---------------------- | ----------- |
| U    | BEST43、全43公開T               | 10更新、1e-5→1e-4、以後一定 | 30104 / 118 / 152        | 公開30051 / 53         | 79 / 118    |
| R    | 同BEST43、公開Tのファイル順減衰 | 同U                         | 30104 / 118 / 152        | 公開29993 / 111        | 118 / 118   |
| W    | 同BEST43、新Sigma zのみ         | 同U                         | 30104 / 118 / 152        | 新3763 / 26341         | 118 / 118   |
| F    | fresh weights、新Sigma zのみ    | 20更新、5e-5→1e-3、以後一定 | 240832 / 941 / 192       | 新3763 / 237069        | 0 / 941     |

Wは旧公開データと新データの混合ではない。Rのsamplingは43ファイルの順に.92^(43-i)で減衰するが、その順を教師の世代や強さと同一視しない。U/R/Wはdraw数・更新数・初期重みとLRが揃う一方、母集団・sampling・実distinctが違う。新VでWがよいことはこの条件内での新分布への適合であり、公開データ一般の無効や新データ量の十分性を証明しない。

W/Fは同じ3763 distinct入力を平均8/64回drawした。これは個々の入力を必ず均等に8/64回見たという意味ではなく、個別visit配列はdecodeしていない。Wの反転drawは15038/30104だった。反転や同入力の再drawを、新しい独立game/familyやdistinct元入力へ数えない。Fは同じTをほぼfitできたため、この小さなTを表現できないことが唯一の障害とは言えない。ただしF LASTのT .000690240に対してV row1.463405845、family1.488976232であり、このLR・更新量・初期化では汎化の隔たりが大きい。F BEST0は実fresh initialのMSE1.0で、BEST43のaliasではない。Fの64露出・10倍LR・warmup差をWと同時変更しているため、初期化の効果だけを取り出した比較ではない。FのLASTの棋力や別設定のscratch学習可能性は未測定である。

BEST選択は同じ52新V family-MSEの最小値、同点は早い更新である。U/R/Wは0/40/79/118、Fは0/314/628/941から選んだ。選択Vの改善は独立testではなく、FはWと観測更新も揃わない。公開fullV419150行は各distinct BESTに一度だけで、curve上の未測定を補間していない。public non-regressionはselectorで無効だった。

| BEST | 新V family-MSE | 公開fullV row-MSE |
| ---- | -------------: | ----------------: |
| U79  |     .944335898 |        .423885973 |
| R118 |     .941504471 |        .423965000 |
| W118 |     .915511250 |        .425680801 |
| F0   |    1.000000000 |       1.000000000 |

Wの新V family改善は初期比約3.21%、T row改善は約5.36%である。一方、同じ公開T診断panelは.001509293悪化し、W BESTの公開fullVはU BESTより.001794829高い。後者は異なる新V選択checkpoint間の比較であり、BEST43のfullV初期値をこの表から捏造しない。公開Vと新Vのrow/family単位、分布、未知の公開game provenanceを混ぜず、trade-offとして保持する。

データ量とcoverageは次のように分ける必要がある。原256生成は全GOALだが、最終T/Vは204/52canonical family、適格T10305行、V2498行、選択T3763行である。適格T distinctは10303、V内distinctは2498、選択T distinctは3763だった。適格Tの2重複と訓練samplingの26341反復drawは別の数である。同じ入力が異なるgame/familyで現れる可能性やラベル競合の全表はこの小集計にはなく、T/Vをまたぐexact input重複数もUNKNOWNである。canonical family分離や各split内distinct数だけから、全軌跡の統計的独立・公開全域との非露出は証明しない。原pilotを変更せず最終fit-viewでID18がVからTへ移った対応も保持する。

| 残壁合計 | 適格T | 選択T |    V | W BESTのV row-MSE |
| -------- | ----: | ----: | ---: | ----------------: |
| 16..20   |   320 |   314 |   76 |       1.159371137 |
| 8..15    |  2217 |  1183 |  558 |       1.078505365 |
| 1..7     |  6685 |  1632 | 1709 |        .974814331 |
| 0        |  1083 |   634 |  155 |        .207639625 |

高在庫の選択T314行はstock16が293、17が21、18..20が0である。元の各game/層<=8 capを上げても高在庫で最大6行しか増えず、欠けた18..20は作れない。4/8/12/16plyの同recipeを増やす量のcohortと、2ply開始によるcoverageのcohortは別の問いである。Vも高在庫76行だけで、426のarena開始はstock4..17、固定7例も最大16だった。18..20の修正効果を旧426が直接測ったとは言えない。低在庫でも3つの強い飽和が残るため、最高在庫coverageだけで全問題が解消するという仮説にも反証材料がある。

W新V全体の符号正答率は.636108887→.640912730、abs(post)>=.99の割合は.393514812→.365492394だった。MSEの減少と比べ、符号変更は小さい。高在庫Vの符号正答率は27/76で初期から変わらない。一方、426の固定7例では全7のlogit絶対値が小さくなっても7/7符号と飽和3件が残った。ply39親のpre4.482471→4.172984、post.999744→.999525がその具体例である。選ばれた少数例を全分布へ外挿せず、飽和の原因や実際の訓練gradientを推定しない。

教師への適合と棋力への翻訳は分ける。Wの教師はSigmaが実際に完了したgameのzであって、Sigma static値やMCTS root Qの回帰ではない。同じ状態のstaticとroot Qも目的・horizon・探索policyが違い得る。保存old-q28の小summaryではq/staticが3/28で逆符号だったが、12旧敗戦から選んだ依存のある例であり、oracleや新q教師採用の根拠ではない。D/Sigmaとの逆符号をそのまま誤教師・敗因と認定しない。

423の固定64familyは72勝56敗、56.25%、保存区間47.66–64.84%で、元区間source bindingのO1制限を維持する。426の新192family/384局では183勝201敗、47.65625%、保存95%区間42.96875–52.34375%となり、事前の下限>50%基準は未達だった。旧区間と今回の区間を再計算・合算せず、違うbookの点推定の違いを重みの劣化や一要因の因果効果にしない。今回言えるのは、選択新V lossの改善がこの独立bookでの棋力改善支持へ結び付かなかったことまでである。劣位・等価・改善不可能の証明ではない。

| 競合仮説                  | 保存結果との関係                                          | 分けて確認すべき条件                                                |
| ------------------------- | --------------------------------------------------------- | ------------------------------------------------------------------- |
| Wの更新不足               | 最終区間もT/V改善、BESTが末尾。必要更新数は未観測         | 同じ大viewの118更新checkpointと長い固定露出条件                     |
| 小さなTへの依存・反復過多 | Wは3763入力に平均8draw、Fは64で大きなtrain/V乖離          | nested small/large、固定drawsで多様性を比較                         |
| 序盤・高在庫不足          | stock18..20が0、cap緩和では埋まらない                     | 総distinctを合わせた同recipe対2plyの別比較                          |
| 元重みへの依存            | W/F差は整合するがLR/更新も同時変更                        | 必要なら同じLR・drawsで初期化だけ変える。今回は低優先               |
| z lossと探索棋力の目的差  | Wのloss改善に独立strength支持なし、static/Qとの違いもある | 未使用bookでの将来の限定比較。現時点でteacher/model変更を採用しない |

Cへは[固定した小本文](to-C4293.md)をmaintained research-session wrapperで直接一度送り、同じ429.3のactive turnへのsteerがaccepted=trueだった。生成BやCの開始・継続をこの分析の完了や返答で止めない。具体案は次の三比較である。全て同BEST43、fresh Adam、同正規化・z loss・reflection、10更新warmupから1e-4、以後一定という実Wの更新座標のLRを出発点にする。

1. 量、固定訓練draws/updates：nested3763対15052 distinctを目安に、両方30104draws/118更新、batch256、tail152。平均露出は8対2。同じ更新点で比較する。訓練仕事量を揃える設計であり、増えた診断T/Vの測定forwardや総wallまで同じとは呼ばない。
2. 量、固定露出：同じ大viewを8平均露出、120416draws/471更新、tail96にする。小viewの8露出より訓練drawsは4倍である。大view自体の118更新対471更新も保持し、可能なら長いrunのcheckpointから比較して将来の無用な重複fitを避ける。これは固定compute比較ではない。
3. coverage、固定総distinct：量のrecipe対2ply開始を同じ実N distinct、8Ndrawsへ合わせる。目安N3763なら118更新/tail152。量と序盤を同時変更した一対だけで原因認定しない。量比較のstock構成も結果非選別で合わせられるなら合わせ、無理なら構成差を交絡として記録する。

3763/15052は保証数ではない。実不足はそのまま出し、反復入力をdistinctへ水増しせず、実Nからdraws/更新/tailを解決する。共通の隔離V、same-input/game/family/stock/露出対応、原423 splitとの対応を保持し、selectorと観測点を将来のfit前に固定する。INITIAL/BEST/LASTと末尾傾向を併記する。同じVで選び続けることを独立検証と呼ばず、既知426結果に合わせたbook選択をしない。新fit・評価forward・arenaの実行許可をこの提案から作らない。

実セッションはthread01a14740-4f03-7652-b060-529179d3d18a、gpt-6.1-sol/max、cwd /workspaces/quoridor、danger-full-access/approval neverを最初の通常command前にactual turn_contextで確認した。既存CycleResources/process guardianを有限に呼び、各helper前の実topology/affinity/freeRAM/peerを保存した。worker16/core8、guardian18/core9、family1GiBはcontrollerを含み、host reserve4GiB、GPU0である。Main leaseやglobal quietを要求していない。解析workerのrusage peakは20,103,168Bで、family連続peakではない。解析本体のguarded wallは.041126259秒である。source/software/LLM/adminや全費、global actual、未観測peakはUNKNOWNを維持する。

[checks.json](checks.json)の検証は四条件のdraws/更新/batch算術、実LR配列長、selector、52family/2498row再平均、coverage合計、比較案の計算だけに限定した。Ruff/Prettierは担当source/docだけへ適用し、終端チェックをcompletionへ結ぶ。初回Prettierでは生成Node compile-cache、C送信後ではuv lockがprivate TMPに残り、最終TMP assertionが失敗した。両方とも子process/handlesのcleanupは完了しており、正確なchild/controller不在を確認後にそのTMPだけを除去した。元STOPと修復receiptを保持し、Cのaccepted送信は再送していない。後続はNode cacheを無効化し、既存guardianの実STOP後に本人TMPを清掃する。最初のPrettierが.gitignore対象をskipした不足は明示的ignore-pathによる限定整形で修復した。解析成功を再演していない。

本人helperの実direct wait/reap、PID-start-boot/fresh identity、handle close、TMP、owned[]/leases[]と一回のaffected OWN使用量は最終completion/STOP/usageへ結ぶ。元423のarena FAILED、R operation FAILED、secondary5UNKNOWN、426 setup FAILEDとNULL/保存scope、全旧費UNKNOWNを変更しない。342.17/323のUSERPAUSE、oldfits96、sealed/newE、現models/weights/seals、product/generator defaults、foreign source、旧RAWは保持する。Main/Git/index/Cargoへの書込みと親429/324の変更は0で、本人429.1だけをowner検証後に通常close/backupする。
