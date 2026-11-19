import hashlib,html,importlib.util,json,re,shutil,tempfile,unittest
from unittest.mock import patch
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('blog_build',ROOT/'scripts/build.py');build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

def paragraphs(s):return [html.unescape(re.sub('<[^>]+>','',p)).strip() for p in re.findall(r'<p>(.*?)</p>',s,re.S)]

class ContentBuildTest(unittest.TestCase):
 def setUp(self):
  self.environment=patch.dict('os.environ',{'GITHUB_SHA':'local-content-test'});self.environment.start();self.addCleanup(self.environment.stop)
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)/'source'
  shutil.copytree(ROOT,self.root,ignore=shutil.ignore_patterns('.git','dist','__pycache__','.venv'))
  # Regression cases use fixed fixtures so published edits never change their assumptions.
  shutil.rmtree(self.root/'content')
  shutil.copytree(ROOT/'tests/fixtures/content',self.root/'content')
  self.out=Path(self.temp.name)/'output'
 def tearDown(self):self.temp.cleanup()
 def test_existing_article_and_movement_are_preserved(self):
  build.build(self.root,self.out)
  def content(p):return re.search(r'<div class="content">(.*?)</div>',p.read_text(),re.S)[1]
  self.assertEqual(paragraphs(content(self.root/'blog-first.html')),paragraphs(content(self.out/'blog-first.html')))
  def data(p):return json.loads(re.search(r'<script id="journal-data" type="application/json">(.*?)</script>',p.read_text(),re.S)[1])
  before=data(self.root/'journal.html');after=data(self.out/'journal.html')
  for key in ['rides','activities','strengths']:self.assertEqual(before[key],after[key])
  self.assertFalse((self.out/'content').exists());self.assertFalse((self.out/'scripts').exists())
 def test_new_article_photo_update_and_delete(self):
  # A newer photo must not change which record is edited or deleted.
  extra={'id':'newer-photo','date':'2026-11-19','caption':'新照片','image':'/fly-blog/photos/assets/light.jpg','sample':False}
  (self.root/'content/photos/newer-photo.json').write_text(json.dumps(extra))
  a={'id':'new-entry','date':'2026-11-19','category':'you','title':'骑行小记','summary':'','body':'## 今日\n\n正文与一张照片。\n\n![图](/fly-blog/photos/assets/light.jpg)'}
  p=self.root/'content/articles/new-entry.json';p.write_text(json.dumps(a))
  build.build(self.root,self.out);self.assertTrue((self.out/'posts/new-entry.html').is_file())
  page=(self.out/'posts/new-entry.html').read_text();self.assertIn('<base href="../">',page);self.assertIn('骑行小记',page)
  self.assertIn('1 篇',(self.out/'index.html').read_text())
  photo=self.root/'content/photos/sample-lake.json';d=json.loads(photo.read_text());d['caption']='修改配文';photo.write_text(json.dumps(d))
  build.build(self.root,self.out)
  entries=json.loads((self.out/'photos/entries.json').read_text())['entries']
  self.assertEqual(entries[0]['id'],'newer-photo')
  self.assertEqual(next(r for r in entries if r['id']=='sample-lake')['caption'],'修改配文')
  p.unlink();photo.unlink();build.build(self.root,self.out);self.assertFalse((self.out/'posts/new-entry.html').exists())
  self.assertEqual({r['id'] for r in json.loads((self.out/'photos/entries.json').read_text())['entries']},{'sample-light','newer-photo'})
 def test_invalid_content_and_asset_paths_are_rejected(self):
  for bad in ['../.git/config','/fly-blog/uploads/../../.git/config','https://example.com/a.jpg','/fly-blog/uploads/missing.jpg','javascript:alert(1)']:
   with self.subTest(path=bad),self.assertRaises(ValueError):build.safe_asset(bad,self.root)
  p=self.root/'content/articles/blog-first.json';d=json.loads(p.read_text());d['id']='../../escape';p.write_text(json.dumps(d))
  with self.assertRaises(ValueError):build.load_content(self.root)
 def test_markdown_does_not_execute_raw_html_or_javascript_links(self):
  rendered=build.MD.render('<script>alert(1)</script>\n\n[x](javascript:alert(1))\n\n![x](data:text/html,evil)')
  self.assertNotIn('<script>',rendered);self.assertNotIn('href="javascript:',rendered);self.assertNotIn('src="data:text/html',rendered)
 def test_drafts_and_unknown_output_folders_are_not_published(self):
  p=self.root/'content/articles/blog-first.json';d=json.loads(p.read_text());d['draft']=True;p.write_text(json.dumps(d))
  with self.assertRaises(ValueError):build.load_content(self.root)
  self.out.mkdir();(self.out/'personal.txt').write_text('keep')
  with self.assertRaises(ValueError):build.build(self.root,self.out)
  self.assertTrue((self.out/'personal.txt').exists())

if __name__=='__main__':unittest.main()
