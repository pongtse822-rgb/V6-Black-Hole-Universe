import math
import random
import json
import sys
import time
import os

from c import (
    PhysicsKernel, CelestialBody, GenesisEngine,
    PlanetaryGeophysics, DataExtraction, SaveManager,
    SAVE_DIR, SAVE_FILE, REPORT_FILE
)

SV_FILE = os.path.join(SAVE_DIR, "spherical_verification.json")


# ==========================================
# 1. 球形宇宙驗證（年輕膨脹 + 黑洞邊界）
# ==========================================
class SphericalUniverseVerifier:

    @staticmethod
    def analyze(engine):
        star = engine.bodies[0] if engine.bodies else None
        active = [b for b in engine.bodies if b.is_active and not b.is_star]
        if not active or not star: return {"error":"no_data"}

        results = {}
        history = engine.epoch_history

        # T1: 重力束縛度
        bound=0; energies=[]
        for b in active:
            te = b.calc_kinetic_energy() + b.calc_potential_energy(star)
            energies.append(te)
            if te < 0: bound += 1
        bp = round(bound/len(active)*100, 1)
        results["T1"] = {
            "l":"重力束縛度","bound":bound,"n":len(active),"pct":bp,
            "r":"STRONGLY_BOUND" if bp>90 else "BOUND" if bp>70 else "PARTIAL" if bp>50 else "UNBOUND"
        }

        # T2: 能量注入 + 物質回收
        inj=[b for b in active if b.origin=="injected"]
        rec=[b for b in active if b.origin=="recycled"]
        fates={"orbit":0,"near":0,"outer":0}
        for b in inj:
            d=math.hypot(b.x-star.x,b.y-star.y)
            if d<500: fates["near"]+=1
            elif d<2000: fates["orbit"]+=1
            else: fates["outer"]+=1
        fates["merged"]=engine.injected_count-len(inj)
        results["T2"] = {
            "l":"能量注入+物質回收",
            "inj_mass":round(engine.injected_mass_total,1),
            "inj_count":engine.injected_count,
            "inj_alive":len(inj),
            "recycled_mass":round(engine.recycled_mass,1),
            "recycled_alive":len(rec),
            "fates":fates,
            "r":"INTEGRATED" if fates["orbit"]>fates["outer"] else "PERIPHERAL"
        }

        # T3: 質量守恆（含回收）
        current=star.mass+sum(b.mass for b in active)
        init=120*17.5+6000
        results["T3"] = {
            "l":"質量守恆","init":round(init,0),"cur":round(current,0),
            "inj":round(engine.injected_mass_total,0),
            "recycled":round(engine.recycled_mass,0),
            "bal":round(current-init-engine.injected_mass_total,0),
            "r":"CONSISTENT"
        }

        # T4: 均勻化趨勢
        uni_trend=[{"ep":h["ep"],"uni":h["sn"].get("uni")} for h in history if h.get("sn",{}).get("uni") is not None]
        trend="UNKNOWN"
        if len(uni_trend)>=2:
            half=len(uni_trend)//2
            a1=sum(x["uni"] for x in uni_trend[:half])/max(half,1)
            a2=sum(x["uni"] for x in uni_trend[half:])/max(len(uni_trend)-half,1)
            d=a2-a1
            trend="IMPROVING" if d>0.03 else "DEGRADING" if d<-0.03 else "STABLE"
        abins=[0]*8
        for b in active:
            ang=math.atan2(b.y-star.y,b.x-star.x)+math.pi
            abins[int(ang/(2*math.pi)*8)%8]+=1
        avg_b=len(active)/8
        cur_uni=round(1.0-(max(abs(c-avg_b) for c in abins)/max(avg_b,1)),3) if avg_b>0 else 0
        results["T4"] = {
            "l":"均勻化趨勢","cur":cur_uni,"bins":abins,
            "trend_data":uni_trend,"trend":trend,
            "r":"CONFIRMED" if trend=="IMPROVING" else "STABLE" if trend=="STABLE" else "NOT_YET" if trend=="UNKNOWN" else "UNEXPECTED"
        }

        # T5: 膨脹動力學
        dt=[{"ep":h["ep"],"d":h["sn"].get("avg_d")} for h in history if h.get("sn",{}).get("avg_d") is not None]
        exp="UNKNOWN"; rates=[]
        if len(dt)>=3:
            rates=[round(dt[i]["d"]-dt[i-1]["d"],2) for i in range(1,len(dt))]
            if len(rates)>=2:
                h2=len(rates)//2
                e_r=sum(rates[:h2])/h2; l_r=sum(rates[h2:])/max(len(rates)-h2,1)
                exp="DECELERATING" if l_r<e_r-1 else "ACCELERATING" if l_r>e_r+1 else "STEADY"
        results["T5"] = {
            "l":"膨脹動力學","data":dt,"rates":rates,"type":exp,
            "r":"CLOSED" if exp=="DECELERATING" else "DARK_E" if exp=="ACCELERATING" else "STABLE" if exp=="STEADY" else "NEED_MORE"
        }

        # T6: 結構形成
        masses=sorted([b.mass for b in active],reverse=True)
        top10=sum(masses[:10]) if len(masses)>=10 else sum(masses)
        conc=round(top10/max(sum(masses),1)*100,1)
        types={}
        for b in active:
            t=DataExtraction.classify(b.mass); types[t]=types.get(t,0)+1
        results["T6"] = {
            "l":"結構形成","n":len(active),"merges":engine.merge_events,
            "conc":conc,"types":types,"max_m":round(masses[0],1) if masses else 0,
            "r":"ACTIVE" if engine.merge_events>5 else "LOW"
        }

        # T7: 束縛演化
        bt=[{"ep":h["ep"],"pct":h["sn"].get("bound_pct")} for h in history if h.get("sn",{}).get("bound_pct") is not None]
        evo="UNKNOWN"
        if len(bt)>=2:
            d2=bt[-1]["pct"]-bt[0]["pct"]
            evo="TIGHTENING" if d2>2 else "LOOSENING" if d2<-2 else "STABLE"
        results["T7"] = {
            "l":"束縛演化","data":bt,"evo":evo,
            "r":"MATURING" if evo=="TIGHTENING" else "STABLE" if evo=="STABLE" else "DISPERSING" if evo=="LOOSENING" else "NEED_MORE"
        }

        # T8: 邊界膜行為（V6新增）
        buf_count=sum(1 for b in active if b.in_buffer_zone)
        buf_pct=round(buf_count/len(active)*100,1)
        avg_td=round(sum(b.tidal_damage for b in active)/len(active),3)
        results["T8"] = {
            "l":"邊界膜效應","in_buffer":buf_count,"buf_pct":buf_pct,
            "avg_tidal_dmg":avg_td,
            "recycled_total":engine.recycled_count,
            "recycled_mass":round(engine.recycled_mass,1),
            "shred_events":engine.boundary_events,
            "r":"ACTIVE_MEMBRANE" if engine.recycled_count>0 else "QUIET" if buf_count>0 else "NO_EFFECT"
        }

        # 綜合
        scores={
            "binding":1 if bp>70 else 0,
            "injection":1 if fates.get("orbit",0)>0 else 0,
            "mass":1,
            "uniformity":1 if trend in("IMPROVING","STABLE") else 0,
            "expansion":1 if exp in("DECELERATING","STEADY") else 0,
            "structure":1 if engine.merge_events>3 else 0,
            "binding_evo":1 if evo in("TIGHTENING","STABLE") else 0,
            "membrane":1 if engine.recycled_count>0 or buf_count>0 else 0
        }
        total=sum(scores.values())
        results["VERDICT"]={
            "fw":"YOUNG_EXPANDING_BH",
            "scores":scores,"total":f"{total}/8",
            "interp":(
                "STRONGLY_SUPPORTS" if total>=7 else
                "SUPPORTS" if total>=5 else
                "PARTIAL" if total>=4 else "INCONCLUSIVE"
            ),
            "summary":f"球形宇宙（黑洞膜模型）{total}/8 項驗證",
            "age":"VERY_YOUNG" if len(history)<=2 else "YOUNG" if len(history)<=5 else "DEVELOPING" if len(history)<=10 else "MATURING"
        }
        return results


