# -*- coding: utf-8 -*-
"""pred_char_transformer_txt_rus_final_acc_no_batch.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1-YMfTQTtHlpGGkk3UkHk6w0xFqQBP3N_
"""

from __future__ import unicode_literals, print_function, division 
from io import open 
import string
import re
import unicodedata
import random 
import matplotlib.pyplot as plt
#plt.switch_backend("agg")
import matplotlib.ticker as ticker 
import numpy as np
import time
import math

#!pip install thai_tokenizer 
#from thai_tokenizer import Tokenizer
#from torchtext.data.utils import get_tokenizer
from torchtext.vocab import build_vocab_from_iterator
from torch.nn.utils.rnn import pad_sequence

import torch
import torch.nn as nn
from torch import optim
import torch.nn.functional as F

device=torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.manual_seed(123456789)


##############3
#Functions that transform the words in numbers. Needs a tokenizer since in certain languages 
#1 english word=n other language words 
###############

src_lang="En"
tgt_lang="Rus"


unk_idx=0
pad_idx=1
bos_idx=2
eos_idx=3

class PositionalEncoding(nn.Module):
    def __init__(self,emb_size:int,dropout:float,maxlen=5000):
        super().__init__()
        den=torch.exp(-torch.arange(0,emb_size,2)*math.log(10000)/emb_size)
        pos=torch.arange(0,maxlen).reshape(maxlen,1)
        pos_embedding=torch.zeros((maxlen,emb_size))
        pos_embedding[:,0::2]=torch.sin(pos*den)
        pos_embedding[:,1::2]=torch.cos(pos*den)
        pos_embedding=pos_embedding.unsqueeze(-2)
        
        self.dropout=nn.Dropout(dropout)
        self.register_buffer("pos_embedding",pos_embedding)
        
    def forward(self,token_embedding):
        return self.dropout(token_embedding+self.pos_embedding[:token_embedding.size(0),:])
        
class TokenEmbedding(nn.Module):
    def __init__(self,vocab_size,embed_size):
        super().__init__()
        self.embedding=nn.Embedding(vocab_size,emb_size)
        self.emb_size=emb_size
        
    def forward(self,tokens):
        return self.embedding(tokens.long())*math.sqrt(self.emb_size)
        
        
class seq2seqTransformer(nn.Module):
    def __init__(self,num_encoder_layers,num_decoder_layers,emb_size,nhead,src_vocab_size,tgt_vocab_size,
                dim_feedforward=512,dropout=0.1):
        super().__init__()
        self.transformer=nn.Transformer(d_model=emb_size,nhead=nhead,num_encoder_layers=num_encoder_layers,
                                       num_decoder_layers=num_decoder_layers,dim_feedforward=dim_feedforward,dropout=dropout)
        
        self.generator=nn.Linear(emb_size,tgt_vocab_size)
        self.src_tok_emb=TokenEmbedding(src_vocab_size,emb_size)
        self.tgt_tok_emb=TokenEmbedding(tgt_vocab_size,emb_size)
        self.positional_encoding=PositionalEncoding(emb_size,dropout)
        
    def forward(self,src,tgt,src_mask,tgt_mask,src_padding_mask,tgt_padding_mask,memory_key_padding_mask):
        src_emb=self.positional_encoding(self.src_tok_emb(src))
        tgt_emb=self.positional_encoding(self.tgt_tok_emb(tgt))
        out=self.transformer(src_emb,tgt_emb,src_mask,tgt_mask,None,src_padding_mask,tgt_padding_mask,memory_key_padding_mask) 
        out=self.generator(out)
        return out
    
    def encode(self, src, src_mask):
        return self.transformer.encoder(self.positional_encoding(self.src_tok_emb(src)),src_mask)
    
    def decode(self,tgt,memory,tgt_mask):
        return self.transformer.decoder(self.positional_encoding(self.tgt_tok_emb(tgt)),memory,tgt_mask)
        

def generate_square_mask(size):
    mask=(torch.triu(torch.ones((size,size),device=device))==1).transpose(0,1)   #make lower triangular with 1's
    #make suare matrix in upper triangle has -inf and in the lower triangle it has 0.0
    mask=mask.float().masked_fill(mask==0,float("-inf")).masked_fill(mask==1,float(0.0))   
    return mask

