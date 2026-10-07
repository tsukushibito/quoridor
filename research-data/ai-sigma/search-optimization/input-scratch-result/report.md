入力scratchの事前確保・参照渡し候補は、限定した正しさと通常評価の一時ヒープ回避を確認できた。速度改善は支持されず、main採用はRootの判断待ち。旧sort・inline・stream・map・TT候補の不採用判断は変更しない。

探索1回または反復推論workerごとに、受入れ済み幅に合わせたVecを一度作る。FT32では70f32/280B、最大FT2048では4102f32/16408B。各評価はReLUと距離入力を一度だけ書き、連続sliceを同じscalar dot loopへ渡す。親accumulatorと大きなmapは参照のまま、重量layout/FP順序/活性化/尺度/特徴/合法手/履歴/TT/Action順/PVSは変更しない。グローバル可変scratch、unsafe未初期化、巨大per-depth stackは追加しない。実standalone evaluateは同じ演算実装へ一回用scratchを渡す便宜APIであり、反復production callerは明示所有のscratchを再用する。

数値job25450e59: 2026-10-07T00:00:50.849084Z開始、00:00:55.709720Z停止、whole4.861134083s。35コマンドのdirectwait/cleanup[]/記録科学PID不在、raw35gzip memberの復元SHAを確認。6限定fixtureは21topology/P1P2/Scalar・Simd FT/元allocating算術/合法full-delta/1270mode-child/全幅minimax/親・履歴復帰/不正入力・Numeric error/cancel/非alias/別invocation再入/defaultResidualとNN0 Counted adapter。24plainの値bits/Action/PV/depth/nodes/既存counter/親復帰が元canonicalと一致。実head2,782,283、Numeric-error head試行2、fingerprint拒否2、FT記録165prepare/2,363,349delta、fulloracle FT詳細はUNKNOWN。限定試験であり全入力空間の証明ではない。

5root allocation計測: 各探索のsetup1回280B、通常evaluate88,727回はalloc/realloc/requested bytesとも0。保存済み同canonical60d/BESTc0ecのhistorical baseline allocator rawでは88,727確保/24,843,560要求Bだった。whole caller確保は585,221→496,499、要求Bは85,744,997→60,902,837（5setup分を含む）。historical allocator記録は新しい同時期の速度比較に使わず、init/通常head/全callerを区別する。FT・合法手・距離・TTなど他の確保は残る。要求量はretained/RSS peakではなく、断片化/latency改善は未測定。

主指標: 旧固定BEST c0ec/真正5root/depth3/node100k/TT4096/PVS、canonical allocating60dのprivate ELF6c18と新候補a7c32を事前固定12組ABBAで比較。候補/元の総時間比 whole1.024989095（2.50%遅い）、search1.015318667、parent process1.078204718。wholeは6組速い/6組遅い、pair中央値0.996751951、範囲0.888846〜1.215696。perprocess wholeは概ね0.13秒の短い系列で外れ値・相関・初期化影響があるため、確実な退行量/一般倍率も断定しない。whole/プロセス時計/探索時計を分け、nested時計を合算しない。

副指標: 同5root、各20,000head、4micro processのABBA。evaluate総比1.140178512、2組比1.299140/0.993183。micro whole1.182345165/process1.469210026。入力setupはmicroの内側timer外で、whole内には含む。microをwhole改善や棋力/MCTS優位へ拡張しない。allocator付きcaller時計は診断で、plain主比較へ混ぜない。

同候補の全job費: r1失敗1.420503708（追加testのfree method/変数名誤り）、r2失敗22.844988135（test Search initializer漏れ）、r3 software成功58.176931933、numeric4.861134083、合計87.303557859s。先行softwareは学習midpoint2と同時実行でありworkcostのみ、数値jobはmidpoint2停止後・midpoint3開始前で非重複。旧費・失敗・source snapshots・UNKNOWNを保全し、source/control/LLM細費はUNKNOWNのまま別扱い。自律枠全knownwhole497.958088249s/head17,631,347、歴史の別枠費は加算/返金/再監査しない。

ソフトウェア資格: exact sourceに対するNNUEresearch/default residual・float parity no-run、AI/native no-run、NN+AI/native限定Clippy -Dwarnings/変更範囲rustfmt PASS。Default Float/Quantized branchはcompile/default delegationの証拠で、今回新しい全モデル実数値検証を行ったという意味ではない。partial oldPASS/原失敗を成功化しない。

候補plain: candidate-plain-r3.gz（397239B、圧縮復元SHA a7c32b5ea34491287a7ce24375ce5508246b16c2077d88ac63dcc61a14dfd834）。counter artifactは測定前に66c016f2を検証し、その後同reserved shared outputへplainを復元して実行bitを付与した。counterを別永久ELFへ複写しない。モデル/入力のコピー・変更は0、sharedtarget growthはnull/UNKNOWN。sample familyRSS178565120B・ownoutput1314816Bで、continuous peak保証ではない。現168MiB/forecast175362048を保持し全target/global walkを追加しない。

判断: 人間が指定した通常評価の一時確保回避は、このResidual production経路で成立した。大きなpayload値渡しを併用した旧WallMapsとは別の介入である。速度は不支持のため高速化として自動採用しない。メモリ原則による採否と所有/API維持の通常レビューをRootへ渡す。standalone一回用APIや他のcaller確保は残るので全heapfree完了とは呼ばない。追加のnumeric/compile予約は0、学習midpoint3が次slotを使用中、探索は保存集計/source準備のみ。

再現: Python aggregate.pyは保存rawから数値一致・counts・比率を再計算するだけで新model forwardは0。研究jobのconfig/worker/guardとcompile proof binding、source差分production-only.patch、全停止sourceはnumeric-plan.json→plan-r3.jsonのpath/SHAを正本とする。live研究計測exampleは停止snapshotを渡し、実験別探索器コピーを恒久化しない。配送予約拒否（323blocked/pre-dispatch）を保持、後のactualSTOP配送はaccepted、他ownerのblockedを変更/盲retryしない。
