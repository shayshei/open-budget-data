import json
import sys


KEY = "%s/%s-"
DEFAULT_YEARS = [2014,2015]


# if __name__ == "__main__":
#     process("../budgets-noequiv.aggregated-jsons","budget_equivalents.jsons")

class item_connections(object):

    def process(self,input_file,output_file,ref_years=DEFAULT_YEARS,curated=[]):
        all_codes = []
        h_eq = {}
        y_eq = { ref_year: {} for ref_year in ref_years }
        code_titles = {}
        title_for_code = {}

        with file(input_file) as input:
            for line in input:
                line = json.loads(line)
                code = str(line['code'])
                year = line['year']
                value = line.get('net_revised',0) + line.get('gross_revised',0)
                test_value = sum(line.get(x,0)**2 for x in ['net_allocated','gross_allocated','commitment_allocated','net_used'])
                if test_value == 0 and year not in ref_years:
                    continue
                title = line.get('title')
                if title is None:
                    continue
                if len(code) > 2:
                    parent_code = code[:-2]
                    h_eq.setdefault(KEY % (year,parent_code),[]).append(KEY % (year,code))
                code_titles.setdefault((code,title),[]).append(year)
                title_for_code[(code,year)] = (title,value)
                if year in ref_years:
                    all_codes.append(KEY % (year,code))

        for key,years in code_titles.iteritems():
            code,title = key
            years.sort()
            for i in range(len(years)-1):
                y1=years[i]
                y2=years[i+1]
                y_eq.setdefault(y1,{}).setdefault(KEY % (y2,code),[]).append(KEY % (y1,code))

        for preset_fn in curated:
            with file(preset_fn) as preset_file:
                presets = json.load(preset_file)
                for preset in presets:
                    key,keys = preset
                    #print key, keys
                    tgt_year = list(set(k[0] for k in keys))
                    assert(len(tgt_year)) == 1
                    tgt_year = tgt_year[0]
                    y_eq[tgt_year][KEY % tuple(key)] = [KEY % tuple(k) for k in keys]

        all_codes.sort(reverse=True)
        missing_links = {}
        target_years = range(1992,max(ref_years)+1)
        target_years.sort(reverse=True)
        for target_year in target_years:
            for key in all_codes:
                go_on = True
                equivs = [ key ]
                #print "KK %s,%d" % (key,target_year)
                bad_keys = []
                while go_on and equivs is not None:
                    #print "EEE %r" % equivs
                    go_on = False
                    new_equivs = []
                    failed = False
                    for k in equivs:
                        year = int(k.split("/")[0])
                        if year == target_year:
                            #print k,"F"
                            new_equivs.append(k)
                            continue
                        got_year = False
                        for test_year in range(target_year,max(ref_years)):
                            if y_eq[test_year].has_key(k):
                                #print k,"Y"
                                new_equivs.extend(y_eq[test_year][k])
                                go_on = True
                                got_year = True
                                break
                        if got_year:
                            continue
                        bad_keys.append(k)
                        if h_eq.has_key(k):
                            #print k,"H"
                            new_equivs.extend(h_eq.get(k))
                            go_on = True
                            continue
                        failed = True
                        #print k,"?"

                    if failed:
                        new_equivs = None
                    equivs = new_equivs
                if equivs is not None:
                    for x in equivs:
                        assert(x.startswith(str(target_year)))
                    if not y_eq[target_year].has_key(key):
                        y_eq[target_year][key] = equivs
                    if len(equivs)>1:
                        print "%s --> %r" % (key, equivs)
                else:
                    for bad_key in bad_keys:
                        year,code = bad_key.split('/')
                        code = code[:-1]
                        year = int(year)
                        #print "MISSING: %s -> %s (%r)" % (key, bad_key, equivs)
                        assert(code!='')
                        if missing_links.has_key(code):
                            if missing_links[code] < year:
                                missing_links[code] = year
                        else:
                            missing_links[code] = year

        out = {}
        for y,eqs in y_eq.iteritems():
            validation = {}
            for key,keys in eqs.iteritems():
                #print "XXXXXXX %r %r" % (key,keys)
                #if key.startswith(str(ref_year)):
                for tgtkey in keys:
                    validation.setdefault(tgtkey,[]).append(key)
                    out.setdefault((y,tgtkey.split('/')[1][:-1]),set()).add('E'+key[:-1])
                for y2 in range(1992,2020):
                    yearly_keys = [ k for k in keys if k.startswith(str(y2))]
                    if len(yearly_keys)==1:
                        out.setdefault((y,key.split('/')[1][:-1]),set()).add('E'+yearly_keys[0][:-1])
            for k,v in validation.iteritems():
                if len(v)>1:
                    for i in range(len(v)):
                        for j in range(len(v)):
                            if i != j and len(v[i]) > len(v[j]):
                                if not v[i][:-1].startswith(v[j][:-1]):
                                    print "VALIDATION:",k,v

        with file(output_file,"w") as output:
            for k,v in out.iteritems():
                year, code = k
                rec = { 'year': year,
                        'code': code,
                        'equiv_code': list(v) }
                output.write(json.dumps(rec,sort_keys=True)+"\n")
            # for tgt_year, eqs in y_eq.iteritems():
            #     for key, keys in eqs.iteritems():
            #         if not key.startswith(str(ref_year)):
            #             continue
            #         for tgt_key in keys:
            #             rec = { 'year': tgt_year,
            #                     'code': tgt_key.split('/')[1][:-1],
            #                     'equiv_code': 'E'+key[:-1] }
            #             output.write(json.dumps(rec,sort_keys=True)+"\n")

        output = file('missing-%s.csv' % year,'wb')
        missing_links = list(missing_links.iteritems())
        missing_links.sort(key=lambda x:int(str(x[1])+x[0]))
        #print "RRR %r" % missing_links[:10]
        for code,year in missing_links:
            title,value = title_for_code.get((code,year),(None,None))
            if title is None:
                print "BAD CODE FOUND: %s/%s" % (code,year)
                continue
            if value <= 0:
                print "DISREGARDING null value: %s/%s" % (code,year)
                continue
            title = title.encode('utf8')
            #print "T: %r,%r,%r" % (year,code,title)
            output.write('%s,"C%s","%s",%s\n' % (year,str(code),title.replace('"','""'),value))

if __name__ == "__main__":
    inputs = sys.argv[1]
    output = sys.argv[2]
    curated = sys.argv[3:]
    processor = item_connections().process(inputs,output,ref_years=[2014,2015],curated=curated)
