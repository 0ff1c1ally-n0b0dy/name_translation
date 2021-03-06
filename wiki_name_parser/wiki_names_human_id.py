# -*- coding: utf-8 -*-
"""wiki_names_human_id.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1j1vITS915Rzpfg1-a9aYVzHI7As7iQ-i
"""

import requests 
import json 
import pandas as pd
import time

def timming(since):
    now=time.time() 
    s=now-since
    m=int(s/60)
    s=s-m*60
    return "%dm %ds"%(m,s)

languages=["en","fr","ru","ar","arz","ast","azb","az","bar","be_x_old","be","bg","bn","bs","ca","cs","cy","da","de","el","en","eo","es","et","eu","fa","fi","fr","ga","gl","he","hr","hu","hy","ia",
           "id","ie","io","is","it","ja","jv","ka","ko","kw","ky","la","lfn","lt","lv","mg","mk","ml","mrj","mr","ms","nl","nn","no","oc","pa","pl","pnb","pt","ro","ru","sco","sc","sh","simple","sk",
           "sl","sq","sr","sv","ta","tr","uk","ur","vep","vl","war","wuu","zh_min_nan","zh_yue","zh"]
printing_iter=10**(2)
file1=open("/content/drive/MyDrive/WunderSchild/Translation/Parser/Names_En-All/Names_En_All_human_id.txt","w")
count_links=1
count_people=0
start=time.time()
line=""

while True:
  prefix="Q"+str(count_links)
  link="https://www.wikidata.org/wiki/Special:EntityData/%s.json"%(prefix) 
  try:
    response = requests.get(link)
    if (response.status_code != 204 and response.headers["content-type"].strip().startswith("application/json")):
      try:
        person = json.loads(response.content)
        flag=1
      except ValueError: 
        flag=0
  except ValueError:
    flag=0 
  if flag==1:
    if prefix in person["entities"].keys(): 
      if "P31" in person["entities"][prefix]["claims"].keys():
        if "mainsnak" in person["entities"][prefix]["claims"]["P31"][0].keys():
          if "datavalue" in person["entities"][prefix]["claims"]["P31"][0]["mainsnak"].keys():
            if "value" in person["entities"][prefix]["claims"]["P31"][0]["mainsnak"]["datavalue"].keys():
              if "id" in person["entities"][prefix]["claims"]["P31"][0]["mainsnak"]["datavalue"]["value"].keys():
                if person["entities"][prefix]["claims"]["P31"][0]["mainsnak"]["datavalue"]["value"]["id"]=="Q5":
                  if "entities" in person.keys():   
                    if prefix in person["entities"].keys():
                      if "labels" in person["entities"][prefix].keys(): 
                        if "en" in person["entities"][prefix]["labels"].keys():
                          person_name=person["entities"][prefix]["labels"]["en"]["value"]
                          if len(person_name.split(" "))>=2:
                            count_people+=1
                            line="["+str(count_people)+"] \t"
                            person_name=person["entities"][prefix]["labels"]["en"]["value"]
                            for lang in languages:
                              if lang in person["entities"][prefix]["labels"].keys():
                                line+=lang+":"+person["entities"][prefix]["labels"][lang]["value"]+"\t"
                            line+="\n"
                            file1.write(line)
                            #print(line)
  count_links+=1
  if count_links%printing_iter==0:
    print("Imported %d names \t Tried %d links \t Last name: %s \t %s time"%(count_people,count_links,person_name,timming(start)))

file1.close()







