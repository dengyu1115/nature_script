select * from workday;

select * from sqlite_master where type='table' and tbl_name = 'workday';

CREATE TABLE workday(date text,type text,primary key(date))

select * from page_config;

select * from fund_data;

select * from kline where code='159941' and type='0' order by date;

select name,type from sqlite_master;