class Lang:
    def __init__(self,lang):
        self.lang=lang
        self.char2index={}
        self.char2count={}
        self.index2char={0: "<unk>", 1:"<pad>", 2:"<bos>", 3:"<eos>" }
        self.n_chars=4
        
    def addName(self,sentence):
        for char in sentence:
            self.addChar(char)
            
    def addChar(self, char):
        if char not in self.char2index:
            self.char2index[char]=self.n_chars
            self.char2count[char]=1
            self.index2char[self.n_chars]=char
            self.n_chars+=1
        else:
            self.char2count[char]+=1 
            
token_transform = {}
def timming(since):
    now=time.time()
    s=now-since
    m=int(s/60)
    s=s-m*60
    return "%dm %ds"%(m,s)
def unicodeToAscii(s):
        return ''.join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")
def normalizeString(string):
    string=unicodeToAscii(string.lower().strip())
    string=re.sub(r"([.!?])",r" \1",string)
    string=string.replace(",","")
    return string

def readLangs(src_lang,tgt_lang,reverse):
    
    forbidden_chars=['\u200e','\u200b','\u200f','ª',')','|','[',']','ǃ','$','‐','?','+','̱','̄','̜','̕','︡', '︠','̈',"ʿ",'"',"ʹ","ʼ","‘","′","'́'","«","»","\xad","\\"]
    apostrophes=["`","’","ʻ","ʾ","'"]
    chirilic=["А", "Б", "В", "Г", "Д", "Е", "Ё", "Ж", "З", "И", "Й", "К", "Л", "М", "Н", "О", "П", "Р", "С", "Т", "У", "Ф", "Х", "Ц", "Ч", "Ш", "Щ", "Ъ", 
              "Ы", "Ь", "Э", "Ю", "Я"]
    chirilic=[char.lower() for char in chirilic]
    sh=["ş","ṣ","ș"]

    print("reading lines...")
    
    #lines=open("/content/drive/MyDrive/WunderSchildt/Transformer/Data/%s-%s Names.txt"%(src_lang,tgt_lang),encoding="UTF-8").read().strip().split("\n")
    lines=open("/content/drive/MyDrive/WunderSchildt/Translation/Data/%s-%s Names.txt"%(src_lang,tgt_lang),encoding="UTF-8").read().strip().split("\n")
    pairs=[]
    i=0
    while i<=len(lines)-1:
      flag=1
      #Keep turkish, etc names or not?
      #lines[i]=unicodeToAscii(lines[i])
      if "-" in lines[i]:
        lines[i]=lines[i].replace("-","-")
      if "–" in lines[i]:
        lines[i]=lines[i].replace("–","-")
      for forbidden_char in forbidden_chars:
        if forbidden_char in lines[i]:
          lines[i]=lines[i].replace(forbidden_char,"")
      for apos in apostrophes:
        if apos in lines[i]:
          lines[i]=lines[i].replace(apos,"'") 
      for s in sh:
        if s in lines[i]:
          lines[i]=lines[i].replace(s,"ş")
      
      if reverse==False:
        s_input=lines[i].split("\t")[0]
        s_output=lines[i].split("\t")[1]
        temp_output=s_output.replace(" ","").replace(",","").replace("-","")
        temp_output=[char.lower() for char in temp_output]
        for char in temp_output:
          if char not in chirilic:
            flag=0
            break
      else:
        s_output=lines[i].split("\t")[0]
        s_input=lines[i].split("\t")[1]
        temp_input=s_input.replace(" ","").replace(",","").replace("-","")
        temp_input=[char.lower() for char in temp_input]
        for char in temp_input:
          if char not in chirilic:
            flag=0
            break

      if flag==0:
        i+=1
      else:
        if "," in lines[i]:
          if "," in s_output:
            temp=s_output.split(",")
            temp=[word.replace(" ","") for word in temp]
            temp=[temp[len(temp)-i] for i in range(1,len(temp)+1)]
            s_output=" ".join(temp)
            s_output=[char.lower() for char in s_output]
          if "," in s_input:
            temp=s_input.split(",")
            temp=[word.replace(" ","") for word in temp]
            temp=[temp[len(temp)-i] for i in range(1,len(temp)+1)]
            s_input=" ".join(temp) 
            s_input=[char.lower() for char in s_input]    
          pairs.append([s_input,s_output])
        else: 
          s_input=[char.lower() for char in s_input]
          s_output=[char.lower() for char in s_output]
          pairs.append([s_input,s_output])
        i+=1

    if reverse:
        #pairs=[list(reversed(p)) for p in pairs]
        input_lang=Lang(tgt_lang)
        output_lang=Lang(src_lang)
    else:
        input_lang=Lang(src_lang)
        output_lang=Lang(tgt_lang) 
        
    return input_lang, output_lang, pairs

