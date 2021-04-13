#! /usr/local/bin/python3
""" Generate database tables for the different sources of information for potential baseline
    measures.
"""

import csv
import sys

from collections import namedtuple, defaultdict
import datetime
from pathlib import Path

from pgconnection import PgConnection

# Development connection
debug = open('./debug', 'w')

# Connect to data sources
# -------------------------------------------------------------------------------------------------

# Transfer Evaluations
trans_conn = PgConnection('cuny_transfers')
trans_cursor = trans_conn.cursor()

# Sessions
session_table_files = Path('./downloads').glob('*SESSION*')
session_table_file = None
for file in session_table_files:
  if session_table_file is None or file.stat().st_mtime > session_table_file.stat().st_mtime:
    session_table_file = file
print(f'Session Table: {session_table_file}', file=sys.stderr)

# Admissions
admissions_table_files = Path('./Admissions_Registrations').glob('*ADMISSIONS*')
admissions_table_file = None
for file in admissions_table_files:
  if admissions_table_file is None or file.stat().st_mtime > admissions_table_file.stat().st_mtime:
    admissions_table_file = file
print(f'Admissions: {admissions_table_file}', file=sys.stderr)

# Registrations
registrations_table_files = Path('./Admissions_Registrations').glob('*STUDENT*')
registrations_table_file = None
for file in registrations_table_files:
  if (registrations_table_file is None
     or file.stat().st_mtime > registrations_table_file.stat().st_mtime):
    registrations_table_file = file
print(f'Registrations: {registrations_table_file}', file=sys.stderr)


# Sessions Cache
# -------------------------------------------------------------------------------------------------
def session_factory(args):
  return Session._make(args)


Session = namedtuple('Session', 'first_enrollment_date open_enrollment_date last_enrollment_date '
                     'session_start_date session_end_date')
Session_Key = namedtuple('Session_Key', 'institution term session')
sessions = defaultdict(session_factory)
with open(session_table_file) as stf:
  session_reader = csv.reader(stf)
  for line in session_reader:
    if session_reader.line_num == 1:
      Row = namedtuple('Row', [col.lower().replace(' ', '_') for col in line])
    else:
      row = Row._make(line)
      if row.career != 'UGRD' or row.term < '1199' or row.term > '1219':
        continue

      try:
        m, d, y = row.first_date_to_enroll.split('/')
        first_enrollment_date = datetime.date(int(y), int(m), int(d))
        m, d, y = row.last_date_to_enroll.split('/')
        last_enrollment_date = datetime.date(int(y), int(m), int(d))
        m, d, y = row.open_enrollment_date.split('/')
        open_enrollment_date = datetime.date(int(y), int(m), int(d))
        m, d, y = row.session_beginning_date.split('/')
        session_start_date = datetime.date(int(y), int(m), int(d))
        m, d, y = row.session_end_date.split('/')
        session_end_date = datetime.date(int(y), int(m), int(d))
      except ValueError as ve:
        print(f'Session Date situation: {row}\n', file=debug)
        continue
      session_key = Session_Key._make([row.institution[0:3], int(row.term), row.session])
      sessions[session_key] = Session._make([first_enrollment_date, open_enrollment_date,
                                            last_enrollment_date, session_start_date,
                                            session_end_date])

# for session_key in sorted(sessions.keys()):
#   if session_key.term % 10 == 6:
#     print(f'{session_key.institution} {session_key.term} {session_key.session}: '
#           f'{sessions[session_key]}', file=debug)
trans_cursor.execute("""
drop table if exists sessions;
create table sessions (
  institution text,
  term int,
  session text,
  first_enrollment date,
  open_enrollment date,
  last_enrollment date,
  session_start date,
  session_end date,
  primary key (institution, term, session)
)
""")

for key in sessions.keys():
  trans_cursor.execute("""
insert into sessions values (%s, %s, %s, %s, %s, %s, %s, %s)
""", (key.institution, key.term, key.session,
      sessions[key].first_enrollment_date, sessions[key].open_enrollment_date,
      sessions[key].last_enrollment_date, sessions[key].session_start_date,
      sessions[key].session_end_date))
trans_conn.commit()


# Admissions Table
# -------------------------------------------------------------------------------------------------
admittees = defaultdict(dict)
Admittee_Key = namedtuple('Admittee_key',
                          'student_id application_number institution admit_term, requirement_term')
Admission_Event = namedtuple('Admission_Event',
                             'admit_type action_date effective_date')
"""
    "ID","Career","Career Nbr","Appl Nbr","Prog Nbr","Institution","Acad Prog","Status","Eff
    Date","Effective Sequence","Program Action","Action Date","Action Reason","Admit Term","Expected
    Graduation Term","Requirement Term","Approved Academic Load","Campus","Application
    Center","Admit Type","Financial Aid Interest","Housing Interest","Application Fee
    Status","Application Fee Date","Notification Plan","Region","Recruiter","Last School
    Attended","Created On","Created By","Last Updated On","Updated By","Application
    Complete","Completed Date","Application Date","Graduation Date","Acad Level","Override
    Deposit","External Application"
"""
with open(admissions_table_file, encoding='ascii', errors='backslashreplace') as atf:
  admissions_reader = csv.reader(atf)
  for line in admissions_reader:
    if admissions_reader.line_num == 1:
      Row = namedtuple('Row', [col.lower().replace(' ', '_') for col in line])
    else:
      row = Row._make(line)
      admit_term = int(row.admit_term)
      try:
        requirement_term = int(row.requirement_term)
      except ValueError as ve:
        requirement_term = 0
      if row.career != 'UGRD' or admit_term < 1199 or admit_term > 1219:
        continue
      try:
        admittee_key = Admittee_Key._make([int(row.id), int(row.appl_nbr), row.institution[0:3],
                                          admit_term, requirement_term])
      except ValueError as ve:
        print(f'Admittee Key situation: {row}')
        continue
      if row.program_action in ['APPL', 'ADMT', 'DEIN', 'MATR'] \
         and row.admit_type in ['TRN', 'TRD']:
        try:
          m, d, y = row.action_date.split('/')
          action_date = datetime.date(int(y), int(m), int(d))
          m, d, y = row.eff_date.split('/')
          effective_date = datetime.date(int(y), int(m), int(d))
        except ValueError as ve:
          print(f'Admittee Date situation: {row}\n', file=debug)
          continue
        admittees[admittee_key][row.program_action] = \
            Admission_Event._make([row.admit_type, action_date, effective_date])
