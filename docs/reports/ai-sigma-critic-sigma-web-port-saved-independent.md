# Sigma-Web移植StageA r2の独立保存裁定 / quoridor-4lc.153

151修正版r2の固定5入力×両policy、10検索K32は、保存算術とP2の既Wasm/JS再演算の範囲で**有限支持**する。150の仕様提案から一段進み、実CP・NN要求・探索traceを根拠に基準実装へ再利用できる。棋力・同CPU・全deep・terminal実枝・正式NIの認定ではない。151 StageBの開始条件を追加せず、16局結果を本課題へ取り込まない。

最終目標はNNUE型最高棋力、Sigma同等は初期段階である。今回の支持はPV-MCTSの基準・教師生成・評価基盤としての機構再現性であり、教師valueの真値、NNUE特徴の適切さ、αβ探索との一致や棋力を認めるものではない。

## 版と入力のbinding

- 契約Git `3c3432512f35528ed80b5efefe138940daf24384`。受領2026-10-03 01:52:50 UTC、本人割当・ready/show・pauseなし確認後、01:53:13に153のみclaim。実開始報告・10分内速報を既coordinator App Serverへ配送し、acceptedを確認した。
- 原r1 source `c706326`、raw SHA `75a09f525d85d2ed3f9ffc09e9a97f7e7ff066964086e9b9858e2a67e5a93bb4`。ABI decimal/f32復元前の失敗を保持し、r2成功で置換しない。
- 修正版r2 source `b62cde0`、raw SHA `d37215cbc7914519ca24ab254c5e413d21e780389094faed537280a059c234d2`。build r3は01:39:30.952876–01:39:32.502347 UTC、既binary SHA `500181795b373f69f6f2214ee1a77e12767e2f342e15a56ab5e27d0a0453f2c2`、282,867 bytes。実served `/b.wasm`・config・現在binaryが一致した。
- private source4（Cargo.toml/lock/context.rs/lib.rs）はbuild記録、測定Git、現在bytesが一致。依存9ファイルの現在hashと保存patch7を照合した。共有未Git変更のpatchをGit-only再現へ格上げせず、mtimeがbuild前であることを全期間read auditとしない。
- 実served各routeは測定Gitからadapterを再構成してhash/size一致。path欄が共有原ファイルを指しても、adapted bodyを原ファイルbytesと同一視しない。現在の `/early-page.js`・`/snapshot-cache.js` は151後続変更でr2と異なり、測定版へbindした。サーバーのserved記録であり、browser独立fetchdigestは欠測。
- 最新goal設計Git `017681c` を測定source変更へ付け替えない。原151・共有source/model/kernelは編集・削除0。

## 保存算術の独立検算

ownerのokay判定・検査器を呼び出さず、独自PythonでNN要求のlegal順から探索graphを再構成し、葉valueから祖先ledgerを更新した。保存root CP全320、実select全1,450、backup祖先更新1,770を照合した。

| 入力 | candidate / reference最終Action | 各検索rootN / root子N合計 | 各手NN | 各select数 |
| --- | --- | --- | --- | --- |
| initial-p1 | 13 / 13 | 32 / 31 | 32 | 159 |
| asym-hv-p2 | 67 / 67 | 32 / 31 | 32 | 196 |
| straight-jump-p2 | 31 / 31 | 32 / 31 | 32 | 89 |
| frame10-prefix-13 | 69 / 69 | 32 / 31 | 32 | 153 |
| frame10-prefix-14 | 49 / 49 | 32 / 31 | 32 | 128 |

全CPでrootN=K、root子N合計=K−1、true root mean=sum/N、temp0 finishは訪問最大の先着を確認した。reference公開simulationsはK−1、candidateはcompleted Kであり、異なる分母を不一致へ変換しない。root初期展開/backupはloop外に1回含む。

各実selectで全兄弟scoreを独自再算し、C1、sqrt(parentN)、未訪問parentQ−.2sqrt(訪問済み子basePriorの和)、訪問済み−childMean、strict first argmaxを確認した。visited priorを訪問数で重み付けせず、root初期NNをtrue meanに含めた。葉NN valueと全祖先の交互符号、preN/preSum、全root/子ledgerが一致した。candidate最終保存treeの18,960 nodeのN/sumも再構成したgraphと一致するが、未観測探索枝の正しさを保証しない。

全320 NN要求でrootからのpathに対応するkey/history/side/plyを再算した。保存壁から独自の通行graphとreverse BFSを構築し、全648特徴のf32 bitsを再算・一致確認した。P2の特徴・policy136 permutationと、Rust209の着地点Actionを区別した。壁順は各(y,x)のH→V交互、駒は元direction順を保持する。共有RuleAの合法判定全体を独立実装したものではなく、保存legal setの両policy一致と、後述2入力の実RuleA再演算を根拠とする。

NN136 logits＋valueは全43,840要素でfinite、f32からの正確拡張を確認した。valueはstrict[-1,1]。同入力の両policy間でNN出力・要求key/history/side/features/path・legal順が厳密一致。保存NN出力の比較であり、新しいteacherNN推論や固定golden照合は行っていない。

