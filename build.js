// 用法：node build_data.js ../game-kit/bank && node build.js [../game-kit]  → 產生單檔 index.html
const fs=require('fs'), path=require('path');
const kit=process.argv[2]||'../game-kit';
const rd=f=>fs.readFileSync(f,'utf8');
let h=rd('index.src.html');
const part=n=>rd(path.join(kit,'parts',n));
// 換成函式避免 $ 被當成取代語法
h=h.replace('/*@@DATA@@*/',()=>rd('data.js'))
   .replace('/*@@SETTINGS@@*/',()=>part('settings.js'))
   .replace('/*@@VOICEHINT@@*/',()=>part('voicehint.js'))
   .replace('/*@@COPYRIGHT@@*/',()=>part('copyright.js'))
   .replace('/*@@PLAYS@@*/',()=>part('plays.js').replace("'REPLACE_GAME_ID'","'detective_de_tonos'"));
fs.writeFileSync('index.html',h);
console.log('index.html',h.length,'bytes');
