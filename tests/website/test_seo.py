"""SEO maintenance must preserve metadata through normal HTML formatting changes."""
import importlib.util, unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('seo',Path(__file__).resolve().parents[2]/'utils/website/seo.py')
seo=importlib.util.module_from_spec(spec);spec.loader.exec_module(seo)
class MetadataTests(unittest.TestCase):
    def test_reordered_attributes_and_duplicate_canonical(self):
        page='<html><head><title>Monzero &amp; mining</title><meta content="Private payments &amp; CPU mining." name="description"/><link href="https://old.example/" rel="canonical"/><meta content="" property="og:description"/></head></html>'
        updated=seo.update(page,'/mining/')
        tags=seo.Metadata(updated).values
        self.assertEqual(tags['description'],tags['og:description'])
        self.assertEqual(tags['description'],tags['twitter:description'])
        self.assertEqual(updated.count('rel="canonical"'),1)
        self.assertNotIn('old.example',updated)
        self.assertEqual(updated,seo.update(updated,'/mining/'))
    def test_editorial_sharing_copy_is_preserved(self):
        page='<title>Site title</title><meta content="General description" name="description"><meta content="Sharing title" property="og:title"><meta content="Sharing description" property="og:description">'
        values=seo.Metadata(seo.block(page,'/')).values
        self.assertEqual(values['og:title'],'Sharing title')
        self.assertEqual(values['og:description'],'Sharing description')
if __name__=='__main__':unittest.main()
