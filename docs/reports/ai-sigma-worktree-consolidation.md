# 永続資産とmanaged worktreeの整理 / quoridor-1d2.1

本作業は終了済みframe21から独立した保守。研究再開・モデル変更・学習/推論/対局は行わない。mainをコードと実験検証記録の正本とし、コードcheckoutの寿命から必要資産を分離する。

## 実施と保護境界

登録済みresearch-team、scheduler、webapp-presentationと未登録ai-sigma-frame18-data-learningを、未保存情報の保存・復元確認後に撤去した。旧ai-sigmaもRoot保全commitと全byte再読込一致後、11:09:35 UTCに通常helperで撤去した。登録解除はmanage_worktree.shを使用し、枝・共有Git履歴・通常indexは保持する。共有DB/アクセスlockとframe21-search、frame21-featuresは撤去対象外。

旧資産76pathを64unique fileへ対応づけ、同volumeのassets/models、assets/checkpoints、assets/inputsへrenameした。12同byte重複は既資産を再用し、各原pathのSHA/sizeを移動対応manifestへ残した。旧科学readerの自然停止と92 scheduler/monitor停止後に実施。互換symlink、旧source tree、再生成cacheはassetsへ移していない。

QF1/NNUE重み・ONNX・教師ラベル・split・尺度はbyte不変。旧weight-manifestは原絶対pathとSHAのままmain Gitへ残し、現在用descriptorは相対weights参照だけを更新した。新runはresearch-assets.pyで現在pathを解決して自身の設定へbindする。研究runの条件や原科学記録は遡及更新しない。

## 未保存情報と分類

small-worktree-preservation.jsonは39既Git byte一致と7unique source/documentを区別する。製品固有27memberはresearch-data/worktree-consolidation/1d2/へ別保存し、Rootが復元SHAを独立確認した。

旧ai-sigmaはtracked HEAD snapshot9405entry/8247unique objectがmainから到達でき、現在treeを読み戻せることを確認した。旧private index12参照の2740unique staged blobもGitまたは保全catalogで照合した。古い29欠落を当時正常として救済せず、旧branchと記録を保持する。全branch過去historyの再監査は行わない。

未一致239MBを全て科学rawとして扱わず、私有Cargo target、診断ELF、旧ORT Web依存を元source/lock/command/version/SHA・非使用で分類した。raw/receipt/未保存sourceは保存した。既main archive/Gitと同byteの情報を再archiveせず、残る7010member/192,924,639復元byteをXZ 6,806,976byteへ保存し、全memberのSHA/sizeをstream復元確認。Rootも全memberを独立確認し、保全12pathを6c07d81095afa45f65d7318660b75783a1832c84へcommitして再読込一致を確認した。

初回16MiB archive cap拒否は原本を保持したまま停止し、失敗receiptを保存した。Rootの新maintenance配分160MiBは旧92guardの変更ではなく、原本・新archive・unique Gitの一時保持を含む独立した現在配分。旧unknown134,217,728byteを減額しない。

## 現役入口と保守ルール

research-paths.json v2を永続assetカテゴリへ更新し、research-assets.pyを公開解決入口とした。未対応旧path・欠落・traversal・symlink範囲外・SHA/size不一致は明示エラーにする。恒常mirrorや旧checkout fallbackを作らない。研究clientのcwdはmainまたは実登録managed code checkoutに限定し、assetsや未登録旧directoryをコード編集先として受理しない。

AGENTS/README/team設計/研究コード手順/storage-policy/scripts案内の配置説明を更新し、Rootの整形規約等は保持した。新asset移行では自然読取終了→byte照合→同volume移動→対応manifest→現在caller設定の順を使う。旧記録はimmutable、現在資産の解決と科学実行を区別する。

## 検証と残る作業

資産resolverの合成6test、研究clientのmock11test、対象PythonのRuff format/check、config/現在descriptorのPrettier checkはPASS。76実資産mappingのSHA/size解決もPASS。検証はモデルをimport/forwardしない。OS Pythonによるclient検査は既websockets依存不足で不成立となり、既team envへ切替後にPASS。失敗を科学結果へ変換しない。

旧ai-sigma撤去前に現存catalog29,338fileのbyte差異0、未追跡/ignored29,367fileのcatalog外0、76asset SHA/size一致を再確認。保全済othersのlogical量1,735,543,062byte・st_blocks合計1,804,017,664byteを撤去した。後者はhardlink/共有extentの物理解放量ではない。63欠落tracked pathはhelperのclean条件のため旧HEADからworktree-only復元した後にcheckout全体を撤去し、旧欠測や科学結果を成功へ変更していない。main index SHAは前後522ed2a5ff40544bf2cafe106f5154b69e740ad4b803eb64b90448a536b1b0b6で一致、codex/ai-sigma branchを保持した。

旧cwdを持つChrome MCP4processが撤去前に見つかり、削除0でRootへ返した。Rootが同MCP cwdだけをmainへ変更し公式reload、旧exactidentity不在後にfresh確認を再開した。他者kill・AppServer再起動・science interruptはない。root-owned procの読取欠測はreceiptへ残し、全host/未来不在を認定しない。

11:11:31 UTCのdirected currentは保持10,051,764,224byte、UNKNOWN134,217,728byte全額と残92/v8・新maintenance160MiBの保守的上界を含む10,478,641,152byte、cap12,884,901,888byte内、読取errors0。終了済み将来予約の解放はRootの明示判断に限定し、現保持・過去peak/原guardは減額しない。新maintenance160MiBは既に保持へ含まれる部分も丸額追加した安全側の上界。旧rootsを含む前本人標本12,211,113,984byteとの差2,159,349,760byteはdirected dev/inode会計の変化で、全diskの物理解放保証ではない。

5撤去対象の不在、必要assets、2registered WTのlock、共有DB wrapper ready/showを確認し、自己短期childはwait済み。runtimeは停止したまま。長期保守上の改善は永続資産とcode checkoutの分離、正本の一元化、再生成cacheとunique証拠の区別。共有env/model/入力は保護し、次の取得・新growthではfresh保持と有効未使用予約を再確認する。未観測量を空きとして扱わない。

証拠正本: [保全と移動対応](../../research-data/ai-sigma/1d2-worktree-consolidation/)、[製品証拠](../../research-data/worktree-consolidation/1d2/)。Git統合ownerはRoot、本人は変更pathとwriter停止を渡しindex/commitを操作しない。