def prepareData(src_lang,tgt_lang,reverse):
    input_lang, output_lang, pairs=readLangs(src_lang,tgt_lang,reverse)
    #token_transform[src_lang] = get_tokenizer('spacy', language='en_core_web_sm')
    #token_transform[tgt_lang] = get_tokenizer('spacy', language='rus')
    print("Read %s name pairs"%len(pairs))
    print("Counting characters:")
    for pair in pairs:      
        input_lang.addName(pair[0])
        output_lang.addName(pair[1]) 
        
    print("counted characters:")
    print(input_lang.lang,input_lang.n_chars) 
    print(output_lang.lang,output_lang.n_chars) 
    
    return input_lang,output_lang, pairs


def prepareData(src_lang,tgt_lang,reverse=False):
    input_lang, output_lang, pairs=readLangs(src_lang,tgt_lang,reverse=False)
    #token_transform[src_lang] = get_tokenizer('spacy', language='en_core_web_sm')
    #token_transform[tgt_lang] = get_tokenizer('spacy', language='rus')
    print("Read %s name pairs"%len(pairs))
    print("Counting characters:")
    for pair in pairs:      
        input_lang.addName(pair[0])
        output_lang.addName(pair[1])
        
    print("counted characters:")
    print(input_lang.lang,input_lang.n_chars)
    print(output_lang.lang,output_lang.n_chars) 
    
    return input_lang,output_lang, pairs

input_lang, output_lang, pairs=prepareData(src_lang,tgt_lang,reverse=True)


transformer=torch.load("/content/drive/MyDrive/WunderSchildt/Translation/Saved_models/Char transformer, rus, names 50000,embedding 512, loss 4.0000, layers 0, acc 39.69%.pth",
                       map_location=torch.device('cpu'))

src_vocab_size=input_lang.n_chars
tgt_vocab_size=output_lang.n_chars
emb_size=512
nhead=8
#ffn_hid_dim=256
batch_size=32
num_encoder_layers=4
num_decoder_layers=4


start=time.time()
src_name="Irina Mironova"
#tgt_name=pairs_test[0][1]
src_list=[input_lang.char2index[char] for char in src_name]
src_list.insert(0,bos_idx)
src_list.append(eos_idx)
src=torch.tensor(src_list,dtype=torch.long,device=device).view(-1,1)
src=src.view(src.shape[0],1,1)
#src=pad_sequence(src,padding_value=pad_idx)

src=src[:,0].to(device)
src_seq_len=src.shape[0]
src_mask=torch.zeros((src_seq_len,src_seq_len),device=device).type(torch.bool)
memory=transformer.encode(src,src_mask)
ys=torch.ones(1,1).fill_(bos_idx).type(torch.long).to(device)
num_tokens=src.shape[0]
max_len=num_tokens+5
memory=memory.to(device)

for j in range(max_len-1):
  tgt_mask=(generate_square_mask(ys.size(0))).type(torch.bool).to(device)
  out=transformer.decode(ys,memory,tgt_mask)
  out=out.transpose(0,1) 
  prob=transformer.generator(out[:,-1])
  _, next_char=torch.max(prob,dim=1)
  next_char=next_char.item()

  ys=torch.cat([ys,torch.ones(1,1).type_as(src.data).fill_(next_char)],dim=0) 
  if next_char==eos_idx:
    break

ys=ys.flatten().cpu().numpy()
output_name="".join([output_lang.index2char[idx] for idx in ys]).replace("<bos>","").replace("<eos>","")
#tgt_name="".join([char for char in tgt_name]).replace("<bos>","").replace("<eos>","")
      #output_name=output_name.split(" ")

output_name=output_name.split(" ")
#tgt_name=tgt_name.split(" ")
print("Source name: ", src_name)
print("Prediction: ", output_name)
#print("Target: ", tgt_name) 
print("Time taken: ",timming(start))