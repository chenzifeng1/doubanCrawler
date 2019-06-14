#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import MySQLdb
import time
import numpy
import logging
import re
import sys
import json
import ssl
import os
import importlib
from functools import reduce
from urllib import parse

importlib.reload(sys)


# state of tag_info
FINISHED = 1
UNFINISHED = 0
# tag page related
PAGE_ADD = 20
PAGE_END = 980
# max times to get same one url
MAX_TRY_TIMES = 20
# sleep time after disconnecting router
DISCON_SLEEP_TIME = 15
# some headers
HEADERSES=[{'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'}]
"""
HEADERSES=[{'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'},\
{'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36'},\
{'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'},\
{'User-Agent':'Mozilla/5.0 (Windows NT 6.2) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.12 Safari/535.11'},\
{'User-Agent': 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)'}]
"""
# set log format
global li_list
logging.basicConfig(level=logging.INFO,
                format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                datefmt='%a, %d %b %Y %H:%M:%S',
                filename='doubanspider.log',
                filemode='w')
# send important info to stderr as well
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

def getResult():
    conn = MySQLdb.connect(
        host='112.74.160.185',
        port=3306,
        user='root',
        password='czf001413',
        database='test',
        charset='utf8'
    )

    sqlStr = "select * from book_info where tag=\"随笔\" ;"
    #or tag = \"\" or tag =\"随笔\"or tag=\"心理学\" or tag=\"漫画\"
    cursor = conn.cursor()
    cursor.execute(sqlStr)
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def getDescId(conn):
    cursor = conn.cursor();
    sql = "select id from book_desc"
    cursor.execute(sql)
    result = [];
    for line in cursor.fetchall:
        result.append(line[0])
    return result



def get_html(url, headers,cookie):
    headers['Referer'] = url
    print(url)
    r = requests.get(url,cookie, headers = headers)
    if r.status_code != requests.codes.ok :
        logging.warning("requests error for url:%s, code:%d" % (url, r.status_code))
    if r.status_code == requests.codes.forbidden:
        logging.warning("requests is forbidden(403) for url:%s, need regain ip." % (url))
        r.raise_for_status()
    return r.content

# load tag info from db
def get_tags(conn):
    cur = conn.cursor()
    cur.execute("select `id`, `name`, `page`, `is_end` from `tag_info`")
    tag_list = []
    for row in cur.fetchall():
        # load unfinished tag only
        if row[3] == UNFINISHED:
            tag_list.append({'id':row[0], 'name':row[1] , 'page':row[2], 'is_end':row[3]})
            #tag_list.append({'id': row[0], 'name': row[1], 'page': row[2], 'is_end': row[3]})
    cur.close()
    return tag_list

def do_spider(conn, tag_list):
    for tag_info in tag_list:
        fetch_books(conn, tag_info)
    logging.info('all books in tags is fetched!')

def fetch_books(conn, tag_info):
    logging.info("start fetching books in tag:%s" % tag_info['name'])
    cur = conn.cursor()
    fetch_count = 0
    time.sleep(numpy.random.rand()*2)

    while tag_info['is_end'] == UNFINISHED:
        name =parse.quote(str(tag_info['name']))
        url = 'https://book.douban.com/tag/' + name+ '?start=' + str(tag_info['page']) + '&type=T'

        headers = HEADERSES[fetch_count % len(HEADERSES)]

        for times in range(1, MAX_TRY_TIMES):
            try:
                content = get_html(url, headers)
                soup = BeautifulSoup(content, "lxml")
                ul = soup.body.find('ul', attrs = {'class':'subject-list'})
                li_list = ul.find_all('li')
                break
            except requests.exceptions.HTTPError as e:
                #raise requests.exceptions.HTTPError, e
                print("error"+e)

        print("step 1 over")
        # get all book info of this page
        book_info_list = []
        for li in li_list:
            # get book url
            time.sleep(numpy.random.rand())
            div = li.find('div', attrs = {'class':'info'})
            book_url = div.a['href']
            for times in range(1, MAX_TRY_TIMES):
                try:
                    book_content = get_html(book_url, headers)
                    soup = BeautifulSoup(book_content, "lxml")
                    bkif = fetch_book_info(book_url, soup)
                    book_info_list.append(bkif)
                    break

                except requests.exceptions.HTTPError as e:
                    #raise requests.exceptions.HTTPError, e
                    print(e)
                except Exception as e:
                    logging.warning("requests exception for url:%s,exception:%s,try times:%d" % (book_url, e, times))
                    time.sleep(numpy.random.rand() * 2)

        # update tag_info and save book_infos to db
        # logging.info("book_info_list:%s" % book_info_list)
        logging.info("finish tag:%s, page:%d" %(tag_info['name'], tag_info['page']))
        # page is end
        if li_list == []:
            tag_info['is_end'] = FINISHED
            save_tag(cur, tag_info)

        else:

            save_tag_book(cur, tag_info, book_info_list)
        fetch_count += 1

    logging.info("finish fetching books in tag:%s" % tag_info['name'])
    cur.close()