print(f'{len(admittees.keys()):,} Admittees', file=sys.stderr)

trans_cursor.execute("""
drop table if exists admissions;
create table admissions (
student_id int,
application_number int,
institution text,
admit_term int,
requirement_term int,
event_type text,
admit_type text,
action_date date,
effective_date date,
primary key (student_id, application_number, institution, admit_term, requirement_term, event_type)
);
""")
for key in admittees.keys():
  for event_type in admittees[key].keys():
    trans_cursor.execute(f"""
insert into admissions values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
on conflict do nothing;
""", (key.student_id, key.application_number, key.institution, key.admit_term, key.requirement_term,
      event_type,
      admittees[key][event_type].admit_type,
      admittees[key][event_type].action_date,
      admittees[key][event_type].effective_date))
    if trans_cursor.rowcount == 0:
      print(f'Admissions Data situation: {trans_cursor.query.decode()}', file=debug)
trans_conn.commit()

# Report: difference between action date and effective date
counts = defaultdict(int)
for admittee_key in admittees.keys():
  for event_type in admittees[admittee_key].keys():
    delta = round((((admittees[admittee_key][event_type].effective_date
                     - admittees[admittee_key][event_type].action_date).days)) / 7)
    counts[delta] += 1
with open('./reports/action-effective_differences.csv', 'w') as aed:
  print('Weeks, Frequency', file=aed)
  for days in sorted(counts.keys()):
    print(f'{days:4}, {counts[days]}', file=aed)


# Registraton Events
# -------------------------------------------------------------------------------------------------
def registration_factory():
  return {'first_registration_date': None, 'last_registration_date': None}


"""
    "ID","Career","Institution","Term","Class Nbr","Course Career","Session","Student Enrollment
    Status","Enrollment Status Reason","Last Enrollment Action","Enrollment Add Date","Enrollment
    Drop Date","Units Taken","Units Taken-Academic Progress","Units Taken-Fin Aid Progress","Course
    Count","Grading Basis","Official Grade","Grade Input","Repeat Code","Include in GPA","Units
    Attempted","Grade Points","Designation","RD Option","RD Grade","Academic
    Group","Subject","Catalog Nbr","Description","Last Enrl Action Reason","Last Enrollment Action
    Process","Status"

"""
# Get first and last registration add dates for each term by student/college
Registration_Key = namedtuple('Registration_Key', 'student_id institution term')
registration_events = defaultdict(registration_factory)
m = 0
n = len(open(registrations_table_file, encoding='ascii', errors='backslashreplace').readlines()) - 1
print('Read Registrations', file=sys.stderr)
with open(registrations_table_file, encoding='ascii', errors='backslashreplace') as rtf:
  registrations_reader = csv.reader(rtf)
  for line in registrations_reader:
    if registrations_reader.line_num == 1:
      Row = namedtuple('Row', [col.lower().replace(' ', '_').replace('-', '_') for col in line])
    else:
      m += 1
      print(f  '{m:6,} / {n:,}\r', end='', file=sys.stderr)
      row = Row._make(line)
      term = int(row.term)
      if row.career != 'UGRD' or term < 1199 or row.session != '1':
        continue
      registration_key = Registration_Key._make([row.id, row.institution[0:3], term])
      try:
        mo, da, yr = row.enrollment_add_date.split('/')
        enrollment_date = datetime.date(int(yr), int(mo), int(da))
      except ValueError as ve:
        print(f'Enrollment date situation: {row}', file=debug)
        continue
      first = registration_events[registration_key]['first_registration_date']
      last = registration_events[registration_key]['last_registration_date']
      changed = False
      if first is None or enrollment_date < first:
        first = enrollment_date
        changed = True
      if last is None or enrollment_date > last:
        last = enrollment_date
        changed = True
      if changed:
        registration_events[registration_key] = {'first_registration_date': first,
                                                 'last_registration_date': last}

print('\rBuild registrations table', file=sys.stderr)

trans_cursor.execute("""
drop table if exists registrations;
create table registrations (
  student_id int,
  institution text,
  term int,
  first_date date,
  last_date date,
  primary key (student_id, institution, term))
""")
for registration_key in registration_events.keys():
  trans_cursor.execute(f"""
insert into registrations values (%s, %s, %s, %s, %s)
""", (registration_key.student_id, registration_key.institution, registration_key.term,
      registration_events[registration_key]['first_registration_date'],
      registration_events[registration_key]['last_registration_date']))

trans_conn.commit()
