#! /usr/bin/env python3

import csv
import datetime
import sys
from collections import namedtuple
from pathlib import Path
from pgconnection import PgConnection
from psycopg2 import errors

possibles = Path('/Users/vickery/transfers_applied/downloads').glob('*FULL*')
latest = None
for possible in possibles:
  if latest is None or possible.stat().m_time > latest.stat.m_time:
    latest = possible
if latest is None:
  sys.exit('No population source found.')

print('You are about to overwrite years of intense effort. Repent or Proceed (r/P)? ',
      end='', file=sys.stderr)
if input().startswith('r'):
  print('Ill-advised consequences averted.', file=sys.stderr)
  exit()

conn = PgConnection()
cursor = conn.cursor()

cursor.execute("""
drop table if exists transfers_applied cascade;

create table transfers_applied (
id serial primary key,
student_id integer not NULL,
src_institution text not NULL,
transfer_model_nbr integer not NULL,
enrollment_term date not NULL,
enrollment_session text not NULL,
articulation_term date not NULL,
model_status text not NULL,
posted_date date,
src_subject text not NULL,
src_catalog_nbr text not NULL,
src_designation text not NULL,
src_grade text not NULL,
src_gpa real not NULL,
src_course_id integer not NULL,
src_offer_nbr integer not NULL,
src_description text not NULL,
academic_program text not NULL,
units_taken real not NULL,
dst_institution text not NULL,
dst_designation text not NULL,
dst_course_id integer not NULL,
dst_offer_nbr integer not NULL,
dst_subject text not NULL,
dst_catalog_nbr text not NULL,
dst_grade text not NULL,
dst_gpa real not NULL
);

create unique index on transfers_applied (student_id,
                                          src_course_id,
                                          src_offer_nbr,
                                          dst_institution,
                                          posted_date);
""")
conn.commit()

with open('populate_report.csv', 'w') as report:
  m = 0
  n = len(open(latest, newline=None, errors='replace').readlines())
  with open(latest, newline=None, errors='replace') as csvfile:
    reader = csv.reader(csvfile, )
    for line in reader:

      if reader.line_num == 1:
        headers = [h.lower().replace(' ', '_') for h in line]
        print(','.join(headers), file=report)
        placeholders = ((len(headers)) * '%s,').strip(', ')
        cols = ', '.join([h for h in headers])
        Row = namedtuple('Row', headers)
      else:
        m += 1
        print(f'  {m:06,}/{n:06,}\r', end='', file=sys.stderr)
        row = Row._make(line)

        yr = 1900 + 100 * int(row.enrollment_term[0]) + int(row.enrollment_term[1:3])
        mo = int(row.enrollment_term[-1])
        da = 1
        enrollment_term = datetime.date(yr, mo, da)

        yr = 1900 + 100 * int(row.articulation_term[0]) + int(row.articulation_term[1:3])
        mo = int(row.articulation_term[-1])
        articulation_term = datetime.date(yr, mo, da)

        if '/' in row.posted_date:
          mo, da, yr = row.posted_date.split('/')
          posted_date = datetime.date(int(yr), int(mo), int(da))
        else:
          posted_date = None

        value_tuple = (row.student_id, row.src_institution, row.transfer_model_nbr, enrollment_term,
                       row.enrollment_session, articulation_term, row.model_status, posted_date,
                       row.src_subject, row.src_catalog_nbr, row.src_designation, row.src_grade,
                       row.src_gpa, row.src_course_id, row.src_offer_nbr, row.src_description,
                       row.academic_program, row.units_taken, row.dst_institution,
                       row.dst_designation, row.dst_course_id, row.dst_offer_nbr, row.dst_subject,
                       row.dst_catalog_nbr, row.dst_grade, row.dst_gpa)
        cursor.execute(f'insert into transfers_applied ({cols}) values ({placeholders}) '
                       f'on conflict do nothing',
                       value_tuple)
        if cursor.rowcount == 0:
          print(','.join(line), file=report)

  conn.commit()
  exit()
