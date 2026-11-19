'use strict';
// Public configuration only. GitHub client secrets belong in the login Worker.
(async()=>{
 const message=document.getElementById('setup-message');
 try{
  const [settings,config]=await Promise.all([fetch('settings.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('配置暂时无法读取');return r.json()}),fetch('config.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw Error('后台配置暂时无法读取');return r.json()})]);
  if(!settings.auth_url){message.textContent='登录服务正在接通。完成后这里可以管理文章与照片；当前还不能在线发布。';return;}
  const auth=new URL(settings.auth_url);if(auth.protocol!=='https:'||auth.username||auth.password||auth.search||auth.hash||auth.pathname!=='/')throw Error('登录服务地址配置有误');
  if(settings.repo!=='li1clbxyqsh1-ship-it/fly-blog'||settings.branch!=='main')throw Error('后台发布目标配置有误');
  config.load_config_file=false;config.backend={name:'github',repo:settings.repo,branch:settings.branch,base_url:auth.origin,auth_methods:['oauth']};config.site_url=settings.site_url;config.display_url=settings.site_url;
  window.CMS_MANUAL_INIT=true;
  await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src='https://unpkg.com/@sveltia/cms@0.269.2/dist/sveltia-cms.js';s.onload=resolve;s.onerror=()=>reject(Error('编辑器未能加载，请刷新重试'));document.head.append(s)});
  await window.CMS.init({config});document.getElementById('setup').hidden=true;document.getElementById('admin-note').hidden=false;
 }catch(e){message.textContent=e.message+'。请保留已写内容，稍后重试。';}
})();