両policyのpath・訪問・Action・ledgerに離散差0。root prior最大差は1.734723475976807e−18、select prior最大差5.551115123125783e−17、score最大差1.1102230246251565e−16、visited prior和最大差2.220446049250313e−16。独自Python softmaxの最大差も5.551115123125783e−17。混合許容差abs1e−4＋rtol1e−4を維持し、離散差をその許容差で救済していない。

手NNはr2 320、startup6/session2を別記。r1+r2のowner StageA手NN累計640/1024、両run startup計12は別分母。terminal-noNNは全10検索0であり、terminal実枝の独立支持はない。

## 既Wasm/Node VMの追加再演算

`asym-hv-p2` / `straight-jump-p2` の固定2入力だけを実行した。既binaryと保存NNtapeを供給し、実Wasmの全32要求state・CP・traceと、固定JS coreの全32要求state・root CPを比較した。新NN/session/model-load/Chrome/build/gameは0。

両入力とも保存と訪問・Action・ledgerが一致、prior微差最大8.673617379884035e−19。Wasm traceの41件でJSON数値の−0と0が異なった。strict bit/sign equalityと算術同値を分離して保存し、discrete path差へ扱わない。JS/Wasmの全演算bits一致を主張しない。RuleA/game/contextは共有参照で、独立性の限界を維持する。

初回の保存checkerは最小prefix boardにwalls_remainingが無いschemaでKeyError、再演算checkerは−0/0のdeepStrictEqualで停止した。binding checkerでは現在151のserved版をr2と仮定した失敗、patch改行形式の失敗があった。失敗版Git/run/logを保持して自己checkerだけ修正した。原科学結果の補充・置換、NN不一致・棋力lossへの付け替え0。

## 監視失敗と停止の裁定

最後の科学検索終了は01:41:23.263345 UTC。最後の151 Beads読取は01:41:23.011から開始され、01:41:28.166にexit0、そのJSON解析が01:41:28.167にBEADS_SCHEMA_ERRORとなった。科学終了の4,903.655 ms後の失敗だが、読取は終了前からinflightだった。最終読取時点のissue状態は欠測であり、全期間監視成功・自然終了・実pause不存在を保証しない。

完了CP/NN trace・全search zeroは既に保存されているため、この最後のreader失敗を科学的NN不一致や機構negativeへ変換しない。一方、summary primary=null/exit0は監視成功の根拠にならない。測定diagnoseは共有pause-checkを利用し、monitor.stopがfailure状態を保存してもsummaryへ伝播しなかった。最後の読取失敗の直接原因を、保存がないstdout切断などへ断定しない。

停止境界は別々に確認した。

- Model2 dropは01:41:28.240730 / 28.241545 UTC、各handles0/activeNN0。
- main timers0/pending messages空、monitor callback timer=false/busy=false/waited=true、pause reader pending children空・callback待機完了。
- Worker2 terminateは01:41:28.248055 UTC、forced。inner controlledはregistered49/waited/remaining0、outer sole-root ownedwait returned、remaining/unknown空、outer記録終了28.650164。
- 同bootの82 identityを02:03:31に独立readonly照合し、現在一致なし/readerror0。現在不在を全期間・自然・全host保証へ格上げしない。
- runnerのlaunch/current hash一致を確認。現在の151 private reader/diagnoseはその後の修復であり、元r2を修復済み成功へ書き換えない。

最大1の提案は**私有readerのファイル保存＋有界retryと、終了時のlate control failureのtyped伝播を維持し、科学完了と制御成否を分けること**。現在sourceでこの修復を静的確認したが、全fault runtime再実行は行っていない。次jobはその時点のfresh admissionでready/pause/ownerを確認し、false/unknown/readerrorはspawn0とする。既151継続に全史読取や本裁定の新承認gateを追加しない。

## 自己実行・保存

CPU0単1、RAMguard896MiB、Node heap256MiB。managed全7attempt（失敗4/成功3）のwall計8.244309秒、観測current RSS最大130,252,800 bytes、各60秒内。短い入口/通信/Git/metadata commandは別で、managed値を全事務費用へ拡張しない。瞬間peak・10ms sample間の短命process・metadata commandの完全identity費用は欠測。新8MiB forecastを旧未確認保持を減額せず既critic128MiB/combined112MiB内へ計上した。原17MB rawはread-only参照・hash/必要解析だけで全コピー・全展開0。

自source書込停止とmanaged66 identity現在不在、全child wait・remaining/readerror空、原科学参照の前後hash不変を保存した。NN/Model/search Worker/main timerは起動0。後続の記録保存・必要Git blob復元・backup sync・coordinator報告を行い、受入れ待ちとする。goal・他者close・Sigma/NI/最強・政策採用認定0。

成果正本は `research-data/ai-sigma/153-sigma-web-port-saved-independent/{analysis,binding,replay,failures,runtime-source-stopped-before-report,manifest,handoff-summary}.json`。再現command、版、失敗ログは同scope process記録とtoolsにある。大きい原raw・モデル・binaryは元参照を保持し、必要小ファイルはGit blobから復元する。
