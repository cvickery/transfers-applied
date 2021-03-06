#! /usr/local/bin/python3
""" The admit_types table explains the admit_type codes in the admissions table.
    There are inconsistencies in the descriptions across colleges. but the following two cover
    transfers for all colleges:
      TRN Transfer
      TRD Transfer Direct
"""
import csv
from collections import namedtuple
from pgconnection import PgConnection
conn = PgConnection('cuny_transfers')
cursor = conn.cursor()

cursor.execute("""
drop table if exists admit_types;
create table admit_types (
institution text,
admit_type text,
description text,
primary key (institution, admit_type)
)
""")

with open('./Admissions_Registrations/admit_type_table.csv') as att:
  reader = csv.reader(att)
  for line in reader:
    if reader.line_num == 1:
      cols = [c.lower().replace(' ', '_') for c in line]
      Row = namedtuple('Row', cols)
    else:
      row = Row._make(line)
      cursor.execute(f"""
insert into admit_types values ('{row.institution}', '{row.admit_type}', '{row.descr}')
""")

conn.commit()
