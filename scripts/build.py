"""Build public pages from published content; never read local health exports."""
import argparse, datetime as dt, hashlib, html, json, os, re, shutil, subprocess
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
from markdown_it import MarkdownIt

ROOT=Path(__file__).resolve().parents[1]
CATEGORIES={'nian':'念','kong':'空','you':'游','yangquan':'漾泉'}
SITE_URL='https://li1clbxyqsh1-ship-it.github.io/fly-blog/'
BASE_PATH='/fly-blog/'
MD=MarkdownIt('commonmark',{'html':False}).enable('table').enable('strikethrough')

def esc(value):return html.escape(str(value),quote=True)
def write_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':')).replace('</','<\\/'),encoding='utf-8')

def required(row,key):
    v=row.get(key)
    if not isinstance(v,str) or not v.strip():raise ValueError(f'{key}不能为空')
    return v.strip()

def safe_asset(value,root):
    if not value:return ''
    if not isinstance(value,str):raise ValueError('图片地址必须是文字')
    u=urlsplit(value)
    if u.scheme or u.netloc or u.query or u.fragment:raise ValueError('图片需要先上传到博客')
    path=unquote(u.path)
    if path.startswith(BASE_PATH):path=path[len(BASE_PATH):]
    if path.startswith('/') or '\\' in path or any(ord(c)<32 for c in path):raise ValueError('图片地址无效')
    parts=PurePosixPath(path).parts
    if '..' in parts or not parts or parts[0] not in ['uploads','photos']:raise ValueError('图片地址超出允许范围')
    target=root/path
    if not target.is_file() or not target.resolve().is_relative_to(root.resolve()):raise ValueError(f'图片不存在：{path}')
    if target.suffix.lower() not in ['.jpg','.jpeg','.png','.webp','.gif']:raise ValueError('图片格式不支持')
    data=target.read_bytes()
    valid=data.startswith((b'\xff\xd8\xff',b'\x89PNG\r\n\x1a\n',b'GIF87a',b'GIF89a')) or (data[:4]==b'RIFF' and data[8:12]==b'WEBP')
    if not valid or len(data)>1048576:raise ValueError('图片格式有误或大于1MB，请重新压缩上传')
    return BASE_PATH+path

def load_content(root):
    articles=[];photos=[]
    for kind,items in [('articles',articles),('photos',photos)]:
        seen=set()
        for p in sorted((root/'content'/kind).glob('*.json')):
            if p.is_symlink():raise ValueError('内容不能使用符号链接')
            row=json.loads(p.read_text(encoding='utf-8'));uid=required(row,'id');date=required(row,'date')
            if not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}',uid) or uid in seen:raise ValueError('记录编号无效或重复')
            seen.add(uid)
            if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):raise ValueError('日期需要为YYYY-MM-DD')
            dt.date.fromisoformat(date)
            if row.get('draft'):raise ValueError('不要把私密草稿提交到公开内容目录')
            if kind=='articles':
                title=required(row,'title');body=required(row,'body');category=required(row,'category')
                if category not in CATEGORIES or len(title)>200 or len(body)>500000:raise ValueError('文章栏目或长度有误')
                content=MD.render(body);summary=row.get('summary','').strip()
                if not summary:summary=re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>','',content))).strip()[:90]
                items.append({'id':uid,'date':date,'category':category,'title':title,'summary':summary,'meta':str(row.get('meta','')),'content':content,'cover':safe_asset(row.get('cover',''),root),'url':'blog-first.html' if uid=='blog-first' else f'posts/{uid}.html'})
            else:
                caption=required(row,'caption')
                if len(caption)>500:raise ValueError('照片配文请控制在500字以内')
                items.append({'id':uid,'date':date,'caption':caption,'image':safe_asset(required(row,'image'),root),'sample':row.get('sample') is True})
        items.sort(key=lambda r:(r['date'],r['id']),reverse=True)
    return articles,photos

