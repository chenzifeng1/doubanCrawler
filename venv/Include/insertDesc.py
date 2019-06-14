
import MySQLdb
import re

def insert():
    file = open('D:/book_infor/data/bookdesc.txt','r',encoding='UTF-8-sig')
    conn = MySQLdb.connect(
        host='112.74.160.185',
        port=3306,
        user='root',
        password='czf001413',
        database='test',
        charset='utf8'
    )

    cursor = conn.cursor()
    for line in file.readlines():
        sql = re.sub("\n","",line)
        cursor.execute(sql)
    conn.commit()
    cursor.close()
    conn.close()

if __name__=='__main__':
    insert()