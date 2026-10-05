import asyncio,importlib.util,pathlib,json,datetime
sp=importlib.util.spec_from_file_location("team","/workspaces/quoridor/scripts/dev/research-team.py");m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
async def main():
 host=m.command_json(["codex","app-server","daemon","version"])
 async with m.AppServer(host,timeout=20) as s:
  t=await s.read_thread("01a0f2e9-357d-7ef3-a2fe-b16f80accda5")
  if t["status"]["type"]!="active": out={"RPC":False,"reason":"root idle; no reply-only turn"}
  else:
   with m.dispatch_lock(pathlib.Path("/workspaces/quoridor")):
    out=await s.deliver(t["id"],"goal quoridor-4lc /230 sameactive補足のみ。現在11:28:57点で228actual-start.json記録無し、新scope静的準備中。人工短子/fakeRPC CPU1テストを科学不在窓に調整する方針受領、開始前にcurrent228 owned子/実physicsを確認し、生成/CPU学習が実activeならテストを窓へ留保（root/coor ACK全稿gateなし）。228ownerへ230 test調整を通知、actualgenstartは必要範囲で報告してもらう。230仕上がりを228entrygateにせず現guardian所有を維持、coorはrootsole新scope/scheduler/team/common/registry/228source重複編集0。11:45 firstgenは目安で未来空窓保証なし。軽NN0CPU計算1だけでも測定には競合し得るので実child終了証拠を分ける。root既active仕事への補足で新turn要求/資源上限増/新承認はありません。",None)
  out["UTC"]=datetime.datetime.now(datetime.timezone.utc).isoformat();pathlib.Path("research-data/ai-sigma/frame18-coordinator/root230-active-steer-receipt.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out))
asyncio.run(main())