def save_tag(cur, tag_info):
    cur.execute("UPDATE `tag_info` SET `page` = %d, `is_end` = %s WHERE `id` = %d" %(tag_info['page'], tag_info['is_end'], tag_info['id']))
    conn.commit()

def save_tag_book(cur, tag_info, book_info_list):
    if tag_info['page'] >= PAGE_END:
        tag_info['is_end'] = FINISHED
    else:
        tag_info['page'] += PAGE_ADD
    books_sql = make_sql(book_info_list,tag_info['name'])
    cur.execute(books_sql)
    cur.execute("UPDATE `tag_info` SET `page` = %d, `is_end` = %s WHERE `id` = %d" %(tag_info['page'], tag_info['is_end'], tag_info['id']))
    conn.commit()

def make_sql(book_info_list,tag):
    str_list = []
    for book_info in book_info_list:
        string = "(%s,'%s','%s','%s','%s','%s',%s,'%s',%s,%s,'%s')" %(book_info['id'], book_info['book_name'], book_info['author'], book_info['publisher'], book_info['translator'], book_info['publish_date'], book_info['page_num'], book_info['isbn'], book_info['score'], book_info['rating_num'],tag)
        str_list.append(string)
    strings = ','.join(str_list)
    sql = "REPLACE INTO `book_info`(`id`, `book_name`, `author`, `publisher`, `translator`, `publish_date`, `page_num`, `isbn`, `score`, `rating_num`,`tag`) VALUES %s" % strings
    # logging.info("sql:%s" % sql)
    print(sql)
    return sql

# strip special characters
def strip_blank(string):
    new_string = string.replace("'","")
    new_string = "".join(new_string.split())
    return new_string

