import sys, os
sys.path.insert(0, os.getcwd())

errors = []

# 1. Unified state
try:
    from state.shared_state import MASState, CandidateProfile, MatchResult, RankedCandidate, JobDescription
    print('[OK] state.shared_state')
except Exception as e:
    errors.append(f'[FAIL] state.shared_state: {e}')

# 2. Observability
try:
    from observability.logger import log_event
    print('[OK] observability.logger')
except Exception as e:
    errors.append(f'[FAIL] observability.logger: {e}')

# 3. Tools
try:
    from tools.grammar_check_tool import grammar_check
    print('[OK] tools.grammar_check_tool')
except Exception as e:
    errors.append(f'[FAIL] tools.grammar_check_tool: {e}')

try:
    from tools.parser_tool import read_all_cvs
    print('[OK] tools.parser_tool')
except Exception as e:
    errors.append(f'[FAIL] tools.parser_tool: {e}')

try:
    from tools.ranker_tool import ranker_tool
    print('[OK] tools.ranker_tool')
except Exception as e:
    errors.append(f'[FAIL] tools.ranker_tool: {e}')

# 4. Database
try:
    from database.db_manager import initialize_database, save_match_result, get_all_match_results, clear_results_for_job
    print('[OK] database.db_manager')
except Exception as e:
    errors.append(f'[FAIL] database.db_manager: {e}')

# 5. Logs
try:
    from logs.agent_log import log_agent_start, log_agent_complete, log_tool_error, log_state_update
    print('[OK] logs.agent_log')
except Exception as e:
    errors.append(f'[FAIL] logs.agent_log: {e}')

# 6. Utils
try:
    from utils.parser_adapter import load_candidates_from_parsed_json
    print('[OK] utils.parser_adapter')
except Exception as e:
    errors.append(f'[FAIL] utils.parser_adapter: {e}')

# 7. Agents
try:
    from agents.parser_agent import run_document_parser, run_parser_agent
    print('[OK] agents.parser_agent')
except Exception as e:
    errors.append(f'[FAIL] agents.parser_agent: {e}')

try:
    from agents.job_matcher_agent import run_job_matcher_agent
    print('[OK] agents.job_matcher_agent')
except Exception as e:
    errors.append(f'[FAIL] agents.job_matcher_agent: {e}')

try:
    from agents.ranker_agent import run_candidate_ranker
    print('[OK] agents.ranker_agent')
except Exception as e:
    errors.append(f'[FAIL] agents.ranker_agent: {e}')

try:
    from agents.report_generator import run_report_generator
    print('[OK] agents.report_generator')
except Exception as e:
    errors.append(f'[FAIL] agents.report_generator: {e}')

# 8. Main
try:
    import importlib.util
    spec = importlib.util.spec_from_file_location('main', 'main.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print('[OK] main.py')
except Exception as e:
    errors.append(f'[FAIL] main.py: {e}')

print()
if errors:
    print('=== FAILURES ===')
    for err in errors:
        print(err)
    sys.exit(1)
else:
    print('All imports resolved successfully.')
