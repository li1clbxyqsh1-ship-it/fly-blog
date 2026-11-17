(() => {
'use strict';
const $=id=>document.getElementById(id);
const zone='Asia/Shanghai';
const ttl=30*60*1000, cacheKey='wenriguang-weather-chengdu-v1';
let cached=null, pending=false;
try { cached=JSON.parse(localStorage.getItem(cacheKey)||'null'); } catch (_) {}
const notes=[['读几页书','急着赶路'],['出门走走','辜负日光'],['提笔记一念','把话藏太久'],['慢慢吃饭','忘了休息'],['听一首老歌','催促自己'],['留意沿途','只看终点'],['整理心情','熬夜太晚']];
function calendar(){
 const now=new Date();
 const values=Object.fromEntries(new Intl.DateTimeFormat('en-GB',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(now).map(p=>[p.type,p.value]));
 const y=+values.year,m=+values.month,d=+values.day;
 $('today-date').replaceChildren(document.createTextNode(`${y}.${values.month}.${values.day}`));
 const weekday=document.createElement('small');weekday.textContent=new Intl.DateTimeFormat('zh-CN',{timeZone:zone,weekday:'long'}).format(now);$('today-date').append(weekday);
 try {
  const lunar=Solar.fromYmdHms(y,m,d,+values.hour,+values.minute,+values.second).getLunar();
  $('today-lunar').textContent=`农历 ${lunar.getYearInGanZhi()}年 ${lunar.getMonthInChinese()}月${lunar.getDayInChinese()}`;
  $('solar-term').textContent=lunar.getPrevJieQi(false).getName();
 } catch (_) {
  try{$('today-lunar').textContent='农历 '+new Intl.DateTimeFormat('zh-CN-u-ca-chinese',{timeZone:zone,month:'long',day:'numeric'}).format(now);}catch(_){$('today-lunar').textContent='';}
  $('solar-term').textContent='节气暂不可用';
 }
 const pair=notes[Math.floor(Date.UTC(y,m-1,d)/86400000)%notes.length];
 $('daily-yi').textContent=pair[0];$('daily-ji').textContent=pair[1];
}
function describe(c){
 if(c===0)return '晴'; if(c===1)return '晴间多云';if(c===2)return '多云';if(c===3)return '阴';
 if([45,48].includes(c))return '雾';if([51,53,55].includes(c))return '毛毛雨';
 if([56,57,66,67].includes(c))return '冻雨';if(c===61)return '小雨';if(c===63)return '中雨';if(c===65)return '大雨';
 if([71,73,75,77].includes(c))return '雪';if([80,81,82].includes(c))return '阵雨';if([85,86].includes(c))return '阵雪';if([95,96,99].includes(c))return '雷雨';return '天气未知';
}
function valid(c){return c&&Number.isFinite(c.temperature)&&Number.isInteger(c.code)&&Number.isFinite(c.at)&&c.at<=Date.now()+60000;}
function show(c,stale=false){
 $('weather').textContent=`${describe(c.code)} ${Math.round(c.temperature)}℃${stale?'（上次数据）':''}`;
 const time=new Intl.DateTimeFormat('zh-CN',{timeZone:zone,hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(c.at));
 $('weather-credit').textContent=`Open-Meteo · ${time}更新${stale?' · 暂未刷新':''}`;
 $('weather').title=`成都天气，数据时间 ${c.modelTime||time}（北京时间）`;
}
async function weather(){
 if(pending)return;
 const now=Date.now();if(valid(cached)&&now-cached.at<ttl){show(cached);return;}
 if(valid(cached)&&now-cached.at<6*3600000)show(cached,true);
 pending=true;const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),9000);
 try{
  const response=await fetch('https://api.open-meteo.com/v1/forecast?latitude=30.67&longitude=104.06&current=temperature_2m,weather_code&timezone=Asia%2FShanghai&forecast_days=1',{signal:controller.signal,cache:'no-store'});
  if(!response.ok)throw new Error('weather unavailable');const data=await response.json();
  const current=data.current;const next={temperature:current?.temperature_2m,code:current?.weather_code,modelTime:current?.time,at:Date.now()};
  if(!valid(next))throw new Error('invalid weather');cached=next;try{localStorage.setItem(cacheKey,JSON.stringify(next));}catch(_){}show(next);
 }catch(_){
  if(valid(cached)&&Date.now()-cached.at<6*3600000)show(cached,true);
  else{$('weather').textContent='天气暂不可用';$('weather-credit').textContent='天气：Open-Meteo · 暂未获取';}
 }finally{clearTimeout(timer);pending=false;}
}
calendar();weather();
setInterval(()=>{calendar();weather();},60000);
document.addEventListener('visibilitychange',()=>{if(!document.hidden){calendar();weather();}});
})();