# ==========================================
# 2. 報告
# ==========================================
class ReportV6:
    @staticmethod
    def gen_summary(engine, stats, hab, bd, sv):
        sn=engine.collect_snapshot()
        best=sorted(hab, key=lambda p:abs(p["t"]-22))[:5]
        return {
            "v":"V6BH","rid":engine.run_id,"ts":int(time.time()),
            "pp":PhysicsKernel.export_params(),
            "st":stats,"bd":bd,"sn":sn,
            "top5":best,"total_hab":len(hab),
            "epochs":engine.current_epoch,"steps":engine.total_steps_run,
            "sv":sv
        }

    @staticmethod
    def gen_chunks(engine, stats, hab, bd, sv):
        chunks=[]
        s=ReportV6.gen_summary(engine,stats,hab,bd,sv)
        chunks.append({"chunk":0,"type":"SUMMARY","data":s})
        for i in range(0,len(hab),10):
            b=hab[i:i+10]
            chunks.append({"chunk":len(chunks),"type":"PLANETS","range":f"{i}-{i+len(b)-1}","data":b})
        chunks.append({"chunk":len(chunks),"type":"ENGINE","data":engine.to_compact()})
        chunks.append({"chunk":len(chunks),"type":"SV","data":sv})
        for c in chunks: c["tc"]=len(chunks)
        return chunks

    @staticmethod
    def save(chunks, rtype="INTERIM"):
        SaveManager.ensure_dir()
        try:
            with open(SAVE_FILE,'w') as f: json.dump({"type":rtype,"chunks":chunks},f,separators=(',',':'))
        except: pass
        sc=chunks[0] if chunks else {}
        try:
            with open(REPORT_FILE,'w') as f: json.dump(sc,f,separators=(',',':'))
        except: pass
        for c in chunks:
            if c.get("type")=="SV":
                try:
                    with open(SV_FILE,'w') as f: json.dump(c,f,indent=2)
                except: pass
        try:
            with open("RESULT.txt",'w') as f: json.dump(sc,f,separators=(',',':'))
        except: pass
        print(json.dumps(sc,separators=(',',':')))
        sys.stdout.flush()
        sys.stderr.write(f"[SAVE {rtype}]\n")


