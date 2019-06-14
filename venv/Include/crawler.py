import urllib3

url =
CREATE TABLE `book_info` (
`id` INT(11) NOT NULL COMMENT '书本在网站唯一id',
`book_name` VARCHAR(200) DEFAULT NULL COMMENT '书名',
`author` VARCHAR(100) DEFAULT NULL COMMENT '作者',
`publisher` VARCHAR(200) DEFAULT NULL COMMENT '出版社',
`translator` VARCHAR(100) DEFAULT NULL COMMENT '译者',
`publish_date` VARCHAR(100) DEFAULT NULL COMMENT '出版年',
`page_num` INT(6) DEFAULT '0' COMMENT '页数',
`isbn` VARCHAR(20) DEFAULT NULL COMMENT '书号',
`score` FLOAT(3,1) DEFAULT '0.0' COMMENT '评分',`rating_num` INT(11) DEFAULT '0' COMMENT '评分人数',`tag` VARCHAR(30) DEFAULT NULL COMMENT '领域标签',
PRIMARY KEY  (`id`)) ENGINE=InnoDB DEFAULT CHARSET=utf8 COMMENT='书本信息';