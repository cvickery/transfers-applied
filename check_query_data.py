#! /usr/local/bin/python3

import os
import sys

from datetime import datetime
from time import time
from pathlib import Path

from pgconnection import PgConnection

""" To update the timeline data, the baseline tables need to be up to date. Updating them is a
    a manual process. Then the timeline tables can be re-built.
"""

# Report the ages of the queries used to build baseline tables
queries = ['CV_QNS_ADMISSIONS', 'CV_QNS_STUDENT_SUMMARY', 'QNS_CV_SESSION_TABLE',
           'admit_action_table', 'admit_type_table', 'prog_reason_table']
project_dir = Path('/Users/vickery/Projects/transfers_applied/')
query_dir = Path(project_dir, 'Admissions_Registrations')
today = datetime.today().timestamp()
sec_per_day = 3600 * 24

warnings = []
for query in queries:
  latest = None
  for file in Path(query_dir).glob(f'{query}*'):
    if latest is None or file.stat().st_mtime > latest.stat().st_mtime:
      latest = file
  days = int((today - latest.stat().st_mtime) / sec_per_day)
  suffix = '' if days == 1 else 's'
  if days > 0 and query in ['CV_QNS_ADMISSIONS', 'CV_QNS_STUDENT_SUMMARY', 'QNS_CV_SESSION_TABLE']:
    warnings.append(query)
  print(f'Latest {query} is {days} day{suffix} old.')

if warnings:
  is_are = 'is' if len(warnings) == 1 else 'are'
  print(f'WARNING: {len(warnings)} of the key query files {is_are} out of date.'
        f'\n Proceed anyway? (yN) ', end='')
  if not input().lower().startswith('y'):
    sys.exit('Update abandoned.')

# Rebuild the baseline tables
baseline_start_time = time()
print('Rebuilding the baseline tables')
os.system(f'{project_dir}/build_baseline_tables.py')
print(f'That took {int(time() - baseline_start_time)} seconds')

# Normal exit
exit(0)

# # Re-generate the timeline spreadsheets
# timelines_start_time = time()
# print('Replacing all timeline spreadsheets')
# timelines_dir = Path(project_dir, 'timelines')
# os.system(f'{project_dir}/generate_baseline_stats.sh')
# print(f'That took {time() - timelines_start_time} seconds')

# print(f'{time() - baseline_start_time} total seconds')