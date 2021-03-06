#encoding: utf8
import os
import subprocess

class scrape_exemptions(object):

    def process(self,input,output,since='yesterday',PROXY=None):
        env = os.environ.copy()
        if PROXY is not None:
            env['PROXY'] = PROXY
        scraper = subprocess.Popen(['/usr/bin/env',
                                  'python',
                                  'exemption_updated_records_scraper.py',
                                  '--scrape=%s' % since,
                                  'intermediates','--update'],
                                  cwd='tenders',env=env)
        scraper.wait()