def fetch_book_info(book_url, soup):
    book_info = {'id':0, 'book_name':'NULL', 'author':'NULL', 'publisher':'NULL',
        'translator':'NULL', 'publish_date':'NULL', 'page_num':0, 'isbn':'NULL',
        'score':0.0, 'rating_num':0}
    body = soup.body
    # get book_name
    wrapper = body.find('div', attrs = {'id':'wrapper'})
    book_name = wrapper.h1.span.string
    book_name = strip_blank(book_name)
    print(book_name)
    book_info['book_name'] = book_name
    #book_name 包含书名及其对应的页面
    #print "book_name:",book_name,type(book_name)

    # get other info
    info = body.find('div',attrs = {'id':'info'}) #找到书籍信息的div
    text = str(info)
    # get book id
    id_pattern = re.compile(r"\d+")
    id_match = re.search(id_pattern, book_url)
    if id_match :
        book_info['id'] = int(id_match.group())
        #print "id:",int(id_match.group())
    # get author
    au_pattern = re.compile(r"作者:?</span>.*?<a.*?>(.*?)</a>", re.S)
    au_match = re.search(au_pattern, text)
    if au_match:
        # strip \n and \s
        author = strip_blank(au_match.group(1))
        #print "author:",author, type(author)
        book_info['author'] = author
    # get publisher
    pu_pattern = re.compile(r"出版社:</span>(.*?)<br/>")
    pu_match = re.search(pu_pattern, text)
    if pu_match:
        publisher = strip_blank(pu_match.group(1))
        #print "publisher:",publisher, type(publisher)
        book_info['publisher'] = publisher
    # get translator
    tr_pattern = re.compile(r"译者:?</span>.*?<a.*?>(.*?)</a>", re.S)
    tr_match = re.search(tr_pattern, text)
    if tr_match:
        translator = strip_blank(tr_match.group(1))
        #print "translator:",translator, type(translator)
        book_info['translator'] = translator
    # get publish_date
    date_pattern = re.compile(r"出版年:</span>(.*?)<br/>")
    data_match = re.search(date_pattern, text)
    if data_match:
        publish_date = strip_blank(data_match.group(1))
        #print "publish_date:",publish_date, type(publish_date)
        book_info['publish_date'] = publish_date
    # get page_num
    num_pattern = re.compile(r"页数:?</span>.*?(\d+).*?<br/?>", re.S)
    num_match = re.search(num_pattern, text)
    if num_match:
        #print "page_num:",int(num_match.group(1))
        book_info['page_num'] = int(num_match.group(1))
    # get isbn
    isbn_pattern = re.compile(r"ISBN:</span>.*?(\d+)<br/>")
    isbn_match = re.search(isbn_pattern, text)
    if isbn_match:
        #print "isbn:",isbn_match.group(1), type(isbn_match.group(1))
        book_info['isbn'] = isbn_match.group(1)
    # get score
    score_ele = body.find('strong', attrs = {'class':'ll rating_num '})

    if score_ele != None:
        try:
            score = float(score_ele.string)
            #print score,type(score)
            book_info['score'] = score
        except ValueError:
            pass
    # get rating num
    rt_num_ele = body.find('a', attrs = {'class':'rating_people'})
    if rt_num_ele != None and rt_num_ele.span != None:
        rt_num = int(rt_num_ele.span.string)
        #print rt_num
        book_info['rating_num'] = rt_num
    #print book_info
    return book_info

def disconnect_router():
    ssl._create_default_https_context = ssl._create_unverified_context
    data = {
        "method":"do",
        "login":{"password":"your_password_after_encrypt"}
    }
    headers = {
        'Host':'192.168.0.1',
        'User-Agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36',
        'Accept':'application/json, text/javascript, */*; q=0.01',
        'Accept-Encoding':'gzip, deflate',
        'Accept-Language':'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6',
        'Connection':'keep-alive',
        'Content-Length':'50',
        'Content-Type':'application/json; charset=UTF-8',
        'Origin':'http://192.168.0.1',
        'Referer':'http://192.168.0.1/',
        'X-Requested-With':'XMLHttpRequest'
    }
    url = "http://192.168.0.1/"
    html = requests.post(url,json=data,headers=headers,verify = False)
    stok = json.loads(html.text)["stok"]
    full_url = "http://192.168.0.1/stok="+ stok +"/ds"
    Disconnect = {"network":{"change_wan_status":{"proto":"pppoe","operate":"disconnect"}},"method":"do"}
    disconn_route = requests.post(url=full_url, json=Disconnect).json()
    logging.info("disconnecting router...sleep for %s s" % DISCON_SLEEP_TIME)
    time.sleep(DISCON_SLEEP_TIME)
    while 1:
        ping_code = os.system('ping www.baidu.com -c 2')
        if ping_code:
            logging.info("cannot connect to internet yet, sleep for %s s" % DISCON_SLEEP_TIME)
            time.sleep(DISCON_SLEEP_TIME)
        else:
            break

def getBooks(conn):
    sql = "select `book_name` from book_info;"
    cur = conn.cursor()
    cur.execute(sql)
    result = cur.fetchall()
    for line in result:
        print(line)
    cur.close()



