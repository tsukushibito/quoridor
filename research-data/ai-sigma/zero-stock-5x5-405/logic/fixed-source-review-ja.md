# 固定5x5源泉の限定独立確認

判定は **source_clear=true、blockers=[]、ordinary=[]**。対象は `source-STOP.json` SHA256 `ff2150ad7be8bd8299d4b2fb9c112b18498198d1e7c067988de322dd9a3f9561`、30482B、0644。Rust `16e4b64f` / Python参照 `34b04d53` の今回の列挙・合法辺・board-WDL境界だけを確認した。一般のD不存在、実際の全配置件数、真の零在庫対局prefix、9x9への結論は含まない。

## 確認した境界

- Rust53–119行：Hの同一行隣接・Vの同一列隣接・同anchor交差が対称な衝突関係になる。上位bitからexclude/includeし、forbiddenをinclude側だけへ渡すDFSは各非衝突集合を一度、数値昇順で出す。空集合・奇数枚・全枚数を残し、初期駒の可達性を配置フィルタにしない。
- 127–245、298–354行：壁による無向辺の削除、各自goalからの可達域、異なる非goal二駒と両手番を使う。相手駒への通常移動を除き、straight jumpを優先し、不可能時だけperpendicular side jumpを生成する。合法goal着地は即GOAL、その他の子は同じactive域内と検査する。非終端の合法手0を勝手にdrawとせずerrorにする。active0の配置も除外せず0件として処理可能である。
- 357–513行：即goalをW/rank1、L子がある親をW、全子Wの親をLとして一度だけqueueへ入れる。Wの選択L子とLの全W子ではrankが厳密に減る。未分類Dにはgoal/L子がなくD子が必要で、W子という負ける逸脱は許す。degree・全行動・子ID・W+L+D=activeを確認する。rankは勝ち手数最適値とは認定しない。
- 255–296、515–572行：raw最大1250、固定8行動/状態、逆辺最大10000の再利用buffer。u16状態/GOAL sentinel、u8 cell、LE固定48B layout行、bounded全graph/D戦略出力の範囲が整合する。実active上界770であり、情報幅を実RSSや速度へ読み替えない。
- 611–619、655–860行：pilotの固定述語とremainingの補集合modKは重複なく全ordinalを分割する。同じbuild/verifyを使用し、全maskの厳密昇順、入力長、選択件数を検査する。完全性の元は今回の成功した同一enumeratorとそのimmutable出力であり、任意の昇順mask fileのheaderだけではない。fresh出力・error伝播・sync後summaryという経路は、失敗prefixやtorn行を成功へ昇格しない。runtime受入れは元process結果と完全summary/全shard censusを併せて扱う。
- Rustの7定義とPython15–220、266–334行の参照選択は、異なる座標集合/同期fixedpointで全合法辺・WDL・rank/D選択を照合する。双方goal葉の退却、jump優先、D cycleを含み、wall距離の単調性に依存しない。独立参照とnativeが共有する規則仕様自体は上記のソース読解で確認した。

## 必要性と限界

有限数学計算に必要なcollision DFS、単一graphのqueueと逆辺、bounded証拠出力であり、製品API・別資格・再実行schedulerを増やしていない。候補Dの発見と、元の同数在庫からの合法な非終端prefixの実現可能性は別問題である。全配置/全WDLの実結果や所要時間はこのreviewでは生成していない。

作者binding時点の7定義と参照はUNBUILT/UNTYPED/UNRUNだった。後着のRoot software通知は同じRust/参照について7定義と52 fixture確認PASSと報告しているが、本source判定をその結果から推論していない。ここではnative、Python参照関数、テスト、列挙、solverを一度も実行していない。source clearは画像/実行成功やD不存在の証明ではない。

## 読者停止と引渡し

選択6参照をSHA-size-modeで前後一致確認。実selected reader STOPは **2026-10-15T02:23:08.392808+00:00**、reader exit観測は02:23:08.395479。各readerはdirectwait/reap済みで元identityはfresh absent。readers/children/jobs/TMP/leases/waits/remainingはすべて[]、current/next reservationはNONE。詳細は `fixed-source-STOP.json`、`fixed-source-read-receipts.json`。原formatter/capture/管理失敗とreturned対diskの区別は変更しない。

この固定ソース境界は完了。最短路leaf・近似許可の論理整理は同じleafの独立残件で、405.1の列挙/pilot/fullや324の通常software受入れをその完成/ACK待ちにしない。mixed/learner全prep/pipelineと323 USERPAUSE、defaults/models/weights/seals/旧RAW・FAILED・費UNKNOWNを保持する。
