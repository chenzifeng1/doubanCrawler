#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import codecs
import pymysql


def getHTML(url):
    r = requests.get(url)
    return r.content

def parseHTML(html):
    soup = BeautifulSoup(html, 'lxml')
    body = soup.body
    table = body.find('table', attrs={'class': 'tagCol'})
    td_list = table.find_all('td')
    tag_list = []
    for td in td_list:
        #tag_list.append(td.a.string.encode('utf-8'))
        tag_list.append(td.a.string)
    return tag_list

def write_file(tag_list):
    conn = pymysql.connect(
        host='112.74.160.185',
        port=3306,
        user='root',
        password='czf001413',
        database='test',
        charset='utf8'
    )
    cur = conn.cursor()
    for tag_name in tag_list:
        cur.execute("insert into `tag_info`(`name`) values(%s)", [tag_name])
    cur.close()
    conn.commit()
    conn.close()

if __name__ == '__main__':
    URL = 'https://book.douban.com/tag/?view=cloud'
    html = getHTML(URL)
    data_list = parseHTML(html)
    write_file(data_list)