def replace_once(text,pattern,replacement,label,flags=re.S):
    result,n=re.subn(pattern,replacement,text,count=1,flags=flags)
    if n!=1:raise ValueError('找不到页面锚点：'+label)
    return result

def article_page(template,article):
    category=CATEGORIES[article['category']];title=article['title'];url=SITE_URL+article['url']
    content=f'<article class="article"><div class="content-context"><a href="category.html?section={article["category"]}">{category}</a><span aria-hidden="true">/</span><span>文章</span></div><div class="content-title-row"><h1>{esc(title)}</h1><a class="back" href="category.html?section={article["category"]}">返回{category}</a></div><div class="meta">{esc(article["date"].replace("-","."))}　{esc(article["meta"])}</div><div class="content">{article["content"]}</div></article>'
    if article['cover']:content=content.replace('<div class="content">',f'<img src="{esc(article["cover"])}" alt="" style="display:block;width:100%;max-height:500px;object-fit:contain;margin:22px 0"><div class="content">',1)
    page=replace_once(template,r'<article class="article">.*?</article>',lambda _:content,'文章正文')
    page=replace_once(page,r'<title>.*?</title>',lambda _:f'<title>{esc(title)} · {category} · 闻日光</title>','文章标题')
    meta=f'<meta name="description" content="{esc(article["summary"])}"><link rel="canonical" href="{esc(url)}">'
    page=page.replace('</head>',meta+'</head>')
    if article['url'].startswith('posts/'):page=page.replace('<head>','<head><base href="../">',1)
    return page

