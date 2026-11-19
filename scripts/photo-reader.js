'use strict';
// Public reading only. All writes go through the authenticated management app.
const $=id=>document.getElementById(id),esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dateText=d=>d.slice(0,10).replaceAll('-','.');
let entries=[],page=0,pageSize=10;
function image(r){return `<button class="image-button" data-photo="${esc(r.id)}" aria-label="放大查看照片"><img src="${esc(r.image)}" alt="照片日记" loading="lazy"></button>`;}
function meta(r){return `<div class="photo-meta"><time>${dateText(r.date)}</time>${r.sample?'<span>示例</span>':''}</div>`;}
function render(){
 document.querySelectorAll('.entry-count').forEach(n=>n.textContent=entries.length+' 张');
 $('category-entries').innerHTML=entries.slice(0,2).map(r=>`<article class="photo-entry">${image(r)}<p>${esc(r.caption)}</p>${meta(r)}</article>`).join('')||'<p class="empty">这里还没有照片。</p>';
 const pages=Math.max(1,Math.ceil(entries.length/pageSize));page=Math.min(page,pages-1);
 $('diary-entries').innerHTML=entries.slice(page*pageSize,(page+1)*pageSize).map(r=>`<article class="diary-entry">${image(r)}<div class="diary-copy"><p>${esc(r.caption)}</p>${meta(r)}</div></article>`).join('')||'<p class="empty">这里还没有照片。</p>';
 let controls=$('diary-pages');if(!controls){controls=document.createElement('div');controls.id='diary-pages';controls.style.cssText='display:flex;gap:12px;align-items:center;justify-content:flex-end;flex-wrap:wrap;margin-top:20px;color:var(--muted);font-size:13px';$('diary-entries').after(controls);}
 controls.innerHTML=`<label style="margin-right:auto">每页 <select aria-label="每页照片条数">${[5,10,20,30,50,100,200].map(n=>`<option ${n===pageSize?'selected':''}>${n}</option>`).join('')}</select> 条</label><button class="text-button" data-page="-1" ${page===0?'disabled':''}>上一页</button><span>${page+1} / ${pages}</span><button class="text-button" data-page="1" ${page===pages-1?'disabled':''}>下一页</button>`;
 controls.querySelector('select').onchange=e=>{pageSize=Number(e.target.value);page=0;render()};controls.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>{page+=Number(b.dataset.page);render();$('diary-entries').scrollIntoView({block:'start'})});
}
function route(){
 const view=(location.hash||'#yangquan').slice(1);
 if(view==='home'){location.assign('../index.html');return;}
 if(!['yangquan','diary'].includes(view)){location.assign('../admin/#/collections/photos');return;}
 document.querySelectorAll('main>section').forEach(n=>n.hidden=n.id!==view+'-view');document.querySelector('.demo-bar').hidden=true;
 document.title=(view==='diary'?'全部记录':'照片日记')+' · 漾泉 · 闻日光';window.scrollTo(0,0);
}
document.querySelectorAll('.write-link').forEach(b=>b.onclick=()=>location.assign('../admin/#/collections/photos'));
document.body.addEventListener('click',e=>{const b=e.target.closest('[data-photo]');if(!b)return;const r=entries.find(r=>r.id===b.dataset.photo);if(!r)return;$('full-photo').src=r.image;$('full-caption').textContent=r.caption;$('full-date').textContent=dateText(r.date);$('photo-dialog').showModal()});
$('close-photo').onclick=()=>$('photo-dialog').close();$('photo-dialog').onclick=e=>{if(e.target===$('photo-dialog'))$('photo-dialog').close()};
$('credits').onclick=()=>$('credits-dialog').showModal();$('close-credits').onclick=()=>$('credits-dialog').close();
window.addEventListener('hashchange',route);route();
fetch('entries.json',{cache:'no-cache'}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(data=>{
 entries=data.entries;render();
 if(data.articles?.length){const section=document.createElement('section');section.style.marginTop='36px';section.innerHTML='<h2>写在漾泉</h2>'+data.articles.map(a=>`<p style="border-top:1px solid var(--line);padding-top:14px"><time style="color:var(--muted);font-size:12px">${dateText(a.date)}</time>　<a href="../${esc(a.url)}">${esc(a.title)}</a></p>`).join('');$('yangquan-view').append(section);}
}).catch(()=>{for(const id of ['category-entries','diary-entries'])$(id).textContent='照片暂时未能加载，请刷新重试。'});