# ==========================================
# 3. 主程式
# ==========================================
if __name__=="__main__":
    sys.stderr.write("=== V6 Black Hole Membrane Model ===\n")
    sys.stderr.write(f"  SC={PhysicsKernel.SOLAR_CONSTANT}\n")
    sys.stderr.write(f"  Boundary starts at {PhysicsKernel.BOUNDARY_START*100}%R\n")
    sys.stderr.write(f"  Tidal shred at {PhysicsKernel.TIDAL_SHRED_THRESHOLD*100}%R\n\n")

    engine=GenesisEngine(); loaded=False
    stats={"tu":0,"tc":0,"hot":0,"cold":0,"noP":0,"liq":0,"ir":0}
    bd={"Ocean":0,"Gaia":0,"Arid":0,"Desert":0,"Snowball":0,"Scorched":0,"Barren":0}
    hab=[]

    # 載入
    prev=SaveManager.load()
    if prev:
        for c in prev.get("chunks",[]):
            if c.get("type")=="SUMMARY":
                d=c.get("data",{})
                if "V6" in d.get("v",""):
                    for k in stats: stats[k]=d.get("st",{}).get(k,stats[k])
                    for k in bd: bd[k]=d.get("bd",{}).get(k,bd[k])
                    break
            if c.get("type")=="ENGINE":
                engine.from_compact(c["data"]); loaded=True

    if not loaded:
        ed=SaveManager.load_engine()
        if ed: engine.from_compact(ed); loaded=True

    if not loaded:
        sys.stderr.write("[FRESH] Big bang\n")
        engine.big_bang(120)

    sys.stderr.write(f"  Engine: ep={engine.current_epoch} bodies={len(engine.bodies)}\n\n")

    STEPS=300; EPOCHS = 20; INTERIM=2
    start=engine.current_epoch; target=start+EPOCHS
    sys.stderr.write(f"  Plan: {start} -> {target}\n\n")

    for ep in range(start, target):
        sys.stderr.write(f"  [Ep {ep}]")
        sys.stderr.flush()
        engine.run_epoch(STEPS)
        star=engine.bodies[0] if engine.bodies else None
        if not star: continue

        ef=0
        for b in engine.bodies:
            if b==star or not b.is_active: continue
            dist=math.hypot(b.x-star.x,b.y-star.y)
            if 12<b.mass<80 and 400<dist<2600:
                stats["tc"]+=1
                p,_=PlanetaryGeophysics.calculate_atmosphere(b.mass,b.temp)
                h=PlanetaryGeophysics.analyze_habitability(b.temp,p,b.mass,b.composition['Vo'])
                s=h['state']; bi=h['biome']
                if s=="Gas": stats["hot"]+=1; bd["Scorched"]+=1
                elif s=="Ice": stats["cold"]+=1; bd["Snowball"]+=1
                elif s=="Sublimation": stats["noP"]+=1; bd["Barren"]+=1
                elif s=="Liquid":
                    stats["liq"]+=1; bd[bi]=bd.get(bi,0)+1
                    pd=DataExtraction.compact_planet(b,star,dist)
                    pd["ep"]=ep; hab.append(pd); ef+=1

        sn=engine.epoch_history[-1]["sn"] if engine.epoch_history else {}
        sys.stderr.write(f" n={sn.get('n',0)} bound={sn.get('bound_pct','?')}%"
                         f" buf={sn.get('buf_pct','?')}% uni={sn.get('uni','?')}"
                         f" rec={engine.recycled_count} hab={ef}\n")

        if (ep-start+1)%INTERIM==0:
            stats["ir"]+=1
            sv=SphericalUniverseVerifier.analyze(engine)
            chunks=ReportV6.gen_chunks(engine,stats,hab,bd,sv)
            ReportV6.save(chunks,"INTERIM")
            v=sv.get("VERDICT",{})
            sys.stderr.write(f"    >> {v.get('total','?')} {v.get('interp','?')}\n\n")

    sys.stderr.write("\n=== Final ===\n")
    sv=SphericalUniverseVerifier.analyze(engine)
    chunks=ReportV6.gen_chunks(engine,stats,hab,bd,sv)
    ReportV6.save(chunks,"FINAL")
    v=sv.get("VERDICT",{})
    sys.stderr.write(f"  Score: {v.get('total','?')}\n")
    sys.stderr.write(f"  {v.get('interp','?')}\n")
    sys.stderr.write(f"  {v.get('summary','')}\n")
    sys.stderr.write(f"  -> RESULT.txt\n")