if __name__=='__main__':
    #file = open('D:/book_infor/data/bookdesc.txt','a',encoding='UTF-8-sig')
    conn = MySQLdb.connect(
        host='112.74.160.185',
        port=3306,
        user='root',
        password='czf001413',
        database='test',
        charset='utf8'
    )
    cursor =conn.cursor()
    tag_list = get_tags(conn)
    results = getResult()
    headers = HEADERSES[0]

    cookie = {
        'Cookie': 'll="118220"; bid=MTB1h91kNvM; _vwo_uuid_v2=D2303FE00F3BD1BFC531A99A1957874C2|d328020d6dd53febfecd436cd92119da; gr_user_id=ee5aef86-e95b-479c-bcaa-ad638b6025cb; __yadk_uid=9Tq06FaTlbl5wqdbm2VKzUsaO1YIAe8l; push_noty_num=0; push_doumail_num=0; __utmv=30149280.19561; __gads=ID=b5a918eb6bcb4f64:T=1557971799:S=ALNI_MZ3FIC67_JH5vn20EmgI9ltvBSULg; __utmz=30149280.1558861026.6.4.utmcsr=baidu|utmccn=(organic)|utmcmd=organic; __utmz=81379588.1558861026.5.3.utmcsr=baidu|utmccn=(organic)|utmcmd=organic; viewed="30217599_27046300_1005411_1000280_27114628_26365491_4189498_30269326_27056016_27038832"; _pk_ref.100001.3ac3=%5B%22%22%2C%22%22%2C1560235079%2C%22https%3A%2F%2Faccounts.douban.com%2Fpassport%2Flogin%3Fredir%3Dhttps%253A%252F%252Fbook.douban.com%252Fsubject%252F1000280%252F%22%5D; _pk_ses.100001.3ac3=*; __utma=30149280.212175990.1548036387.1560176261.1560235079.11; __utmc=30149280; __utmt_douban=1; __utma=81379588.708256610.1555854271.1560176261.1560235079.10; __utmc=81379588; __utmt=1; ap_v=0,6.0; dbcl2="195618742:z5puy1bDh9A"; ck=FwdI; gr_session_id_22c937bbd8ebd703f2d8e9445f7dfd03=e6d41151-12ab-4212-b68e-2a969007d5af; gr_cs1_e6d41151-12ab-4212-b68e-2a969007d5af=user_id%3A1; _pk_id.100001.3ac3=427e2e1ac35e50d3.1555854271.26.1560235453.1560176261.; __utmb=30149280.3.10.1560235079; __utmb=81379588.3.10.1560235079; gr_session_id_22c937bbd8ebd703f2d8e9445f7dfd03_e6d41151-12ab-4212-b68e-2a969007d5af=true'
    }

    book_info = {'id':0, 'book_name':'NULL', 'book_desc':'NULL', 'book_img':'NULL'}
    for line in results:
        book_id =line[0]
        book_url = "https://book.douban.com/subject/"+str(book_id)

        content = get_html(book_url,cookie, headers)
        soup = BeautifulSoup(content, "lxml")
        body = soup.body
        if body ==None:
            break
        img_wrapper = body.find('a',attrs={'class':'nbg'})
        if img_wrapper!=None:
            img = img_wrapper.get("href")
            bookname = img_wrapper.get('title')
        else:
            img = "/img/0.jpg"
            bookname=book_id
        print(bookname+":"+img)
        # get book_desc
        wrapper = body.find('div', attrs={'class': 'intro'})
        if  wrapper != None:
            desc = wrapper.find_all('p')
            try:
                highpoints = re.compile(u'[\U00010000-\U0010ffff]')
            except re.error:
                highpoints = re.compile(u'[\uD800-\uDBFF][\uDC00-\uDFFF]')
            finally:
                desc = highpoints.sub(u'',str(desc))
        else:
            desc ="本书暂无描述"
        print(desc)
        sql = "insert into book_desc (id,book_name,book_desc,book_img) values (%s,%s,%s,%s)"
        cursor.execute(sql,[book_id,bookname,desc,img])
        #sqlstr = "insert into book_desc (id,book_name,book_desc,book_img) values "+"("+str(book_id)+","+str(bookname)+","+str(desc)+","+str(img)+")"
       # print(sqlstr)
        #file.write(sqlstr+"\n")

    #file.close()
    #conn.commit()
    cursor.close()

    conn.close()