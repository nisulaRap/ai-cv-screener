import sys, os
sys.path.insert(0, os.getcwd())

from state.shared_state import MASState
from agents.parser_agent import run_document_parser
import json

# Load real job description
with open('data/job_description.json') as f:
    job = json.load(f)

initial_state: MASState = {
    'job_description_path': 'data/job_description.json',
    'cv_folder_path': 'data/cvs',
    'job_description': job,
    'candidate_profiles': [],
    'match_results': [],
    'ranked_candidates': [],
    'executive_summary': None,
    'report_path': None,
    'logs': [],
    'errors': [],
}

print('=== Agent 1: Document Parser ===')
state = run_document_parser(initial_state)

profiles = state.get('candidate_profiles', [])
print(f'  Parsed {len(profiles)} candidate(s)')
for p in profiles:
    name = p.get('name', '?')
    skills = p.get('skills', [])
    exp = p.get('experience_years', 0)
    edu = p.get('education', '?')
    print(f'    - {name} | exp={exp}y | edu={edu} | skills={skills}')

print()
errors = state.get('errors', [])
logs = state.get('logs', [])
print(f'  Logs   : {logs}')
print(f'  Errors : {errors}')
print()

if 'candidate_profiles' in state and len(profiles) > 0:
    print('Agent 1 OUTPUT -> candidate_profiles  : PASS')
else:
    print('Agent 1 OUTPUT -> candidate_profiles  : FAIL (empty or missing)')

# Verify state keys present for Agent 2
required_keys = ['candidate_profiles', 'job_description', 'match_results', 'ranked_candidates', 'logs', 'errors']
missing = [k for k in required_keys if k not in state]
if missing:
    print(f'Missing state keys for Agent 2: {missing}')
else:
    print('All required state keys present    : PASS')
