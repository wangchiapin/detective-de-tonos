// 用法：node build_data.js ../game-kit/bank  → 產生 data.js（遊戲用句庫：本調答案、無調拼音）
const fs=require('fs'), path=require('path');
const dir=process.argv[2]||'../game-kit/bank';
const MARK={ā:['a',1],á:['a',2],ǎ:['a',3],à:['a',4],ē:['e',1],é:['e',2],ě:['e',3],è:['e',4],ī:['i',1],í:['i',2],ǐ:['i',3],ì:['i',4],ō:['o',1],ó:['o',2],ǒ:['o',3],ò:['o',4],ū:['u',1],ú:['u',2],ǔ:['u',3],ù:['u',4],ǖ:['ü',1],ǘ:['ü',2],ǚ:['ü',3],ǜ:['ü',4]};
function parse(syl){ let tone=0, plain=''; for(const c of syl){ if(MARK[c]){plain+=MARK[c][0]; tone=MARK[c][1];} else plain+=c; } return {plain,tone}; }
const out=[], problems=[];
for(const L of ['A1','A2','B1']){
  const j=JSON.parse(fs.readFileSync(path.join(dir,L+'.json'),'utf8'));
  for(const s of j.sentences){
    const chars=[], simp=[], syls=[]; let bad=false;
    s.trad.forEach((t,i)=>{
      const ps=s.pinyin[i].split(' '), tc=[...t], sc=[...s.simp[i]];
      if(ps.length!==tc.length||sc.length!==tc.length){bad=true;problems.push(s.id+' '+t+' '+s.pinyin[i]);return;}
      tc.forEach((c,k)=>{
        let {plain,tone}=parse(ps[k]);
        if(c==='不') tone=4;            // 一、不：答案一律用本調
        if(c==='一') tone=1;
        chars.push(c); simp.push(sc[k]); syls.push([plain,tone]);
      });
    });
    if(bad) continue;
    // 詞的分組（讓畫面按詞排列）：每個詞有幾個字
    const wl=s.trad.map(t=>[...t].length);
    out.push({id:s.id,lv:L,t:chars,s:simp,p:syls.map(x=>x[0]),a:syls.map(x=>x[1]),w:wl,es:s.es,en:s.en});
  }
}
fs.writeFileSync('data.js','/* 由 build_data.js 從 game-kit 句庫產生；一、不已換成本調 */\nconst SENTENCES='+JSON.stringify(out)+';\n');
console.log('句數',out.length,'問題',problems.length); problems.slice(0,10).forEach(x=>console.log(x));
const neu=out.reduce((n,s)=>n+s.a.filter(x=>x===0).length,0), all=out.reduce((n,s)=>n+s.a.length,0);
console.log('音節總數',all,'輕聲',neu);