def build(root,out):
    root=root.resolve();out=out.resolve()
    if out==root or root.is_relative_to(out):raise ValueError('输出目录不能覆盖源文件')
    if out.exists():
        if out.is_symlink() or not (out/'.wrg-generated').is_file():raise ValueError('仅允许重建带有生成标识的输出目录')
        shutil.rmtree(out)
    out.mkdir(parents=True);(out/'.wrg-generated').write_text('Generated blog assets only.\n')
    for p in root.iterdir():
        if p.is_file() and (p.suffix.lower() in ['.html','.css','.js','.png','.jpg','.jpeg','.webp'] or p.name in ['CREDITS.md','LEAFLET-LICENSE.txt','.nojekyll']):shutil.copyfile(p,out/p.name)
    for folder in ['photos','admin','uploads']:
        if (root/folder).exists():
            for p in (root/folder).rglob('*'):
                if p.is_symlink():raise ValueError('静态文件不能使用符号链接')
            shutil.copytree(root/folder,out/folder,ignore=shutil.ignore_patterns('*.md','.*'))
    articles,photos=load_content(root)
    journal=(root/'journal.html').read_text(encoding='utf-8')
    pattern=r'(<script id="journal-data" type="application/json">)(.*?)(</script>)'
    match=re.search(pattern,journal,re.S)
    if not match:raise ValueError('找不到已有运动数据')
    data=json.loads(match[2]);original_movement=hashlib.sha256(json.dumps({k:data[k] for k in ['rides','activities','strengths']},sort_keys=True).encode()).hexdigest()
    data['articles']=articles
    payload=json.dumps(data,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
    journal=replace_once(journal,pattern,lambda m:m[1]+payload+m[3],'内容数据')
    old="const filtered=isYou?all.filter(r=>journalType==='all'||r.kind===journalType):DATA.articles.filter(r=>r.category===categoryKey);"
    new="const posts=DATA.articles.filter(r=>r.category===categoryKey).map(r=>({...r,kind:'article'}));const filtered=(isYou?[...all.filter(r=>journalType==='all'||r.kind===journalType),...(['all','article'].includes(journalType)?posts:[])]:posts).sort((a,b)=>b.date.localeCompare(a.date));"
    if old not in journal:raise ValueError('栏目脚本版本需要核对')
    journal=journal.replace(old,new).replace("const href=isYou?activityHref(r):`#article/${r.id}`;","const isMovement=isYou&&r.kind!=='article';const href=isMovement?activityHref(r):`#article/${r.id}`;")
    journal=journal.replace('const meta=isYou?','const meta=isMovement?').replace('esc(isYou?itemTitle(r):r.title)','esc(isMovement?itemTitle(r):r.title)')
    journal=journal.replace("`${all.length.toLocaleString()} 条运动记录 · ${rides.length.toLocaleString()} 条骑行轨迹`","`${all.length.toLocaleString()} 条运动记录 · ${posts.length} 篇文章`")
    journal=journal.replace('<option value="cycling">骑行</option>','<option value="cycling">骑行</option><option value="article">文章</option>')
    journal=journal.replace("$('article-content').innerHTML=article.content;","$('article-content').innerHTML=(article.cover?`<img src=\"${esc(article.cover)}\" alt=\"\" style=\"display:block;width:100%;max-height:500px;object-fit:contain;margin:22px 0\">`:'')+article.content;")
    (out/'journal.html').write_text(journal,encoding='utf-8')
    template=(root/'blog-first.html').read_text(encoding='utf-8')
    for article in articles:
        p=out/article['url'];p.parent.mkdir(parents=True,exist_ok=True);p.write_text(article_page(template,article),encoding='utf-8')
    if not any(a['id']=='blog-first' for a in articles):(out/'blog-first.html').unlink(missing_ok=True)
    home=(out/'index.html').read_text(encoding='utf-8')
    counts={key:sum(a['category']==key for a in articles) for key in CATEGORIES}
    labels={'nian':f'{counts["nian"]} 篇','kong':f'{counts["kong"]} 篇','you':f'{len(data["activities"]):,} 条'+(f' · {counts["you"]} 篇' if counts['you'] else ''),'yangquan':(f'{len(photos)} 张示例' if photos and all(p['sample'] for p in photos) else f'{len(photos)} 张')+(f' · {counts["yangquan"]} 篇' if counts['yangquan'] else '')}
    for key,label in labels.items():home=replace_once(home,r'(<a class="card" href="category.html\?section='+key+r'">.*?<span class="count">).*?(</span>)',lambda m:m[1]+label+m[2],'首页计数')
    entries=''.join(f'<a class="entry" href="{esc(a["url"])}"><time class="date">{a["date"].replace("-",".")}</time><span><strong>{esc(a["title"])}</strong><small>{esc(a["summary"])}</small></span><span class="tag">{CATEGORIES[a["category"]]}</span></a>' for a in articles[:5]) or '<p class="empty">暂无文章</p>'
    home=replace_once(home,r'(<section class="recent" id="recent"><div class="section-head"><h2>最近写下</h2></div>).*?(</section>)',lambda m:m[1]+entries+m[2],'最近文章')
    home=home.replace('</footer>',' <a href="admin/" style="margin-left:16px;font-size:12px">管理</a></footer>')
    (out/'index.html').write_text(home,encoding='utf-8')
    write_json(out/'photos/entries.json',{'entries':photos,'articles':[a for a in articles if a['category']=='yangquan']})
    if (root/'scripts/photo-reader.js').exists():shutil.copyfile(root/'scripts/photo-reader.js',out/'photos/app.js')
    revision=os.environ.get('GITHUB_SHA') or subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
    report={'revision':revision,'built_at':dt.datetime.now(dt.timezone.utc).isoformat(),'articles':len(articles),'photos':len(photos),'movement_checksum':original_movement}
    write_json(out/'build.json',report)
    total=sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    if total>900*1024**2:raise ValueError('网站接近平台容量上限，请先处理图片存储')
    print(json.dumps({**report,'bytes':total,'capacity_notice':total>=200*1024**2},ensure_ascii=False))
    return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist');args=parser.parse_args()
    build(ROOT,args.output)
